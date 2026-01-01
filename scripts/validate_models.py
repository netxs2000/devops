import os
import sys
import pandas as pd
from sqlalchemy import create_engine
import great_expectations as gx
from devops_collector.config import settings

def run_validation():
    """Runs data quality validation for core dbt models using Great Expectations."""
    print("🚀 Starting Data Quality Validation...")
    
    # 1. Setup GX Context and Data Source
    context = gx.get_context()
    engine = create_engine(settings.database.uri)
    
    datasource_name = "devops_db"
    if datasource_name not in context.datasources:
        context.sources.add_postgres(name=datasource_name, connection_string=settings.database.uri)
    
    datasource = context.get_datasource(datasource_name)

    # 定义校验模型清单
    models_to_validate = [
        {
            "name": "fct_dora_metrics",
            "suite_name": "dora_quality_suite",
            "expectations": [
                {"type": "expect_column_values_to_not_be_null", "column": "project_name"},
                {"type": "expect_column_values_to_be_between", "column": "deployment_frequency", "min_value": 0},
                {"type": "expect_column_values_to_be_between", "column": "change_failure_rate_pct", "min_value": 0, "max_value": 100},
                {"type": "expect_column_values_to_be_between", "column": "lead_time_minutes", "min_value": 0}
            ]
        },
        {
            "name": "fct_project_delivery_health",
            "suite_name": "health_quality_suite",
            "expectations": [
                {"type": "expect_column_values_to_be_between", "column": "health_score", "min_value": 0, "max_value": 100},
                {"type": "expect_column_values_to_not_be_null", "column": "quality_gate"},
                {"type": "expect_column_values_to_be_in_set", "column": "quality_gate", "value_set": ["OK", "ERROR", "WARN", "UNKNOWN"]}
            ]
        },
        {
            "name": "fct_compliance_audit",
            "suite_name": "compliance_quality_suite",
            "expectations": [
                {"type": "expect_column_values_to_be_between", "column": "bypass_rate_pct", "min_value": 0, "max_value": 100},
                {"type": "expect_column_values_to_be_in_set", "column": "compliance_status", "value_set": ["NON_COMPLIANT", "PROCESS_RISK", "COMPLIANT"]}
            ]
        },
        {
            "name": "fct_architectural_brittleness",
            "suite_name": "brittleness_quality_suite",
            "expectations": [
                {"type": "expect_column_values_to_be_between", "column": "brittleness_index", "min_value": 0},
                {"type": "expect_column_values_to_not_be_null", "column": "risk_level"}
            ]
        },
        {
            "name": "fct_developer_activity_profile",
            "suite_name": "developer_dna_quality_suite",
            "expectations": [
                {"type": "expect_column_values_to_not_be_null", "column": "full_name"},
                {"type": "expect_column_values_to_be_between", "column": "contribution_count", "min_value": 0}
            ]
        },
        {
            "name": "fct_capitalization_audit",
            "suite_name": "capitalization_quality_suite",
            "expectations": [
                {"type": "expect_column_values_to_not_be_null", "column": "epic_title"},
                {"type": "expect_column_values_to_be_between", "column": "audit_effort_units", "min_value": 0}
            ]
        },
        {
            "name": "fct_delivery_costs",
            "suite_name": "finops_quality_suite",
            "expectations": [
                {"type": "expect_column_values_to_be_between", "column": "total_labor_cost", "min_value": 0}
            ]
        },
        {
            "name": "fct_metrics_audit_guard",
            "suite_name": "metrics_guard_quality_suite",
            "expectations": [
                {"type": "expect_column_values_to_not_be_null", "column": "metric_name"},
                {"type": "expect_column_values_to_be_in_set", "column": "is_outlier", "value_set": [True, False]}
            ]
        },
        {
            "name": "fct_talent_radar",
            "suite_name": "talent_quality_suite",
            "expectations": [
                {"type": "expect_column_values_to_be_between", "column": "influence_score", "min_value": 0}
            ]
        },
        {
            "name": "fct_shadow_it_discovery",
            "suite_name": "shadow_it_quality_suite",
            "expectations": [
                {"type": "expect_column_values_to_not_be_null", "column": "project_name"}
            ]
        },
        {
            "name": "int_unified_activities",
            "suite_name": "unified_activity_quality_suite",
            "expectations": [
                {"type": "expect_column_values_to_not_be_null", "column": "activity_id"},
                {"type": "expect_column_values_to_not_be_null", "column": "event_type"}
            ]
        },
        {
            "name": "int_entity_alignment",
            "suite_name": "alignment_quality_suite",
            "expectations": [
                {"type": "expect_column_values_to_be_between", "column": "similarity_score", "min_value": 0, "max_value": 1}
            ]
        },
        {
            "name": "int_unified_work_items",
            "suite_name": "unified_work_quality_suite",
            "expectations": [
                {"type": "expect_column_values_to_not_be_null", "column": "unified_id"}
            ]
        }
    ]

    all_passed = True
    results_summary = []

    for model in models_to_validate:
        print(f"\n🔍 Validating model: {model['name']}...")
        
        # Create or Get Expectation Suite
        suite = context.suites.add_or_update(gx.ExpectationSuite(name=model['suite_name']))
        
        # Add Expectations
        for exp in model['expectations']:
            if exp['type'] == "expect_column_values_to_not_be_null":
                suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(column=exp['column']))
            elif exp['type'] == "expect_column_values_to_be_between":
                suite.add_expectation(gx.expectations.ExpectColumnValuesToBeBetween(
                    column=exp['column'], 
                    min_value=exp.get('min_value'), 
                    max_value=exp.get('max_value')
                ))
            elif exp['type'] == "expect_column_values_to_be_in_set":
                suite.add_expectation(gx.expectations.ExpectColumnValuesToBeInSet(
                    column=exp['column'], 
                    value_set=exp['value_set']
                ))

        # Get Batch from Table
        asset_name = f"table_{model['name']}"
        try:
            asset = datasource.get_asset(asset_name)
        except LookupError:
            asset = datasource.add_table_asset(name=asset_name, table_name=model['name'])
        
        batch_definition = asset.add_batch_definition_whole_dataframe(f"batch_def_{model['name']}")
        batch = batch_definition.get_batch()
        
        # Run Validation
        validation_result = batch.validate(suite)
        
        if not validation_result.success:
            print(f"❌ Validation FAILED for {model['name']}")
            all_passed = False
        else:
            print(f"✅ Validation PASSED for {model['name']}")
            
        results_summary.append({
            "model": model['name'],
            "success": validation_result.success,
            "percent_success": validation_result.statistics['success_percent']
        })

    # Saving results to a metadata table for Dashboard display
    summary_df = pd.DataFrame(results_summary)
    summary_df['validated_at'] = pd.Timestamp.now()
    summary_df.to_sql('sys_data_quality_results', engine, if_exists='replace', index=False)
    
    print("\n📊 Quality Validation Complete. Results saved to 'sys_data_quality_results'.")
    return all_passed

if __name__ == "__main__":
    if not run_validation():
        sys.exit(1)
