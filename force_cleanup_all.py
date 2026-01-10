
from sqlalchemy import text
from dashboard.common.db import get_db_engine

def force_cleanup():
    engine = get_db_engine()
    schemas = ['public_marts', 'public_intermediate', 'public_staging']
    with engine.connect() as conn:
        for schema in schemas:
            try:
                # Get all tables and views in schema
                query = text(f"""
                    SELECT table_name, table_type 
                    FROM information_schema.tables 
                    WHERE table_schema = '{schema}'
                """)
                res = conn.execute(query)
                for row in res:
                    name = f"{schema}.{row[0]}"
                    obj_type = "TABLE" if row[1] == 'BASE TABLE' else "VIEW"
                    print(f"Dropping {obj_type} {name}...")
                    conn.execute(text(f"DROP {obj_type} IF EXISTS {name} CASCADE"))
                conn.commit()
            except Exception as e:
                print(f"Error cleaning schema {schema}: {e}")

if __name__ == "__main__":
    force_cleanup()
