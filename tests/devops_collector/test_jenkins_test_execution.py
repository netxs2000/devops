import pytest
from sqlalchemy.exc import IntegrityError
from devops_collector.models.base_models import JenkinsTestExecution

def test_create_jenkins_test_execution(db_session):
    """Test creating a JenkinsTestExecution record."""
    execution = JenkinsTestExecution(
        project_id=101,
        build_id="build-500",
        test_level="Unit",
        test_tool="Jenkins/JUnit",
        total_cases=100,
        passed_count=90,
        failed_count=5,
        skipped_count=5,
        pass_rate=90.0,
        duration_ms=5000,
        raw_data={"some": "data"}
    )
    db_session.add(execution)
    db_session.commit()
    db_session.refresh(execution)
    
    assert execution.id is not None
    assert execution.project_id == 101
    assert execution.build_id == "build-500"
    assert execution.test_level == "Unit"
    assert execution.pass_rate == 90.0

def test_jenkins_test_execution_uniqueness(db_session):
    """Test the unique constraint on (project_id, build_id, test_level)."""
    # Create first record
    execution1 = JenkinsTestExecution(
        project_id=202,
        build_id="build-888",
        test_level="Integration",
        pass_rate=95.0
    )
    db_session.add(execution1)
    db_session.commit()
    
    # Try to create duplicate record
    execution2 = JenkinsTestExecution(
        project_id=202,
        build_id="build-888",
        test_level="Integration",
        pass_rate=0.0
    )
    db_session.add(execution2)
    
    with pytest.raises(IntegrityError):
        db_session.commit()
    
    db_session.rollback()

def test_jenkins_test_execution_allow_different_levels(db_session):
    """Test that same project and build can have different test levels."""
    # Unit Test Record
    unit_test = JenkinsTestExecution(
        project_id=303,
        build_id="build-999",
        test_level="Unit",
        pass_rate=100.0
    )
    # UI Test Record
    ui_test = JenkinsTestExecution(
        project_id=303,
        build_id="build-999",
        test_level="UI",
        pass_rate=80.0
    )
    
    db_session.add(unit_test)
    db_session.add(ui_test)
    db_session.commit()
    
    assert db_session.query(JenkinsTestExecution).filter_by(project_id=303, build_id="build-999").count() == 2
