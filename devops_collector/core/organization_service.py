"""统一组织架构管理服务 (MDM Organization Service)。

负责跨系统(如企业微信、禅道、Jira)的部门架构同步、拓扑维护与负责人对齐。
该服务严格遵循 AGENTS.md 3.4 节的“两阶段对齐规程”：
Phase 1: 拓扑同步 (Upsert 部门及其父子关系，记录 manager_raw_id)
Phase 2: 延迟关联 (使用独立的对齐逻辑绑定 manager_user_id)
"""

import logging
from typing import Any, Optional
from sqlalchemy.orm import Session
from devops_collector.models.base_models import Organization, User, IdentityMapping

logger = logging.getLogger(__name__)

class OrganizationService:
    """组织架构核心业务服务。"""

    def __init__(self, session: Session):
        self.session = session

    def upsert_organization(
        self, 
        org_code: str, 
        org_name: str, 
        org_level: int = 1,
        parent_org_code: Optional[str] = None,
        manager_raw_id: Optional[str] = None,
        source: str = "unknown"
    ) -> Organization:
        """Phase 1: 幂等同步部门基本信息。
        
        Args:
            org_code: 来源系统中的部门唯一标识 (如 WeCom DeptID)。
            org_name: 部门显示名称。
            org_level: 组织层级 (1=公司, 2=部门, 3=团队)。
            parent_org_code: 上级部门的原始代码 (用于延迟绑定 parent_id)。
            manager_raw_id: 负责人原始标识 (如 WeCom UserID / 工号)。
            source: 数据来源标识 (如 'wecom' / 'zentao')。
            
        Returns:
            Organization: 已同步的部门对象。
        """
        org = self.session.query(Organization).filter_by(
            org_code=org_code, is_current=True
        ).first()

        if not org:
            org = Organization(
                org_code=org_code,
                org_name=org_name,
                org_level=org_level,
                manager_raw_id=manager_raw_id,
                is_current=True,
                sync_version=1
            )
            self.session.add(org)
            logger.info(f"Created Org: {org_name} from {source}")
        else:
            org.org_name = org_name
            org.org_level = org_level
            # 只有在提供了新值且原值为空时，才更新 raw_id
            if manager_raw_id and not org.manager_user_id:
                org.manager_raw_id = manager_raw_id

        # 处理父子层级 (Topological resolution)
        if parent_org_code:
            parent = self.session.query(Organization).filter_by(
                org_code=parent_org_code, is_current=True
            ).first()
            if parent:
                org.parent_id = parent.id
            else:
                logger.debug(f"Parent org {parent_org_code} not found yet for {org_code}, will be linked in next cycle.")

        self.session.flush()
        return org

    def realign_all_managers(self) -> dict:
        """Phase 2: 批量对齐部门负责人。
        
        扫描所有设置了原始标识但尚未绑定全局 ID 的组织进行物理外键绑定。
        """
        # 查找所有设置了原始标识但尚未绑定全局 ID 的组织
        pending_orgs = self.session.query(Organization).filter(
            Organization.manager_user_id == None,
            Organization.manager_raw_id != None,
            Organization.is_current == True
        ).all()

        stats = {"success": 0, "failed": 0}

        for org in pending_orgs:
            raw_id = org.manager_raw_id
            
            # 匹配策略优先级：
            # 1. 优先尝试从 IdentityMapping 表找外部系统映射 (适用于第三方企业微信/LDAP ID)
            # 2. 其次尝试直接匹配工号 (employee_id)
            # 3. 最后尝试匹配邮箱 (primary_email)
            
            global_user_id = None
            
            # 策略 1: 映射表
            mapping = self.session.query(IdentityMapping).filter_by(
                external_user_id=str(raw_id)
            ).first()
            if mapping:
                global_user_id = mapping.global_user_id
                
            # 策略 2: 工号
            if not global_user_id:
                user = self.session.query(User).filter_by(employee_id=raw_id, is_current=True).first()
                if user:
                    global_user_id = user.global_user_id
            
            # 策略 3: 邮箱
            if not global_user_id and "@" in str(raw_id):
                user = self.session.query(User).filter_by(primary_email=raw_id.lower(), is_current=True).first()
                if user:
                    global_user_id = user.global_user_id

            if global_user_id:
                org.manager_user_id = global_user_id
                stats["success"] += 1
                logger.info(f"Successfully aligned manager for org '{org.org_name}' using identifier '{raw_id}'")
            else:
                stats["failed"] += 1
                logger.debug(f"Failed to align manager for org '{org.org_name}' with identifier '{raw_id}'")

        if stats["success"] > 0:
            self.session.flush()
        
        return stats

    def get_org_by_code(self, org_code: str) -> Optional[Organization]:
        """按外部代码查找部门。"""
        return self.session.query(Organization).filter_by(
            org_code=org_code, is_current=True
        ).first()

    def get_full_hierarchy(self, root_code: Optional[str] = None):
        """获取全量拓扑树 (用于前端视图展现)。"""
        # 实际业务逻辑可以调用 common/algorithms.py 里的树遍历
        pass
