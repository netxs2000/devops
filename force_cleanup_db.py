
from sqlalchemy import text
from dashboard.common.db import get_db_engine

def force_cleanup():
    engine = get_db_engine()
    tables_to_drop = [
        "public_marts.fct_architectural_brittleness",
        "public_marts.fct_talent_radar",
        "public_marts.fct_metrics_audit_guard",
        "public_intermediate.int_unified_activities"
    ]
    with engine.connect() as conn:
        for table in tables_to_drop:
            try:
                print(f"Dropping {table}...")
                conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))
                conn.execute(text(f"DROP VIEW IF EXISTS {table} CASCADE"))
                conn.commit()
            except Exception as e:
                print(f"Error dropping {table}: {e}")

if __name__ == "__main__":
    force_cleanup()
