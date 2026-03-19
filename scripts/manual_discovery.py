"""手动触发发现与同步。"""

import logging
import sys
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session


# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))
from devops_collector.config import settings
from devops_collector.plugins.gitlab.gitlab_client import GitLabClient
from devops_collector.plugins.gitlab.models import GitLabProject
from devops_collector.plugins.zentao.client import ZenTaoClient
from devops_collector.plugins.zentao.models import ZenTaoProduct


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("ManualSync")


def run():
    engine = create_engine(settings.database.uri)
    with Session(engine) as session:
        # 1. 发现 GitLab 项目
        logger.info("Connecting to GitLab...")
        gl_client = GitLabClient(settings.gitlab.url, settings.gitlab.private_token, verify_ssl=False)
        # 不使用 test_connection，直接尝试获取第一页项目
        try:
            projects = gl_client._get("projects", params={"page": 1, "per_page": 50}).json()
            for p_data in projects:
                pid = p_data["id"]
                existing = session.query(GitLabProject).filter_by(id=pid).first()
                if not existing:
                    new_proj = GitLabProject(id=pid, name=p_data.get("name"), path_with_namespace=p_data.get("path_with_namespace"), sync_status="PENDING")
                    session.add(new_proj)
                    logger.info(f"Discovered GitLab project: {new_proj.name}")
            session.commit()
        except Exception as e:
            logger.error(f"Failed to discover GitLab: {e}")

        # 2. 发现 ZenTao 产品
        logger.info("Connecting to ZenTao...")
        zt_client = ZenTaoClient(settings.zentao.url, settings.zentao.token, account=settings.zentao.account, password=settings.zentao.password)
        try:
            if zt_client.test_connection():
                products = zt_client.get_products()
                for p_data in products:
                    pid = p_data.get("id")
                    if not pid:
                        continue
                    existing = session.query(ZenTaoProduct).filter_by(id=pid).first()
                    if not existing:
                        new_prod = ZenTaoProduct(id=pid, name=p_data.get("name"), code=p_data.get("code"), sync_status="PENDING")
                        session.add(new_prod)
                        logger.info(f"Discovered ZenTao product: {new_prod.name}")
                session.commit()
            else:
                logger.error("ZenTao login failed")
        except Exception as e:
            logger.error(f"Failed to discover ZenTao: {e}")


if __name__ == "__main__":
    run()
