"""统一身份管理服务 (Identity Manager)

负责在多系统采集过程中进行人员身份对齐与去重，支持 SCD Type 2。
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
    def get_or_create_user(
        session: Session, 
        source: str, 
        external_id: str, 
        email: Optional[str] = None, 
        name: Optional[str] = None,
        employee_id: Optional[str] = None
    ) -> User:
        """根据外部账号解析并获取全局用户。
        
        策略:
        1. 优先从 identity_mappings 表查找匹配 (source, external_id) 的记录。
        2. 如果找到了 Mapping，则返回对应的当前有效 User (is_current=True)。
        3. 如果没找到，且提供了 email，则从 mdm_identities 表尝试按 primary_email 匹配当前用户。
        4. 如果通过 email 匹配到了 User，则为该 User 创建新的 IdentityMapping。
        5. 如果还是没找到，则创建全新的 User (SCD Type 2 初始化) 和对应的 IdentityMapping。
        
        Args:
            session: 数据库会话
            source: 系统来源 (如 'jira', 'zentao', 'gitlab')
            external_id: 外部系统账号 (如 'admin', '1001')
            email: 用户邮箱 (用于跨源识别的关键字段)
            name: 用户显示姓名 (可选)
            employee_id: 员工工号 (可选，辅助匹配)
            
        Returns:
            User: 关联后的全局当前用户对象
        """
        # 1. 尝试从映射表查找
        mapping = session.query(IdentityMapping).filter_by(
            source_system=source, external_user_id=str(external_id)
        ).first()
        
        if mapping:
            # 返回该 OneID 对应的当前有效记录
            current_user = session.query(User).filter_by(
                global_user_id=mapping.global_user_id, 
                is_current=True
            ).first()
            if current_user:
                return current_user
            
        # 2. 尝试通过 Email 跨系统对齐 (仅查找当前有效的)
        user = None
        if email:
            user = session.query(User).filter_by(
                primary_email=email.lower(), 
                is_current=True
            ).first()
            if user:
                logger.debug(f"Identity matched by email: {email} for source: {source}")
        
        if not user and employee_id:
            user = session.query(User).filter_by(
                employee_id=employee_id, 
                is_current=True
            ).first()
            if user:
                logger.debug(f"Identity matched by employee_id: {employee_id} for source: {source}")
        
        # 3. 如果没匹配到，创建新用户
        if not user:
            new_global_id = uuid.uuid4()
            user = User(
                global_user_id=new_global_id,
                full_name=name or (email.split('@')[0] if email else f"{source}_{external_id}"),
                primary_email=email.lower() if email else None,
                employee_id=employee_id,
                is_active=True,
                is_survivor=True,
                sync_version=1,
                is_current=True,
                is_deleted=False
            )
            session.add(user)
            session.flush() # 获取 ID
            logger.info(f"Created new global user: {user.full_name} (ID: {new_global_id})")

        # 4. 建立新的映射记录 (如果尚不存在)
        if not mapping:
            mapping = IdentityMapping(
                global_user_id=user.global_user_id,
                source_system=source,
                external_user_id=str(external_id),
                external_username=name,
                external_email=email.lower() if email else None
            )
            session.add(mapping)
            session.flush()
        
        return user
