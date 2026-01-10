from sqlalchemy import create_engine
from devops_collector.config import settings

def get_db_engine():
    """Returns a SQLAlchemy engine using the project settings."""
    return create_engine(settings.database.uri)
