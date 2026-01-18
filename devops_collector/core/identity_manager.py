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
        3. 如果没找到，严格按 Email (主数据邮箱) 检索现有 User。
        4. 如果按 Email 没找到，且提供了工号，则按工号检索。
        5. 如果匹配成功，建立新的 Mapping 关系。
        6. 如果所有主数据特征均未匹配，创建一个标记为 'EXTERNAL' 的临时用户，待后续手动治理。
        
        Args:
            session: 数据库会话。
            source: 系统来源 (如 'gitlab', 'zentao')。
            external_id: 外部系统原始 ID (如 GitLab ID 或 禅道 account)。
            email: 用户邮箱。
            name: 用户名 (可选)。
            employee_id: 工号 (可选)。
            
        Returns:
            User: 关联后的当前有效用户对象。
        """
        email_lower = email.lower().strip() if email else None
        ext_id_str = str(external_id).strip()
        
        # 1. 查找现有映射
        mapping = session.query(IdentityMapping).filter_by(
            source_system=source, 
            external_user_id=ext_id_str
        ).first()
        
        if mapping:
            current_user = session.query(User).filter_by(
                global_user_id=mapping.global_user_id, 
                is_current=True
            ).first()
            if current_user:
                return current_user

        # 2. 尝试从主数据对齐 (Email 优先)
        user = None
        if email_lower:
            user = session.query(User).filter_by(primary_email=email_lower, is_current=True).first()
        
        # 3. 如果 Email 没中，试工号
        if not user and employee_id:
            user = session.query(User).filter_by(employee_id=employee_id, is_current=True).first()
            
        # 4. 如果还没中，尝试通过姓名匹配 (仅限唯一匹配)
        if not user and name:
            potential_users = session.query(User).filter_by(full_name=name, is_current=True).all()
            if len(potential_users) == 1:
                user = potential_users[0]
                logger.warning(f"用户 {name} 通过姓名匹配到主数据 (ID: {user.employee_id})")

        # 5. 如果彻底找不到，创建一个待对齐的外部用户
        if not user:
            new_uid = uuid.uuid4()
            user = User(
                global_user_id=new_uid,
                full_name=name or f"Unknown_{source}_{ext_id_str}",
                primary_email=email_lower,
                employee_id=employee_id,
                is_active=False,       # 非主大数据导入，默认为非激活状态
                is_survivor=False,     # 标记为非金数据用户
                sync_version=1,
                is_current=True
            )
            session.add(user)
            session.flush()
            logger.info(f'创建外部临时用户: {user.full_name} ({source}:{ext_id_str})，需手动治理对齐。')

        # 6. 建立映射关系
        if not mapping:
            mapping = IdentityMapping(
                global_user_id=user.global_user_id,
                source_system=source,
                external_user_id=ext_id_str,
                external_username=name,
                external_email=email_lower,
                mapping_status='AUTO' if user.is_survivor else 'PENDING',
                confidence_score=1.0 if user.is_survivor else 0.5
            )
            session.add(mapping)
            session.flush()
            
        return user