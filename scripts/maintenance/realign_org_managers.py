"""
组织负责人对齐维护脚本 (Organization Manager Alignment Tool)。

目的：
解决由于“数据同步先后顺序”导致的负责人缺失问题。例如，先同步了部门，但负责人用户尚未入库。
该脚本通过原始标识 (manager_raw_id) 重新匹配全局 OneID。
"""

import logging
from sqlalchemy.orm import Session
from devops_collector.models.base_models import Organization, User, IdentityMapping

logger = logging.getLogger(__name__)

def realign_org_managers(session: Session) -> dict:
    """全量扫描并对齐组织机构负责人。
    
    返回统计信息：{"success": int, "failed": int}
    """
    # 查找所有设置了原始标识但尚未绑定全局 ID 的组织
    pending_orgs = session.query(Organization).filter(
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
        mapping = session.query(IdentityMapping).filter_by(
            external_user_id=str(raw_id)
        ).first()
        if mapping:
            global_user_id = mapping.global_user_id
            
        # 策略 2: 工号 (如果 raw_id 看起来像工号)
        if not global_user_id:
            user = session.query(User).filter_by(employee_id=raw_id, is_current=True).first()
            if user:
                global_user_id = user.global_user_id
        
        # 策略 3: 邮箱 (如果 raw_id 看起来像邮箱)
        if not global_user_id and "@" in str(raw_id):
            user = session.query(User).filter_by(primary_email=raw_id.lower(), is_current=True).first()
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
        session.commit()
    
    return stats

if __name__ == "__main__":
    # 支持独立运行进行手动修复
    from devops_collector.core.database import SessionLocal
    with SessionLocal() as db:
        results = realign_org_managers(db)
        print(f"Manual Realignment Summary: {results}")
