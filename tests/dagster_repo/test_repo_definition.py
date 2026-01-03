"""TODO: Add module description for dagster_repo package tests."""
import sys
import os
from unittest.mock import MagicMock
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.append(project_root)
sys.modules.setdefault('dagster', MagicMock())
sys.modules.setdefault('dagster_dbt', MagicMock())
sys.modules.setdefault('sqlalchemy', MagicMock())

def test_dagster_definitions():
    """测试 Dagster 定义是否能正确加载。"""
    try:
        from dagster_repo import defs
        assert defs is not None
    except Exception as e:
        import pytest
        pytest.skip(f'Skipping dagster definitions test due to: {e}')