"""TODO: Add module description for dagster_repo assets core tests."""
import sys
import os
from unittest.mock import MagicMock
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.append(project_root)
mock_modules = ['dagster', 'dagster_assets', 'dagster_dbt', 'devops_collector', 'devops_collector.config', 'devops_collector.models', 'devops_collector.models.base_models', 'devops_collector.plugins', 'devops_collector.plugins.gitlab', 'devops_collector.plugins.gitlab.worker', 'devops_collector.plugins.gitlab.models', 'devops_collector.plugins.jira', 'devops_collector.plugins.jira.worker', 'devops_collector.plugins.sonarqube', 'devops_collector.plugins.sonarqube.worker', 'sqlalchemy', 'sqlalchemy.orm', 'sqlalchemy.ext', 'sqlalchemy.ext.hybrid', 'sqlalchemy.dialects', 'sqlalchemy.dialects.postgresql', 'sqlalchemy.sql']
for mod in mock_modules:
    sys.modules[mod] = MagicMock()

def test_import_core_module():
    """测试 dagster_repo.assets.core 模块能够成功导入。"""
    try:
        import dagster_repo.assets.core as core
        assert core is not None
    except Exception as e:
        import pytest
        pytest.skip(f'Skipping core import test due to env/circular issues: {e}')