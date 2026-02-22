import csv
import logging
import os

from sqlalchemy.orm import Session

from devops_collector.models.database import SessionLocal
from devops_collector.plugins.jenkins.models import JenkinsJob


# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

JENKINS_MAP_CSV = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'docs', 'jenkins_job_map.csv')

def init_jenkins_links():
    """根据 CSV 映射文件初始化 Jenkins Job 与 MDM 资产的关联。支持 Folder 级继承。"""
    if not os.path.exists(JENKINS_MAP_CSV):
        logger.warning(f"找不到映射文件: {JENKINS_MAP_CSV}")
        return

    session: Session = SessionLocal()
    try:
        logger.info("开始同步 Jenkins Job 关联...")
        mappings = []
        with open(JENKINS_MAP_CSV, encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                full_name = row.get('job_full_name', '').strip()
                if full_name:
                    mappings.append(row)

        for row in mappings:
            job_name = row['job_full_name']
            mdm_proj = row.get('mdm_project_id')
            mdm_prod = row.get('mdm_product_id')
            is_deploy = row.get('is_deployment', 'false').lower() == 'true'
            env = row.get('deployment_env')

            # 处理继承逻辑：如果 job_name 以 / 结尾，视为文件夹/前缀匹配
            if job_name.endswith('/'):
                target_jobs = session.query(JenkinsJob).filter(JenkinsJob.full_name.like(f"{job_name}%")).all()
                for job in target_jobs:
                    _update_job(job, mdm_proj, mdm_prod, is_deploy, env)
                    logger.info(f"继承继承关联: {job.full_name} <- Folder {job_name}")
            else:
                job = session.query(JenkinsJob).filter_by(full_name=job_name).first()
                if not job:
                    # 创建占位
                    job = JenkinsJob(full_name=job_name, name=job_name.split('/')[-1])
                    session.add(job)
                _update_job(job, mdm_proj, mdm_prod, is_deploy, env)
                logger.info(f"直接关联: {job_name} -> MDM")

        session.commit()
        logger.info("Jenkins 拓扑关联同步完成。")
    except Exception as e:
        session.rollback()
        logger.error(f"同步失败: {e}")
    finally:
        session.close()

def _update_job(job, proj_id, prod_id, is_deploy, env):
    """更新单个 Job 的 MDM 属性。"""
    if proj_id: job.mdm_project_id = proj_id
    if prod_id: job.mdm_product_id = prod_id
    job.is_deployment = is_deploy
    if env: job.deployment_env = env

if __name__ == "__main__":
    init_jenkins_links()
