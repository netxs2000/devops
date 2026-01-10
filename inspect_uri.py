
import pandas as pd
from sqlalchemy import text
from dashboard.common.db import get_db_engine, settings

def inspect_columns(table_name):
    engine = get_db_engine()
    print(f"Using URI: {settings.database.uri}")
    try:
        query = f"SELECT * FROM {table_name} LIMIT 0"
        with engine.connect() as conn:
            df = pd.read_sql(text(query), conn)
            print(f"Columns in {table_name}:")
            for col in df.columns:
                print(f"- {col}")
    except Exception as e:
        print(f"Error inspecting {table_name}: {e}")

if __name__ == "__main__":
    inspect_columns("public_marts.fct_talent_radar")
