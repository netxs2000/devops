"""统一身份管理服务 (Identity Manager)

负责在多系统采集过程中进行人员身份对齐与去重，支持 SCD Type 2 生命周期。
遵循 Google Python Style Guide。
"""
import logging
import uuid
from typing import Optional
from sqlalchemy.orm import Session
from devops_collector.models.base_models import User, IdentityMapping
logger = logging.getLogger(__name__)

class IdentityManager:
    """身份管理中心，提供跨系统的用户识别与映射能力。"""

    @staticmethod
    def get_or_create_user(session: Session, source: str, external_id: str, email: Optional[str]=None, name: Optional[str]=None, employee_id: Optional[str]=None) -> User:
        """根据外部账号解析并获取全局用户实体。
        
        策略:
        1. 优先查找是否存在已建立的 IdentityMapping。
        2. 如果存在映射，返回关联的当前有效 User (is_current=True)。
        3. 如果没找到，尝试按 Email 检索现有 User。
        4. 如果按 Email 找到，则建立新的 Mapping 关系。
        5. 如果所有特征均未匹配，创建全新的全局用户 (SCD v1)。
        
        Args:
            session: 数据库会话。
            source: 系统来源 (如 'gitlab', 'jira')。
            external_id: 外部系统原始 ID。
            email: 用户邮箱 (核心识别依据)。
            name: 用户名 (可选)。
            employee_id: 工号 (辅助依据)。
            
        Returns:
            User: 关联后的当前有效用户对象。
        """
        email_lower = email.lower() if email else None
        mapping = session.query(IdentityMapping).filter_by(source_system=source, external_user_id=str(external_id)).first()
        if mapping:
            current_user = session.query(User).filter_by(global_user_id=mapping.global_user_id, is_current=True).first()
            if current_user:
                return current_user
        user = None
        if email_lower:
            user = session.query(User).filter_by(primary_email=email_lower, is_current=True).first()
        if not user and employee_id:
            user = session.query(User).filter_by(employee_id=employee_id, is_current=True).first()
        if not user:
            new_uid = uuid.uuid4()
            user = User(global_user_id=new_uid, full_name=name or (email_lower.split('@')[0] if email_lower else f'{source}_{external_id}'), primary_email=email_lower, employee_id=employee_id, sync_version=1, is_current=True)
            session.add(user)
            session.flush()
            logger.info(f'Created new user: {user.full_name} via {source}')
        if not mapping:
            mapping = IdentityMapping(global_user_id=user.global_user_id, source_system=source, external_user_id=str(external_id), external_username=name, external_email=email_lower)
            session.add(mapping)
            session.flush()
        return user