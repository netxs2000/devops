"""Dagster repository definition.

This module centralizes the loading of assets, resources, and job definitions
for the Dagster orchestration of the DevOps data platform.
"""
import os
from pathlib import Path
from dagster import Definitions, load_assets_from_modules, DefineAssetJob, AssetSelection, ScheduleDefinition
try:
    from dagster_dbt import DbtCliResource
except ImportError:
    DbtCliResource = None
from dagster_repo.assets import core, dbt, gitlab, quality, reports
from dagster_repo.resources import get_db_resource

DBT_PROJECT_DIR = Path(__file__).joinpath('..', '..', 'dbt_project').resolve()

all_assets = load_assets_from_modules([core, gitlab, reports])
all_checks = load_assets_from_modules([quality])

try:
    from dagster_repo.assets.dbt import devops_dbt_assets
    all_assets.append(devops_dbt_assets)
except ImportError:
    pass

resources = {'db': get_db_resource()}
if DbtCliResource:
    resources['dbt'] = DbtCliResource(project_dir=os.fspath(DBT_PROJECT_DIR))
else:
    from unittest.mock import MagicMock
    resources['dbt'] = MagicMock()

# Define Job: Run all assets including the executive report
audit_report_job = DefineAssetJob(
    name="executive_audit_job",
    selection=AssetSelection.all()
)

# Define Schedule: Every Monday at 9:00 AM
audit_report_schedule = ScheduleDefinition(
    job=audit_report_job,
    cron_schedule="0 9 * * 1",
)

defs = Definitions(
    assets=all_assets,
    asset_checks=all_checks,
    resources=resources,
    jobs=[audit_report_job],
    schedules=[audit_report_schedule]
)