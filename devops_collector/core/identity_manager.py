"""统一身份管理服务 (Identity Manager)

负责在多系统采集过程中进行人员身份对齐与去重，支持 SCD Type 2 生命周期。
遵循 Google Python Style Guide。
"""

import logging
from typing import Any

from sqlalchemy.orm import Session

from devops_collector.models.base_models import IdentityMapping, User


logger = logging.getLogger(__name__)

from sqlalchemy.dialects.postgresql import insert


class IdentityManager:
    """身份管理中心，提供跨系统的用户识别与映射能力。"""

    _local_cache: dict[tuple[str, str], Any] = {}

    @classmethod
    def get_or_create_user(
        cls,
        session: Session,
        source: str,
        external_id: str,
        email: str | None = None,
        name: str | None = None,
        employee_id: str | None = None,
    ) -> User | None:
        """根据外部账号解析并获取全局用户实体。"""
        email_lower = email.lower().strip() if email else None
        ext_id_str = str(external_id).strip()
        cache_key = (source, ext_id_str)

        # 0. 优先检查本地内存缓存 (存储 ID 而非对象，防止跨 Session 游离)
        if cache_key in cls._local_cache:
            user_id = cls._local_cache[cache_key]
            user = session.query(User).filter_by(global_user_id=user_id).first()
            if user:
                return user

        # 1. 查找现有映射
        mapping = session.query(IdentityMapping).filter_by(source_system=source, external_user_id=ext_id_str).first()

        if mapping:
            current_user = session.query(User).filter_by(global_user_id=mapping.global_user_id).first()
            if current_user:
                cls._local_cache[cache_key] = current_user.global_user_id
                return current_user

        # 2. 尝试从主数据对齐 (Email 优先)
        user = None
        if email_lower:
            user = session.query(User).filter_by(primary_email=email_lower).first()

        # 3. 如果 Email 没中，试工号
        if not user and employee_id:
            user = session.query(User).filter_by(employee_id=employee_id).first()

        # 4. 如果还没中，尝试通过姓名匹配
        if not user and name:
            potential_users = session.query(User).filter_by(full_name=name).all()
            if len(potential_users) == 1:
                user = potential_users[0]

        # 5. 如果彻底找不到，不再创建临时用户，而是记录原始信号供 dbt 后续处理
        if not user:
            logger.debug(f"未找到匹配的全局用户，记录信号待 dbt 处理: {source}:{ext_id_str}")

        # 6. 建立映射关系 (如果不存在)
        if not mapping:
            # 并发加固：在插入前再次尝试根据 Global User ID 查找，防止 uq_source_global_user 冲突
            if user:
                mapping = session.query(IdentityMapping).filter_by(source_system=source, global_user_id=user.global_user_id).first()

            if not mapping:
                try:
                    # 使用子事务保护，防止 IntegrityError 破坏外部 Session
                    with session.begin_nested():
                        # 第一步：处理 external_user_id 冲突
                        stmt = (
                            insert(IdentityMapping)
                            .values(
                                global_user_id=user.global_user_id if user else None,
                                source_system=source,
                                external_user_id=ext_id_str,
                                external_username=name,
                                external_email=email_lower,
                                mapping_status="AUTO" if user and user.is_survivor else "PENDING",
                                confidence_score=1.0 if user and user.is_survivor else 0.5,
                            )
                            .on_conflict_do_nothing(index_elements=["source_system", "external_user_id"])
                        )
                        session.execute(stmt)

                        # 第二步：处理 global_user_id 冲突 (如果 user 存在且没触发第一步冲突)
                        if user:
                            # 再次使用子事务或直接执行 ON CONFLICT (后者更稳健)
                            stmt_global = (
                                insert(IdentityMapping)
                                .values(
                                    global_user_id=user.global_user_id,
                                    source_system=source,
                                    external_user_id=ext_id_str,
                                    external_username=name,
                                    external_email=email_lower,
                                    mapping_status="AUTO" if user.is_survivor else "PENDING",
                                    confidence_score=1.0 if user.is_survivor else 0.5,
                                )
                                .on_conflict_do_nothing(index_elements=["source_system", "global_user_id"])
                            )
                            session.execute(stmt_global)
                    session.flush()
                except Exception as e:
                    # 如果仍有冲突（极少数情况），不再报错，由后续查询补齐
                    logger.debug(f"Recovered from concurrent identity insertion: {e}")
                    session.rollback()

            # 为了使 session 状态保持一致，重新查询 mapping
            mapping = session.query(IdentityMapping).filter_by(source_system=source, external_user_id=ext_id_str).first()
            if mapping:
                logger.info(f"Identity mapping secured: {source}:{ext_id_str}")

        if user:
            cls._local_cache[cache_key] = user.global_user_id
        return user
