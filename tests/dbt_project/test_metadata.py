"""TODO: Add module description for dbt_project metadata tests."""
import os
from pathlib import Path

def test_dbt_project_structure():
    """测试 dbt 项目结构是否完整。"""
    project_root = Path(__file__).parent.parent.parent / 'dbt_project'
    assert project_root.exists()
    assert project_root.is_dir()
    assert (project_root / 'dbt_project.yml').exists()
    assert (project_root / 'models').exists()

def test_dbt_models_count():
    """测试 dbt 模型文件是否存在。"""
    project_root = Path(__file__).parent.parent.parent / 'dbt_project'
    sql_files = list(project_root.glob('models/**/*.sql'))
    assert len(sql_files) > 0