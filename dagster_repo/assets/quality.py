import pandas as pd
import great_expectations as gx
from dagster import asset_check, AssetCheckResult, AssetKey, Definitions, load_assets_from_modules
from dagster_repo.resources import DatabaseResource
import sqlalchemy as sa

@asset_check(asset=AssetKey(["devops_dbt_assets", "fct_developer_activity_profile"]), description="Check for non-null user_id and reasonable impact scores")
def check_developer_profile(db: DatabaseResource):
    """Data quality check for developer activity profile using Great Expectations."""
    engine = sa.create_engine(db.uri)
    df = pd.read_sql("SELECT * FROM fct_developer_activity_profile", engine)
    
    # Initialize GX context
    context = gx.get_context()
    
    # Create a batch of data
    batch = context.data_sources.add_pandas("developer_profile").add_data_asset("profile_asset").get_batch(df)
    
    # Define and run expectations
    results = batch.validate(
        gx.expectations.ExpectColumnValuesToNotBeNull(column="user_id"),
        gx.expectations.ExpectColumnValuesToBeBetween(column="total_impact_score", min_value=0),
        gx.expectations.ExpectColumnValuesToBeInSet(column="developer_archetype", value_set=['Review Master', 'Code Machine', 'Task Closer', 'Generalist'])
    )
    
    return AssetCheckResult(
        passed=results.success,
        metadata={
            "success_percent": results.statistics["success_percent"],
            "total_expectations": results.statistics["evaluated_expectations"],
            "failed_expectations": results.statistics["unsuccessful_expectations"]
        }
    )

@asset_check(asset=AssetKey(["devops_dbt_assets", "fct_dora_metrics"]), description="Check DORA metrics sanity")
def check_dora_metrics(db: DatabaseResource):
    """Data quality check for DORA metrics using Great Expectations."""
    engine = sa.create_engine(db.uri)
    df = pd.read_sql("SELECT * FROM fct_dora_metrics", engine)
    
    context = gx.get_context()
    batch = context.data_sources.add_pandas("dora_metrics").add_data_asset("dora_asset").get_batch(df)
    
    results = batch.validate(
        gx.expectations.ExpectColumnValuesToNotBeNull(column="deployment_count"),
        gx.expectations.ExpectColumnValuesToBeBetween(column="change_failure_rate", min_value=0, max_value=100)
    )
    
    return AssetCheckResult(
        passed=results.success,
        metadata={
            "success_percent": results.statistics["success_percent"]
        }
    )

@asset_check(asset=AssetKey(["devops_dbt_assets", "fct_metrics_audit_guard"]), description="Guard against high variance in metrics")
def check_metrics_guard(db: DatabaseResource):
    """Data quality check for Metrics Audit Guard."""
    engine = sa.create_engine(db.uri)
    df = pd.read_sql("SELECT * FROM fct_metrics_audit_guard", engine)
    
    context = gx.get_context()
    batch = context.data_sources.add_pandas("metrics_guard").add_data_asset("guard_asset").get_batch(df)
    
    # Expect variance percentage to be low for "Consistency"
    results = batch.validate(
        gx.expectations.ExpectColumnValuesToBeBetween(column="variance_percentage", min_value=-5, max_value=5)
    )
    
    return AssetCheckResult(
        passed=results.success,
        metadata={
            "anomalies_detected": int(len(df[df['is_anomaly'] == True])),
            "success_percent": results.statistics["success_percent"]
        }
    )
