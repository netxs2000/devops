
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

db_user = os.getenv('POSTGRES_USER', 'postgres')
db_pass = os.getenv('POSTGRES_PASSWORD', 'devops123')
db_name = os.getenv('POSTGRES_DB', 'devops_db')
db_host = 'localhost'
db_port = '5432'

db_url = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"

engine = create_engine(db_url)

try:
    with engine.connect() as conn:
        print("Checking if public_marts.fct_compliance_audit exists...")
        result = conn.execute(text("""
            SELECT count(*) 
            FROM information_schema.tables 
            WHERE table_schema = 'public_marts' 
              AND table_name = 'fct_compliance_audit'
        """))
        exists = result.scalar() > 0
        print(f"Exists: {exists}")
except Exception as e:
    print(f"Error: {e}")
