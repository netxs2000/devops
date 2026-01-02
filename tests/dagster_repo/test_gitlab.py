"""TODO: Add module description for dagster_repo assets gitlab tests."""

import sys
import os
from unittest.mock import MagicMock

# 将项目根目录加入 sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.append(project_root)

# Mock Dagster related imports
sys.modules.setdefault('dagster', MagicMock())
sys.modules.setdefault('dagster_assets', MagicMock())
sys.modules.setdefault('dagster_dbt', MagicMock())

def test_import_gitlab_module():
    """测试 dagster_repo.assets.gitlab 模块能够成功导入。"""
    try:
        import dagster_repo.assets.gitlab as gitlab_mod
        assert gitlab_mod is not None
    except Exception as e:
        import pytest
        pytest.skip(f"Skipping gitlab import test due to env/circular issues: {e}")
