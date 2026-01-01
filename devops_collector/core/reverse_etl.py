"""Reverse ETL 服务模块

负责将 dbt 计算出来的分析结果（如 Talent Radar 分数）回写到业务主数据表（如 mdm_identities）。
实现数据闭环，让分析结果能够直接触达业务流程。
"""
import logging
from sqlalchemy import text
from sqlalchemy.orm import Session
from devops_collector.models.base_models import User
from devops_collector.core.services import close_current_and_insert_new

logger = logging.getLogger(__name__)

def sync_talent_tags_to_mdm(session: Session, threshold: float = 50.0) -> int:
    """将高潜力人才标签同步回 mdm_identities 表。
    
    1. 从 dbt 生成的 marts.fct_talent_radar 视图中查询数据。
    2. 识别 talent_influence_index 超过阈值的用户。
    3. 调用 SCD Type 2 服务更新 mdm_identities 表，添加 'HighPotential' 标签。
    
    Args:
        session: 数据库会话
        threshold: 认定为高潜人才的分数阈值
    
    Returns:
        int: 更新的用户数量
    """
    # 1. 查询 dbt 计算结果
    # 注意：dbt_project.yml 配置了 marts 层的 schema 为 'marts'
    query = text("""
        SELECT user_id, talent_influence_index 
        FROM marts.fct_talent_radar 
        WHERE talent_influence_index >= :threshold
    """)
    
    try:
        results = session.execute(query, {"threshold": threshold}).mappings().all()
    except Exception as e:
        logger.error(f"Failed to query dbt results from marts.fct_talent_radar: {e}")
        return 0

    updated_count = 0
    for row in results:
        user_id = row['user_id']
        score = row['talent_influence_index']
        
        # 2. 获取当前用户记录进行更新 (SCD Type 2)
        current_user = session.query(User).filter_by(global_user_id=user_id, is_current=True).first()
        
        if current_user:
            # 准备新数据
            new_tags = current_user.raw_data or {}
            if not isinstance(new_tags, dict):
                new_tags = {}
            
            # 添加标签
            new_tags['talent_influence_score'] = float(score)
            new_tags['is_high_potential'] = True
            
            new_data = {
                "raw_data": new_tags,
                "sync_version": current_user.sync_version
            }
            
            try:
                close_current_and_insert_new(
                    session, 
                    User, 
                    {"global_user_id": user_id}, 
                    new_data
                )
                updated_count += 1
            except Exception as e:
                logger.error(f"Failed to update user {user_id} during reverse ETL: {e}")
                session.rollback()
                continue
                
    session.commit()
    logger.info(f"Reverse ETL completed: {updated_count} users tagged as HighPotential")
    return updated_count

def sync_aligned_entities_to_mdm(session: Session) -> int:
    """将 dbt 自动对齐的实体关系回写到 mdm_entities_topology 表。
    
    逻辑：
    1. 从 intermediate.int_entity_alignment 中抓取对齐结果。
    2. 如果 alignment_strategy 是有效匹配且当前 topology 为空，则回写。
    """
    query = text("""
        SELECT gitlab_project_id, master_entity_id, alignment_strategy 
        FROM intermediate.int_entity_alignment 
        WHERE master_entity_id IS NOT NULL 
          AND alignment_strategy IN ('EXACT_NAME', 'FUZZY_PATH')
    """)
    
    try:
        results = session.execute(query).mappings().all()
    except Exception as e:
        logger.error(f"Failed to query entity alignments: {e}")
        return 0

    from devops_collector.models.base_models import EntityTopology
    updated_count = 0
    
    for row in results:
        repo_id = str(row['gitlab_project_id'])
        entity_id = row['master_entity_id']
        
        # 查找目标实体
        target = session.query(EntityTopology).filter_by(entity_id=entity_id, is_current=True).first()
        
        if target and not target.internal_id:
            # 准备新数据：更新 internal_id 以完成“硬连接”对齐
            new_data = {
                "internal_id": repo_id,
                "sync_version": target.sync_version
            }
            try:
                close_current_and_insert_new(
                    session,
                    EntityTopology,
                    {"entity_id": entity_id},
                    new_data
                )
                updated_count += 1
            except Exception as e:
                logger.error(f"Failed to align entity {entity_id}: {e}")
                continue
                
    session.commit()
    logger.info(f"Entity Alignment Reverse ETL completed: {updated_count} entities aligned")
    return updated_count

def sync_shadow_it_findings(session: Session) -> int:
    """将 dbt 发现的影子系统记录回写到 mdm_compliance_issues 表。
    
    逻辑：
    1. 从 marts.fct_shadow_it_discovery 中抓取风险项。
    2. 如果该实体（GitLab Project ID）尚未记录在案，则创建 OPEN 状态的合规问题。
    """
    query = text("""
        SELECT gitlab_project_id, project_name, shadow_it_status, last_30d_activity_count 
        FROM marts.fct_shadow_it_discovery 
        WHERE shadow_it_status IN ('HIGH_RISK_SHADOW', 'ACTIVE_UNREGISTERED')
    """)
    
    try:
        results = session.execute(query).mappings().all()
    except Exception as e:
        logger.error(f"Failed to query shadow IT findings: {e}")
        return 0

    from devops_collector.models.base_models import ComplianceIssue
    created_count = 0
    
    for row in results:
        repo_id = str(row['gitlab_project_id'])
        
        # 检查是否已有相同实体的影子系统记录
        existing = session.query(ComplianceIssue).filter_by(
            entity_id=repo_id, 
            issue_type='SHADOW_IT',
            status='OPEN'
        ).first()
        
        if not existing:
            # 创建新问题
            new_issue = ComplianceIssue(
                issue_type='SHADOW_IT',
                severity='HIGH' if row['shadow_it_status'] == 'HIGH_RISK_SHADOW' else 'MEDIUM',
                entity_id=repo_id,
                description=f"发现影子系统：仓库 '{row['project_name']}' (ID: {repo_id}) 活跃度高但未在 MDM 注册。",
                metadata_payload={
                    "status_label": row['shadow_it_status'],
                    "activity_count": row['last_30d_activity_count']
                }
            )
            session.add(new_issue)
            created_count += 1
                
    session.commit()
    logger.info(f"Shadow IT Reverse ETL completed: {created_count} new risks detected")
    return created_count
