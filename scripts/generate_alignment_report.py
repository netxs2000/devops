import os
import sys

import pandas as pd
from sqlalchemy import create_engine, text


# Add the project root to the path
sys.path.append(os.getcwd())
from devops_collector.config import settings


def generate_report():
    engine = create_engine(settings.database.uri)

    with engine.connect() as conn:
        # 1. Unaligned GitLab Projects
        query_gitlab = text("""
            SELECT project_name, path_with_namespace 
            FROM public_intermediate.int_entity_alignment 
            WHERE master_entity_id IS NULL
            ORDER BY path_with_namespace
        """)
        rows_gitlab = conn.execute(query_gitlab).fetchall()

        # 2. Unaligned ZenTao Executions
        query_zentao = text("""
            SELECT execution_id, execution_name 
            FROM public_staging.stg_zentao_executions 
            WHERE mdm_project_id IS NULL
            ORDER BY execution_name
        """)
        rows_zentao = conn.execute(query_zentao).fetchall()

        # 3. MDM Projects for reference
        query_mdm = text("""
            SELECT project_id, project_name 
            FROM public_marts.dim_projects
        """)
        rows_mdm = conn.execute(query_mdm).fetchall()

    report_path = "unaligned_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# 数据对齐审计报告 (Orphan Alignment Audit)\n\n")
        f.write("> **说明**：以下资产目前未关联到 MDM 项目主数据，导致其指标无法汇总到报表大屏。\n\n")

        f.write(f"## 1. 未对齐的 GitLab 仓库 ({len(rows_gitlab)} 个)\n\n")
        f.write("| 仓库路径 (path_with_namespace) | 建议对齐方式 |\n")
        f.write("| :--- | :--- |\n")
        for idx, row in enumerate(rows_gitlab):
            if idx >= 50:
                break
            f.write(f"| {row[1]} | 在 `projects.csv` 中添加此路径 |\n")
        if len(rows_gitlab) > 50:
            f.write(f"| ... | 还有 {len(rows_gitlab) - 50} 条未显示 |\n")

        f.write(f"\n## 2. 未对齐的禅道执行/迭代 ({len(rows_zentao)} 个)\n\n")
        f.write("| 禅道执行名称 | 禅道 ID | 建议对齐方式 |\n")
        f.write("| :--- | :--- | :--- |\n")
        for row in rows_zentao:
            f.write(f"| {row[1]} | {row[0]} | 在 `zentao_project_map.csv` 中添加此 ID |\n")

        f.write("\n## 3. 可用的 MDM 项目参考\n\n")
        f.write("| MDM 项目 ID | 项目名称 |\n")
        f.write("| :--- | :--- |\n")
        for row in rows_mdm:
            f.write(f"| {row[0]} | {row[1]} |\n")

    print(f"Report generated: {report_path}")


if __name__ == "__main__":
    generate_report()
