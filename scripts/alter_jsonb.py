import os
import sys
from sqlalchemy import create_engine, text

sys.path.append(os.getcwd())
from devops_collector.config import settings

def upgrade_json_to_jsonb():
    engine = create_engine(settings.database.uri)
    with engine.begin() as conn:
        print("Upgrading columns to JSONB...")
        try:
            conn.execute(text("ALTER TABLE zentao_issues ALTER COLUMN estimate TYPE jsonb USING estimate::text::jsonb"))
            conn.execute(text("ALTER TABLE zentao_issues ALTER COLUMN consumed TYPE jsonb USING consumed::text::jsonb"))
            conn.execute(text("ALTER TABLE zentao_issues ALTER COLUMN \"left\" TYPE jsonb USING \"left\"::text::jsonb"))
            conn.execute(text("ALTER TABLE zentao_issues ALTER COLUMN raw_data TYPE jsonb USING raw_data::text::jsonb"))
            print("Finished upgrading zentao_issues")
        except Exception as e:
            print(f"Error on zentao_issues (table might not exist or columns changed): {e}")

        try:
            conn.execute(text("ALTER TABLE zentao_products ALTER COLUMN raw_data TYPE jsonb USING raw_data::text::jsonb"))
            print("Finished upgrading zentao_products")
        except Exception as e:
            print(f"Error on zentao_products: {e}")

        try:
            conn.execute(text("ALTER TABLE zentao_product_plans ALTER COLUMN raw_data TYPE jsonb USING raw_data::text::jsonb"))
            print("Finished upgrading zentao_product_plans")
        except Exception as e:
            print(f"Error on zentao_product_plans: {e}")

        try:
            conn.execute(text("ALTER TABLE zentao_executions ALTER COLUMN raw_data TYPE jsonb USING raw_data::text::jsonb"))
            print("Finished upgrading zentao_executions")
        except Exception as e:
            print(f"Error on zentao_executions: {e}")

if __name__ == "__main__":
    upgrade_json_to_jsonb()
