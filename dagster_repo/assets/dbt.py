import os
from dagster import AssetExecutionContext
from dagster_dbt import DbtCliResource, dbt_assets, DagsterDbtTranslator
from pathlib import Path

# Path to the dbt project
DBT_PROJECT_DIR = Path(__file__).joinpath("..", "..", "..", "dbt_project").resolve()

dbt_resource = DbtCliResource(project_dir=os.fspath(DBT_PROJECT_DIR))

# Generate manifest at runtime if needed, but usually we load it
# For the sake of this setup, we'll assume dbt build is what we want to run
@dbt_assets(manifest=DBT_PROJECT_DIR.joinpath("target", "manifest.json"))
def devops_dbt_assets(context: AssetExecutionContext, dbt: DbtCliResource):
    yield from dbt.cli(["build"], context=context).get_artifacts()
