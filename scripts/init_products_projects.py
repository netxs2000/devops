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
    prod_map_obj = {}  # code -> Object
    prod_map_id = {}    # code -> Integer ID

    # 预加载组织和用户索引
    # 注意：Organization 现在使用 org_code
    orgs = {o.org_name: o.id for o in session.query(Organization).filter_by(is_current=True).all()}
    email_idx, name_idx = build_user_indexes(session)

    # 第一遍：创建产品并构建名称映射 (First Pass: Create Products & Build Map)
    product_rows = []
    with open(PRD_CSV, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get("产品名称", row.get("PRODUCT_NAME", "")).strip()
            if not name:
                continue

            # 业务主键
            prod_code = row.get("PRODUCT_ID", "").strip()
            if not prod_code:
                prod_code = f"PRD-{uuid.uuid5(uuid.NAMESPACE_DNS, name).hex[:8].upper()}"

            # 创建/更新产品对象 (使用 product_code)
            product = session.query(Product).filter_by(product_code=prod_code).first()
            if not product:
                product = Product(product_code=prod_code, product_name=name, product_description=name, version_schema="SemVer", is_current=True)
                session.add(product)

            # 更新属性 (Update Attributes)
            product.product_name = name
            product.node_type = row.get("节点类型", row.get("node_type", "APP")).strip().upper()
            product.category = row.get("产品分类", row.get("category", "")).strip()

            # 处理关联团队和人员
            team_name = row.get("负责团队", row.get("owner_team_id", "")).strip()
            if team_name in orgs:
                product.owner_team_id = orgs[team_name]
            elif team_name:
                # 尝试通过 org_code 匹配
                org_by_code = session.query(Organization).filter_by(org_code=team_name).first()
                if org_by_code:
                    product.owner_team_id = org_by_code.id

            # 人员解析
            for csv_col, attr in [
                ("产品经理", "product_manager_id"),
                ("开发经理", "dev_lead_id"),
                ("测试经理", "qa_lead_id"),
                ("发布经理", "release_lead_id"),
            ]:
                val = row.get(csv_col, "").strip()
                uid = resolve_user(val, email_idx, name_idx, csv_col)
                if uid:
                    setattr(product, attr, uid)

            session.flush()
            # 记录到映射表 (Code -> ID)
            prod_map_id[prod_code] = product.id
            prod_map_id[name] = product.id  # 支持名称查找
            
            # 暂存行数据以便第二遍处理父级关系
            product_rows.append((product, row))

    # 第二遍：解析父级关系 (Second Pass: Resolve Parent Relationships)
    for product, row in product_rows:
        parent_ref = row.get("上级产品ID", row.get("parent_product_id", "")).strip()
        if parent_ref:
            # 尝试通过 名称 或 Code 查找父级 ID
            parent_id = prod_map_id.get(parent_ref)
            if parent_id:
                # 防止自引用循环
                if parent_id != product.id:
                    product.parent_product_id = parent_id
                else:
                    logger.warning(f"Product {product.product_name} cannot set itself as parent.")
            else:
                logger.warning(f"Parent product '{parent_ref}' not found for product '{product.product_name}'. Ignoring.")
        else:
            product.parent_product_id = None

    session.commit()
    return prod_map_id


def init_projects(session: Session, prod_map_id):
    if not PROJ_CSV.exists():
        return
    logger.info("同步项目主数据...")

    email_idx, name_idx = build_user_indexes(session)
    # 预加载组织
    orgs_by_name = {o.org_name: o.id for o in session.query(Organization).filter_by(is_current=True).all()}

    with open(PROJ_CSV, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            code_val = row.get("项目代号", "").strip()
            name = row.get("项目名称", "").strip()
            prod_name = row.get("所属产品", "").strip()

            if not code_val or not name:
                continue

            proj_code = f"PROJ-{code_val}"
            project = session.query(ProjectMaster).filter_by(project_code=proj_code).first()
            if not project:
                project = ProjectMaster(project_code=proj_code, project_name=name, status="ACTIVE", is_current=True)
                session.add(project)

            # 关联部门 (通过名称反查ID)
            dept_name = row.get("负责部门", "").strip()
            if dept_name in orgs_by_name:
                project.org_id = orgs_by_name[dept_name]
            elif dept_name:
                 # 尝试通过 org_code 匹配
                org_by_code = session.query(Organization).filter_by(org_code=dept_name).first()
                if org_by_code:
                    project.org_id = org_by_code.id

            # 关联代码仓库
            # 建立 entity_topology 关联
            repo_url = row.get("主代码仓库URL", "").strip()
            if repo_url:
                # 确保 SystemRegistry 存在
                system = ensure_system_registry(session)

                # 必须先 flush 确保 project 有 ID
                session.flush()

                # 检查是否已存在关联
                topology = session.query(EntityTopology).filter_by(
                    project_id=project.id, 
                    external_resource_id=repo_url, 
                    element_type="source-code"
                ).first()

                if not topology:
                    topology = EntityTopology(
                        project_id=project.id,
                        service_id=None,
                        system_id=system.id,
                        external_resource_id=repo_url,
                        resource_name=urlparse(repo_url).path.strip("/").removesuffix(".git"),
                        element_type="source-code",
                        is_active=True,
                    )
                    session.add(topology)
                    logger.info(f"Created topology link for project {proj_code} -> {repo_url}")

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
            target_prod_id = prod_map_id.get(prod_name)
            if target_prod_id:
                rel = session.query(ProjectProductRelation).filter_by(project_id=project.id, product_id=target_prod_id).first()
                if not rel and project.org_id:
                    session.add(
                        ProjectProductRelation(
                            project_id=project.id,
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
