"""统一身份管理服务 (Identity Manager)

负责在多系统采集过程中进行人员身份对齐与去重。
"""
import logging
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
        username: Optional[str] = None
    ) -> User:
        """根据外部账号解析并获取全局用户。
        
        策略:
        1. 优先从 identity_mappings 表查找匹配 (source, external_id) 的记录。
        2. 如果没找到，且提供了 email，则从 users 表尝试按 email 匹配。
        3. 如果通过 email 匹配到了 User，则为该 User 创建新的 IdentityMapping。
        4. 如果还是没找到，则创建全新的 User 和对应的 IdentityMapping。
        
        Args:
            session: 数据库会话
            source: 系统来源 (如 'jira', 'zentao', 'gitlab')
            external_id: 外部系统账号 (如 'admin', '1001')
            email: 用户邮箱 (用于跨源识别的关键字段)
            name: 用户显示姓名 (可选)
            username: 用户在本系统中的原始用户名 (可选，辅助匹配)
            
        Returns:
            User: 关联后的全局用户对象
        """
        # 1. 尝试从映射表查找
        mapping = session.query(IdentityMapping).filter_by(
            source=source, external_id=str(external_id)
        ).first()
        
        if mapping:
            return mapping.user
            
        # 2. 尝试通过 Email 跨系统对齐
        user = None
        if email:
            user = session.query(User).filter_by(email=email.lower()).first()
            if user:
                logger.debug(f"Identity matched by email: {email} for source: {source}")
        
        if not user and username:
            user = session.query(User).filter_by(username=username).first()
            if user:
                logger.debug(f"Identity matched by username: {username} for source: {source}")
        
        # 3. 如果没匹配到，创建新用户
        if not user:
            # 这里的 username 只是一个占位符，优先使用传入的 username
            final_username = username or (email.split('@')[0] if email else f"{source}_{external_id}")
            # 检查 username 是否冲突
            base_username = final_username
            counter = 1
            while session.query(User).filter_by(username=final_username).first():
                final_username = f"{base_username}_{counter}"
                counter += 1
                
            user = User(
                username=final_username,
                name=name or final_username,
                email=email.lower() if email else None
            )
            session.add(user)
            session.flush() # 获取 ID
            logger.info(f"Created new global user: {username}")

        # 4. 建立新的映射记录
        mapping = IdentityMapping(
            user_id=user.id,
            source=source,
            external_id=str(external_id),
            external_name=name,
            email=email.lower() if email else None
        )
        session.add(mapping)
        session.flush()
        
        return user
