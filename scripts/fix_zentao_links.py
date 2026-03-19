# -*- coding: utf-8 -*-
import csv
import os
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


# Add project root to path
sys.path.append(os.getcwd())

from devops_collector.config import settings
from devops_collector.models import EntityTopology
from devops_collector.plugins.zentao.models import ZenTaoExecution, ZenTaoProduct


def main():
    engine = create_engine(settings.database.uri)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # 1. Sync Products
        product_csv = "docs/zentao_product_map.csv"
        if os.path.exists(product_csv):
            print(f"Syncing products from {product_csv}...")
            with open(product_csv, encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    zt_id = row.get("zentao_product_id")
                    mdm_id = row.get("mdm_product_id")
                    if zt_id and mdm_id:
                        # 尝试通过 ID 或 Code 查找产品
                        p = None
                        if zt_id.isdigit():
                            p = session.query(ZenTaoProduct).filter_by(id=int(zt_id)).first()

                        if not p:
                            p = session.query(ZenTaoProduct).filter(ZenTaoProduct.code == zt_id).first()

                        if p:
                            p.mdm_product_id = mdm_id
                            # 同步更新外部资源 ID 匹配
                            zt_id_actual = str(p.id)
                        else:
                            zt_id_actual = zt_id

                        # Update topology
                        topo = (
                            session.query(EntityTopology)
                            .filter_by(
                                system_code="zentao-prod",
                                resource_name=row.get("zentao_product_name"),  # 冗余匹配
                            )
                            .first()
                        )

                        if not topo:
                            topo = session.query(EntityTopology).filter_by(system_code="zentao-prod", external_resource_id=zt_id_actual).first()

                        if not topo:
                            topo = EntityTopology(
                                system_code="zentao-prod",
                                external_resource_id=zt_id_actual,
                                resource_name=row.get("zentao_product_name"),
                                element_type="issue-tracker-product",
                                is_active=True,
                            )
                            session.add(topo)
                        topo.project_id = mdm_id
            session.commit()

        # 2. Sync Projects/Executions
        project_csv = "docs/zentao_project_map.csv"
        if os.path.exists(project_csv):
            print(f"Syncing projects from {project_csv}...")
            with open(project_csv, encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    zt_exec_id = row.get("zentao_execution_id")
                    mdm_proj_id = row.get("mdm_project_id")
                    if zt_exec_id and mdm_proj_id:
                        # Update topology for zentao-exec
                        # Note: zt_exec_id in CSV might be a code or ID string
                        topo = session.query(EntityTopology).filter_by(system_code="zentao-exec", external_resource_id=str(zt_exec_id)).first()
                        if not topo:
                            topo = EntityTopology(
                                system_code="zentao-exec", external_resource_id=str(zt_exec_id), element_type="issue-tracker-execution", is_active=True
                            )
                            session.add(topo)
                        topo.project_id = mdm_proj_id
            session.commit()

        print("Done!")

    except Exception as e:
        session.rollback()
        print(f"Error: {e}")
    finally:
        session.close()


if __name__ == "__main__":
    main()
