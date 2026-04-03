"""统一身份管理服务 (Identity Manager)

负责在多系统采集过程中进行人员身份对齐与去重，支持 SCD Type 2 生命周期。
遵循 Google Python Style Guide。
"""

import logging
import uuid
from typing import Any

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from devops_collector.models.base_models import IdentityMapping, User


logger = logging.getLogger(__name__)


class IdentityManager:
    """人员身份对齐管理器。

    使用内存缓存及数据库映射表 (mdm_identity_mappings) 实现
    跨系统账号与全局 OneID (global_user_id) 的关联。
    """

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
        username: str | None = None,
        create_if_not_found: bool = False,
    ) -> User | None:
        """根据外部账号解析并获取全局用户实体。

        Args:
            session: 通用数据库会话。
            source: 来源系统名称 (如 'gitlab', 'zentao')。
            external_id: 外部系统中的用户唯一标识 (UID)。
            email: 用户邮箱 (用于对齐的主要凭据)。
            name: 用户显示名称 (可选)。
            employee_id: 员工工号 (可选)。
            username: 外部系统用户名 (可选)。

            create_if_not_found: 是否在找不到时自动创建 User 实体 (仅限主数据源)。

        Returns:
            Resolved User 实体，若未命中任何规则且无法新建则返回 None。
        """
        email_lower = email.lower().strip() if email else None
        ext_id_str = str(external_id).strip()
        cache_key = (source, ext_id_str)

        # 0. 优先检查本地内存缓存
        if cache_key in cls._local_cache:
            user_id = cls._local_cache[cache_key]
            user = session.query(User).filter_by(global_user_id=user_id, is_current=True).first()
            if user:
                return user

        # 1. 查找现有映射
        mapping = session.query(IdentityMapping).filter_by(source_system=source, external_user_id=ext_id_str).first()

        if mapping and mapping.global_user_id:
            current_user = session.query(User).filter_by(global_user_id=mapping.global_user_id, is_current=True).first()
            if current_user:
                cls._local_cache[cache_key] = current_user.global_user_id
                return current_user

        # 2. 尝试从主数据对齐 (Email 优先, 需查询当前生效版本)
        user = None
        if email_lower:
            user = session.query(User).filter_by(primary_email=email_lower, is_current=True).first()

        # 3. 如果 Email 没中，试工号
        if not user and employee_id:
            user = session.query(User).filter_by(employee_id=employee_id, is_current=True).first()

        # 4. 如果还没中，尝试通过 username 匹配
        if not user and username:
            user = session.query(User).filter_by(username=username, is_current=True).first()

        # 5. 如果彻底找不到，记录调试信息并按需创建
        if not user:
            if create_if_not_found and email_lower:
                user = User(
                    global_user_id=uuid.uuid4(),
                    full_name=name or username or email_lower.split("@")[0],
                    primary_email=email_lower,
                    employee_id=employee_id,
                    username=username or email_lower.split("@")[0],
                    source_system=source,
                    is_current=True,
                    is_survivor=True,  # 标记为由受信任源同步生成
                )
                session.add(user)
                session.flush()
            else:
                logger.debug(f"未找到匹配的全局用户，记录身份映射供后续人工或 dbt 治理: {source}:{ext_id_str}")

        # 6. 建立或更新映射关系
        if not mapping:
            # 检测数据库方言（SQLite 不支持 PostgreSQL 的 ON CONFLICT 语法）
            is_postgres = session.bind.dialect.name == "postgresql" if session.bind else True

            if is_postgres:
                try:
                    with session.begin_nested():
                        stmt = (
                            insert(IdentityMapping)
                            .values(
                                global_user_id=user.global_user_id if user else None,
                                source_system=source,
                                external_user_id=ext_id_str,
                                external_username=name or username or ext_id_str,
                                external_email=email_lower,
                                mapping_status="AUTO" if user and user.is_survivor else "PENDING",
                                confidence_score=1.0 if user and user.is_survivor else 0.5,
                            )
                            .on_conflict_do_nothing(index_elements=["source_system", "external_user_id"])
                        )
                        session.execute(stmt)
                    session.flush()
                except Exception as e:
                    logger.debug(f"Recovered from concurrent identity insertion: {e}")
                    session.rollback()
            else:
                # 兼容性退化逻辑 (用于 SQLite/测试环境): 先查后增
                mapping = session.query(IdentityMapping).filter_by(source_system=source, external_user_id=ext_id_str).first()
                if not mapping:
                    mapping = IdentityMapping(
                        global_user_id=user.global_user_id if user else None,
                        source_system=source,
                        external_user_id=ext_id_str,
                        external_username=name or username or ext_id_str,
                        external_email=email_lower,
                        mapping_status="AUTO" if user and user.is_survivor else "PENDING",
                        confidence_score=1.0 if user and user.is_survivor else 0.5,
                    )
                    session.add(mapping)
                    session.flush()

            mapping = session.query(IdentityMapping).filter_by(source_system=source, external_user_id=ext_id_str).first()

        # 7. 缓存结果
        if user:
            cls._local_cache[cache_key] = user.global_user_id
        return user
