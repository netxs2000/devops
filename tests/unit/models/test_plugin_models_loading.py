import pytest
from sqlalchemy import create_engine, inspect
from devops_collector.models.base_models import Base
from devops_collector.core.plugin_loader import PluginLoader

@pytest.fixture(scope="module")
def engine():
    """Create a memory SQLite engine for testing."""
    return create_engine("sqlite:///:memory:")

def test_plugin_autodiscover():
    """Test that plugins are discovered correctly."""
    PluginLoader.autodiscover()
    assert len(PluginLoader._loaded_plugins) > 0
    assert "gitlab" in PluginLoader._loaded_plugins

def test_load_models():
    """Test that models from all plugins can be loaded."""
    PluginLoader.autodiscover()
    PluginLoader.load_models()
    # After loading models, they should be registered in Base.metadata
    # We check if some known plugin tables are present
    table_names = Base.metadata.tables.keys()
    assert "gitlab_projects" in table_names
    assert "gitlab_commits" in table_names
    assert "zentao_products" in table_names

def test_create_tables(engine):
    """Test that all tables can be created without foreign key errors."""
    PluginLoader.autodiscover()
    PluginLoader.load_models()
    
    # This will raise an exception if there are foreign key issues or mapping errors
    Base.metadata.create_all(engine)
    
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    # Core tables
    assert "mdm_identities" in tables
    assert "mdm_organizations" in tables
    
    # Plugin tables
    assert "gitlab_projects" in tables
    assert "gitlab_commits" in tables
    assert "gitlab_issues" in tables
    assert "zentao_products" in tables

def test_gitlab_model_relations(engine):
    """Deep check for GitLab model relations."""
    from sqlalchemy.orm import sessionmaker
    from devops_collector.plugins.gitlab.models import GitLabProject, GitLabCommit
    
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Create a project
    project = GitLabProject(
        id=1,
        name="test-project",
        path_with_namespace="group/test",
        star_count=0
    )
    session.add(project)
    
    # Create a commit
    commit = GitLabCommit(
        id="abc123def",
        project_id=1,
        short_id="abc123d",
        title="initial commit",
        author_name="Test User",
        author_email="test@example.com"
    )
    session.add(commit)
    session.commit()
    
    # Test relationship
    fetched_project = session.query(GitLabProject).filter_by(id=1).first()
    assert len(fetched_project.commits) == 1
    assert fetched_project.commits[0].id == "abc123def"
    
    session.close()
