from dagster import Definitions, load_assets_from_modules
from dagster_repo.assets import core, gitlab, dbt, quality
from dagster_repo.resources import get_db_resource
from dagster_dbt import DbtCliResource
import os
from pathlib import Path

DBT_PROJECT_DIR = Path(__file__).joinpath("..", "..", "dbt_project").resolve()

# Load all assets and checks
all_assets = load_assets_from_modules([core, gitlab])
all_checks = load_assets_from_modules([quality])

# dbt assets (if manifest exists)
try:
    from dagster_repo.assets.dbt import devops_dbt_assets
    all_assets.append(devops_dbt_assets)
except Exception:
    pass

defs = Definitions(
    assets=all_assets,
    asset_checks=all_checks,
    resources={
        "db": get_db_resource(),
        "dbt": DbtCliResource(project_dir=os.fspath(DBT_PROJECT_DIR)),
    },
)
