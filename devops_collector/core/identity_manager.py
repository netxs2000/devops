"""统一身份管理服务 (Identity Manager)

负责在多系统采集过程中进行人员身份对齐与去重，支持 SCD Type 2 生命周期。
遵循 Google Python Style Guide。
"""

import logging
import uuid
from typing import Any

from sqlalchemy.orm import Session

from devops_collector.models.base_models import IdentityMapping, User


logger = logging.getLogger(__name__)


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
    ) -> User:
        """根据外部账号解析并获取全局用户实体。"""
        email_lower = email.lower().strip() if email else None
        ext_id_str = str(external_id).strip()
        cache_key = (source, ext_id_str)

        # 0. 优先检查本地内存缓存 (存储 ID 而非对象，防止跨 Session 游离)
        if cache_key in cls._local_cache:
            user_id = cls._local_cache[cache_key]
            user = session.query(User).filter_by(global_user_id=user_id, is_current=True).first()
            if user:
                return user

        # 1. 查找现有映射
        mapping = session.query(IdentityMapping).filter_by(source_system=source, external_user_id=ext_id_str).first()

        if mapping:
            current_user = session.query(User).filter_by(global_user_id=mapping.global_user_id, is_current=True).first()
            if current_user:
                cls._local_cache[cache_key] = current_user.global_user_id
                return current_user

        # 2. 尝试从主数据对齐 (Email 优先)
        user = None
        if email_lower:
            user = session.query(User).filter_by(primary_email=email_lower, is_current=True).first()

        # 3. 如果 Email 没中，试工号
        if not user and employee_id:
            user = session.query(User).filter_by(employee_id=employee_id, is_current=True).first()

        # 4. 如果还没中，尝试通过姓名匹配
        if not user and name:
            potential_users = session.query(User).filter_by(full_name=name, is_current=True).all()
            if len(potential_users) == 1:
                user = potential_users[0]

        # 5. 如果彻底找不到，创建一个待对齐的外部用户
        if not user:
            new_uid = uuid.uuid4()
            user = User(
                global_user_id=new_uid,
                full_name=name or f"Unknown_{source}_{ext_id_str}",
                primary_email=email_lower,
                employee_id=employee_id,
                is_active=False,
                is_survivor=False,
                sync_version=1,
                is_current=True,
            )
            session.add(user)
            logger.info(f"创建外部临时用户: {user.full_name} ({source}:{ext_id_str})")

        # 6. 建立映射关系
        if not mapping:
            existing_user_mapping = session.query(IdentityMapping).filter_by(
                source_system=source, global_user_id=user.global_user_id
            ).first()
            
            if not existing_user_mapping:
                mapping = IdentityMapping(
                    global_user_id=user.global_user_id,
                    source_system=source,
                    external_user_id=ext_id_str,
                    external_username=name,
                    external_email=email_lower,
                    mapping_status="AUTO" if user.is_survivor else "PENDING",
                    confidence_score=1.0 if user.is_survivor else 0.5,
                )
                session.add(mapping)
            else:
                logger.info(f"用户 {user.full_name} 在 {source} 下已有映射，不再重复处理。")

        cls._local_cache[cache_key] = user.global_user_id
        return user
