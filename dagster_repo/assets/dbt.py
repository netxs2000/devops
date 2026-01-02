"""Dagster assets for dbt models.

This module defines the integration between Dagster and dbt, allowing dbt models
to be managed as Software-Defined Assets (SDA) within the Dagster ecosystem.
"""
import os
from pathlib import Path
from dagster import AssetExecutionContext
from dagster_dbt import DbtCliResource, dbt_assets
DBT_PROJECT_DIR = Path(__file__).joinpath('..', '..', '..', 'dbt_project').resolve()
dbt_resource = DbtCliResource(project_dir=os.fspath(DBT_PROJECT_DIR))

@dbt_assets(manifest=DBT_PROJECT_DIR.joinpath('target', 'manifest.json'))
def devops_dbt_assets(context: AssetExecutionContext, dbt: DbtCliResource):
    """Execution logic for dbt assets.

    Args:
        context: The Dagster execution context.
        dbt: The dbt CLI resource used to execute commands.

    Yields:
        Dagster events for each dbt artifact produced during execution.
    """
    yield from dbt.cli(['build'], context=context).get_artifacts()