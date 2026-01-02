"""Dagster resources for the DevOps data platform.

This module defines the shared resources used by Dagster assets and jobs,
such as database connections.
"""
from dagster import ConfigurableResource
from sqlalchemy import create_engine
from devops_collector.config import settings

class DatabaseResource(ConfigurableResource):
    """Resource for interacting with the DevOps database.

    Attributes:
        connection_string: The SQLAlchemy connection URI for the database.
    """
    connection_string: str

    def get_engine(self):
        """Creates and returns a SQLAlchemy engine for the database.

        Returns:
            A SQLAlchemy Engine instance.
        """
        return create_engine(self.connection_string)

def get_db_resource():
    """Factory function to create a DatabaseResource instance.

    Returns:
        A DatabaseResource initialized with settings from config.
    """
    return DatabaseResource(connection_string=settings.database.uri)