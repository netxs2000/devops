"""初始化组织架构及负责人数据。

本脚本已重构为从 docs/organizations.csv 动态加载数据，不再包含任何硬编码。
执行方式:
    python scripts/init_organizations.py
"""

import csv
import logging
import sys
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session


# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))
from devops_collector.config import settings
from devops_collector.models import Organization
from scripts.utils import build_user_indexes, resolve_user


# 日志配置
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

CSV_FILE = Path(__file__).parent.parent / "docs" / "organizations.csv"


def init_organizations_from_csv(session: Session):
    """从 CSV 文件加载组织架构。"""
    if not CSV_FILE.exists():
        logger.warning(f"跳过组织初始化：找不到 CSV 文件 {CSV_FILE}")
        return

    logger.info(f"开始从 {CSV_FILE} 同步组织架构...")

    # 预加载用户索引 (邮箱 + 姓名)
    email_idx, name_idx = build_user_indexes(session)

    # 创建公司根节点 (L1)
    root_code = "ORG-HQ"
    root_org = session.query(Organization).filter_by(org_code=root_code).first()
    if not root_org:
        root_org = Organization(org_code=root_code, org_name="HQ", org_level=1, is_current=True)
        session.add(root_org)
        session.flush()
        logger.info(f"创建公司根节点: {root_code}")

    with open(CSV_FILE, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            system = row.get("体系", "").strip()
            center = row.get("中心", "").strip()
            dept = row.get("部门", "").strip()
            manager_val = row.get("负责人", row.get("负责人邮箱", "")).strip()

            manager_id = resolve_user(manager_val, email_idx, name_idx, "负责人")

            parent_org = root_org

            # 1. 中心层级 (L2) - 挂在公司根节点下
            if center:
                org_code_l2 = f"CTR-{center}"
                org_l2 = session.query(Organization).filter_by(org_code=org_code_l2).first()
                if not org_l2:
                    org_l2 = Organization(org_code=org_code_l2, org_name=center, org_level=2, parent_id=root_org.id, business_line=system, is_current=True)
                    session.add(org_l2)
                    session.flush()

                # 中心级负责人 (无部门的行)
                if manager_id and not dept:
                    org_l2.manager_user_id = manager_id

                parent_org = org_l2

            # 2. 部门层级 (L3) - 挂在中心下
            if dept:
                org_code_l3 = f"DEP-{dept}"
                org_l3 = session.query(Organization).filter_by(org_code=org_code_l3).first()
                if not org_l3:
                    org_l3 = Organization(org_code=org_code_l3, org_name=dept, org_level=3, parent_id=parent_org.id, business_line=system, is_current=True)
                    session.add(org_l3)
                    session.flush()

                if manager_id:
                    org_l3.manager_user_id = manager_id

    session.commit()
    logger.info("组织架构同步完成！")


def main():
    engine = create_engine(settings.database.uri)
    # Base.metadata.create_all(engine) # 已经在之前步骤创建过了
    with Session(engine) as session:
        init_organizations_from_csv(session)


if __name__ == "__main__":
    main()
