
from dagster import asset, AssetIn
from scripts.executive_audit_report import ExecutiveAuditBot
import logging

logger = logging.getLogger(__name__)

@asset(
    ins={
        "hotspots": AssetIn(key=["devops_dbt_assets", "fct_code_hotspots"]),
        "bus_factor": AssetIn(key=["devops_dbt_assets", "dws_subsystem_bus_factor"]),
        "fin_audit": AssetIn(key=["devops_dbt_assets", "fct_capitalization_audit"]),
        "talent": AssetIn(key=["devops_dbt_assets", "fct_talent_radar"]),
    },
    description="Engineers and Executive Audit Report Asset. Triggers notifications."
)
def executive_audit_report_asset(hotspots, bus_factor, fin_audit, talent):
    """
    This asset represents the executive audit report. 
    It doesn't store data itself but triggers the notification logic.
    """
    bot = ExecutiveAuditBot()
    bot.run()
    return "Report Sent"
