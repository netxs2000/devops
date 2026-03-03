"""初始化产品主数据 (MDM_PRODUCT)。

本脚本根据用户提供的产品目录图，自动完成以下任务：
1. 录入全量产品信息（代号、名称、产品线）。
2. 建立产品与所属部门（中心）的关联。

执行方式:
    python scripts/init_products.py
"""

import logging
import sys
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session


# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))
from devops_collector.config import settings
from devops_collector.models import Base, Organization, Product
from scripts.utils import build_user_indexes, resolve_user


# 日志配置
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# 产品原始数据 (产品代号, 产品名称, 归属中心名称, 负责人姓名)
PRODUCT_RAW_DATA = [
    ("PL001", "预算一体化-江苏", "财政研发中心", "王斌"),
    ("PL002", "预算一体化-通用", "财政研发中心", "刘洪昌"),
    ("PL003", "预算一体化-浙江", "财政研发中心", "刘洪昌"),
    ("PL004", "预算一体化-海南", "政务研发中心", "李水珍"),
    ("PL005", "财政绩效", "智慧云政务研发中心", "赵孝涛"),
    ("PL006", "单位核算", "智慧云政务研发中心", "张聚锁"),
    ("PL007", "轻松报", "智慧云政务研发中心", "高明"),
    ("PL008", "涉企分析", "智慧云政务研发中心", "蔡道斌"),
    ("PL009", "项目枢纽", "政务研发中心", "李水珍"),
    ("PL010", "政务", "政务研发中心", "李水珍"),
    ("PL011", "非税", "互联网与协同业务拓展中心", "周景伟"),
    ("PL012", "协同", "互联网与协同业务拓展中心", "皎海军"),
    ("PL013", "大数据", "大数据及AI业务拓展中心", "马世杰"),
    ("PL014", "行业业务", "行业业务拓展中心", "杜崇明"),
    ("PL015", "创新业务", "创新业务拓展中心", "王海峰"),
]


def init_products():
    """解析数据并初始化产品主数据。"""
    engine = create_engine(settings.database.uri)
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        logger.info("开始初始化全量产品目录...")

        # 构建用户双索引 (邮箱 + 姓名)
        email_idx, name_idx = build_user_indexes(session)

        for p_id, p_name, owner_name, manager_name in PRODUCT_RAW_DATA:
            # 1. 匹配所属部门 ID
            owner_id = f"CTR-{owner_name}"
            org = session.query(Organization).filter_by(org_id=owner_id).first()
            if not org:
                logger.warning(f"产品 {p_name} 的归属部门 {owner_name} 不存在。")
                owner_id = None

            # 2. 查找负责人 (通过姓名或邮箱匹配)
            mgr_user_id = resolve_user(manager_name, email_idx, name_idx, "产品负责人")

            # 3. 创建/更新产品
            existing = session.query(Product).filter_by(product_id=p_id).first()
            if not existing:
                product = Product(
                    product_id=p_id,
                    product_name=p_name,
                    product_description=f"华青 {p_name} 核心产品",
                    category="Core Product",
                    version_schema="SemVer",
                    lifecycle_status="Active",
                    owner_team_id=owner_id,
                    product_manager_id=mgr_user_id,
                )
                session.add(product)
                logger.info(f"已创建产品: {p_name} ({p_id})")
            else:
                existing.product_name = p_name
                existing.owner_team_id = owner_id
                if mgr_user_id:
                    existing.product_manager_id = mgr_user_id
                logger.info(f"已更新产品: {p_name}")

        session.commit()
        logger.info("产品目录初始化完成！")


if __name__ == "__main__":
    init_products()
