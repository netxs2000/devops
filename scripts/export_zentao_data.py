import csv
import os
import sys
from pathlib import Path
from sqlalchemy import create_engine, text

def export_data():
    uri = os.getenv("DATABASE__URI")
    if not uri:
        uri = "postgresql://postgres:devops123@db:5432/devops_db"
        
    engine = create_engine(uri)
    
    # Export zentao_products
    print("Exporting zentao_products...")
    sql_products = text("SELECT id, code, name, status, mdm_product_id FROM public.zentao_products ORDER BY id")
    with engine.connect() as conn:
        result = conn.execute(sql_products)
        with open("zentao_products_export.csv", "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "code", "name", "status", "mdm_product_id"])
            for row in result:
                writer.writerow(row)
    
    # Export zentao_executions
    print("Exporting zentao_executions...")
    sql_executions = text("SELECT id, product_id, name, code, type, status, parent_id, mdm_project_id FROM public.zentao_executions ORDER BY id")
    with engine.connect() as conn:
        result = conn.execute(sql_executions)
        with open("zentao_executions_export.csv", "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "product_id", "name", "code", "type", "status", "parent_id", "mdm_project_id"])
            for row in result:
                writer.writerow(row)
    
    print("Export completed successfully.")

if __name__ == "__main__":
    export_data()
