from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from devops_collector.config import Config

engine = create_engine(Config.DB_URI)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
