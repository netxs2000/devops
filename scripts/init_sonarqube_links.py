import csv
import os
import logging
from sqlalchemy.orm import Session
from devops_collector.models.database import SessionLocal
from devops_collector.plugins.sonarqube.models import SonarProject
from devops_collector.models.base_models import ProjectMaster, Product

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

SONAR_MAP_CSV = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'docs', 'sonarqube_project_map.csv')

def init_sonarqube_links():
    """根据 CSV 映射文件初始化 SonarQube 项目与 MDM 资产的关联。"""
    if not os.path.exists(SONAR_MAP_CSV):
        logger.warning(f"找不到映射文件: {SONAR_MAP_CSV}")
        return

    session: Session = SessionLocal()
    try:
        logger.info("开始同步 SonarQube 项目关联...")
        with open(SONAR_MAP_CSV, mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                sonar_key = row.get('sonar_project_key', '').strip()
                mdm_proj_id = row.get('mdm_project_id', '').strip()
                mdm_prod_id = row.get('mdm_product_id', '').strip()

                if not sonar_key:
                    continue

                # 1. 查找或创建 Sonar 项目占位符 (如果尚未同步)
                project = session.query(SonarProject).filter_by(key=sonar_key).first()
                if not project:
                    project = SonarProject(key=sonar_key, name=sonar_key.split(':')[-1])
                    session.add(project)
                    logger.info(f"创建占位节点: {sonar_key}")

                # 2. 验证并更新 MDM 关联
                if mdm_proj_id:
                    exists = session.query(ProjectMaster).filter_by(project_id=mdm_proj_id).first()
                    if exists:
                        project.mdm_project_id = mdm_proj_id
                    else:
                        logger.warning(f"MDM 项目 {mdm_proj_id} 不存在")

                if mdm_prod_id:
                    exists = session.query(Product).filter_by(product_id=mdm_prod_id).first()
                    if exists:
                        project.mdm_product_id = mdm_prod_id
                    else:
                        logger.warning(f"MDM 产品 {mdm_prod_id} 不存在")

                logger.info(f"关联成功: {sonar_key} -> Proj:{mdm_proj_id}, Prod:{mdm_prod_id}")

        session.commit()
        logger.info("SonarQube 拓扑关联同步完成。")
    except Exception as e:
        session.rollback()
        logger.error(f"同步失败: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    init_sonarqube_links()
