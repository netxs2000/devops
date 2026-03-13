"""初始化产品与项目主数据。

本脚本已重构为从 docs/products.csv 和 docs/projects.csv 动态加载。
"""

import csv
import logging
import sys
import uuid
from pathlib import Path
from urllib.parse import urlparse

from sqlalchemy import create_engine
from sqlalchemy.orm import Session


# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))
from devops_collector.config import settings
from devops_collector.models import (
    EntityTopology,
    Organization,
    Product,
    ProjectMaster,
    ProjectProductRelation,
    SystemRegistry,
)
from scripts.utils import build_user_indexes, resolve_user


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

PRD_CSV = Path(__file__).parent.parent / "docs" / "products.csv"
PROJ_CSV = Path(__file__).parent.parent / "docs" / "projects.csv"


def ensure_system_registry(session: Session, code="gitlab-prod", name="生产环境GitLab"):
    system = session.query(SystemRegistry).filter_by(system_code=code).first()
    if not system:
        system = SystemRegistry(system_code=code, system_name=name, system_type="VCS", is_active=True)
        session.add(system)
        session.flush()
    return system


def init_products(session: Session):
    if not PRD_CSV.exists():
        return {}
    logger.info("同步产品主数据...")
    prod_map = {}

    # 预加载组织和用户索引
    orgs = {o.org_name: o.org_id for o in session.query(Organization).filter_by(is_current=True).all()}
    email_idx, name_idx = build_user_indexes(session)

    # 第一遍：创建产品并构建名称映射 (First Pass: Create Products & Build Map)
    product_rows = []
    with open(PRD_CSV, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get("产品名称", row.get("PRODUCT_NAME", "")).strip()
            if not name:
                continue

            prod_id = row.get("PRODUCT_ID", "").strip()
            # 自动生成ID逻辑
            final_id = prod_id if prod_id else f"PRD-{uuid.uuid5(uuid.NAMESPACE_DNS, name).hex[:8].upper()}"

            # 创建/更新产品对象
            product = session.query(Product).filter_by(product_name=name).first()
            if not product:
                product = Product(product_id=final_id, product_name=name, product_description=name, version_schema="SemVer")
                session.add(product)

            # 更新属性 (Update Attributes)
            product.node_type = row.get("节点类型", row.get("node_type", "APP")).strip().upper()
            product.category = row.get("产品分类", row.get("category", "")).strip()

            # 处理关联团队和人员
            team_name = row.get("负责团队", row.get("owner_team_id", "")).strip()
            if team_name in orgs:
                product.owner_team_id = orgs[team_name]

            # 人员解析
            pm_val = row.get("产品经理", row.get("pm_email", "")).strip()
            uid = resolve_user(pm_val, email_idx, name_idx, "产品经理")
            if uid:
                product.product_manager_id = uid

            dev_val = row.get("开发经理", "").strip()
            uid = resolve_user(dev_val, email_idx, name_idx, "开发经理")
            if uid:
                product.dev_lead_id = uid

            qa_val = row.get("测试经理", "").strip()
            uid = resolve_user(qa_val, email_idx, name_idx, "测试经理")
            if uid:
                product.qa_lead_id = uid

            rel_val = row.get("发布经理", "").strip()
            uid = resolve_user(rel_val, email_idx, name_idx, "发布经理")
            if uid:
                product.release_lead_id = uid

            session.flush()
            # 记录到映射表 (Name -> ID) 和 (ID -> ID)
            prod_map[name] = product.product_id
            prod_map[product.product_id] = product.product_id

            # 暂存行数据以便第二遍处理父级关系
            product_rows.append((product, row))

    # 第二遍：解析父级关系 (Second Pass: Resolve Parent Relationships)
    for product, row in product_rows:
        parent_ref = row.get("上级产品ID", row.get("parent_product_id", "")).strip()
        if parent_ref:
            # 尝试通过 名称 或 ID 查找父级 ID
            parent_id = prod_map.get(parent_ref)
            if parent_id:
                # 防止自引用循环
                if parent_id != product.product_id:
                    product.parent_product_id = parent_id
                else:
                    logger.warning(f"Product {product.product_name} cannot set itself as parent.")
            else:
                logger.warning(f"Parent product '{parent_ref}' not found for product '{product.product_name}'. Ignoring.")
        else:
            product.parent_product_id = None

    session.commit()
    return prod_map


def init_projects(session: Session, prod_map):
    if not PROJ_CSV.exists():
        return
    logger.info("同步项目主数据...")

    email_idx, name_idx = build_user_indexes(session)

    with open(PROJ_CSV, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            code = row.get("项目代号", "").strip()
            name = row.get("项目名称", "").strip()
            prod_name = row.get("所属产品", "").strip()

            if not code or not name:
                continue

            proj_id = f"PROJ-{code}"
            project = session.query(ProjectMaster).filter_by(project_id=proj_id).first()
            if not project:
                project = ProjectMaster(project_id=proj_id, project_name=name, status="ACTIVE", is_current=True)
                session.add(project)

            # 关联部门 (通过名称反查ID)
            dept_name = row.get("负责部门", "").strip()
            if dept_name:
                org = session.query(Organization).filter_by(org_name=dept_name).first()
                if org:
                    project.org_id = org.org_id

            # 关联代码仓库
            # 建立 entity_topology 关联
            repo_url = row.get("主代码仓库URL", "").strip()
            if repo_url:
                # 确保 SystemRegistry 存在
                system = ensure_system_registry(session)

                # 检查是否已存在关联
                topology = session.query(EntityTopology).filter_by(project_id=proj_id, external_resource_id=repo_url, element_type="source-code").first()

                if not topology:
                    topology = EntityTopology(
                        project_id=proj_id,
                        service_id=None,
                        system_code=system.system_code,
                        external_resource_id=repo_url,
                        resource_name=urlparse(repo_url).path.strip("/").removesuffix(".git"),
                        element_type="source-code",
                        is_active=True,
                    )
                    session.add(topology)
                    logger.info(f"Created topology link for project {proj_id} -> {repo_url}")

                # 保留原来的 description 逻辑作为备份显示
                if not project.description:
                    project.description = ""
                if repo_url not in project.description:
                    project.description += f"\nRepo: {repo_url}"

            # 关联项目成员 (支持邮箱或姓名)
            for csv_col, attr in [
                ("项目经理", "pm_user_id"),
                ("产品经理", "product_owner_id"),
                ("开发经理", "dev_lead_id"),
                ("测试经理", "qa_lead_id"),
                ("发布经理", "release_lead_id"),
            ]:
                val = row.get(csv_col, "").strip()
                uid = resolve_user(val, email_idx, name_idx, csv_col)
                if uid:
                    setattr(project, attr, uid)

            session.flush()
            # 建立产品关联
            target_prod_id = prod_map.get(prod_name)
            if target_prod_id:
                rel = session.query(ProjectProductRelation).filter_by(project_id=proj_id, product_id=target_prod_id).first()
                if not rel and project.org_id:
                    session.add(
                        ProjectProductRelation(
                            project_id=proj_id,
                            product_id=target_prod_id,
                            org_id=project.org_id,
                            relation_type="PRIMARY",
                        )
                    )
    session.commit()


def main():
    engine = create_engine(settings.database.uri)
    with Session(engine) as session:
        pm = init_products(session)
        init_projects(session, pm)


if __name__ == "__main__":
    main()
