from dagster import ConfigurableResource
from sqlalchemy import create_engine
from devops_collector.config import settings

class DatabaseResource(ConfigurableResource):
    """Resource for interacting with the DevOps database."""
    connection_string: str

    def get_engine(self):
        return create_engine(self.connection_string)

def get_db_resource():
    return DatabaseResource(connection_string=settings.database.uri)
