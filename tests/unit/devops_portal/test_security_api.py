from unittest.mock import MagicMock, patch

import pytest
from fastapi import UploadFile
from sqlalchemy.orm import Session

from devops_collector.core import security
from devops_collector.core.exceptions import ValidationException
from devops_collector.models.dependency import DependencyScan
from devops_portal.routers.security_router import list_dependency_scans, upload_dependency_report


@pytest.fixture
def mock_db():
    return MagicMock(spec=Session)


@pytest.fixture
def mock_user():
    user = MagicMock()
    user.global_user_id = "user-uuid"
    user.role = security.ADMIN_ROLE_KEY
    return user


@patch("devops_portal.routers.security_router.DependencyCheckWorker")
@pytest.mark.asyncio
async def test_upload_dependency_report_success(mock_worker_class, mock_db):
    # Setup
    mock_worker = mock_worker_class.return_value
    mock_worker.process_task.return_value = 123

    mock_scan = MagicMock(spec=DependencyScan)
    mock_scan.id = 123
    mock_scan.project_id = 1
    mock_scan.scan_status = "completed"
    mock_scan.total_dependencies = 10
    mock_scan.vulnerable_dependencies = 2
    mock_scan.high_risk_licenses = 0

    mock_service = MagicMock()
    mock_service.get_scan.return_value = mock_scan

    mock_file = MagicMock(spec=UploadFile)
    mock_file.read.return_value = b'{"report": "data"}'

    # Execute
    result = await upload_dependency_report(project_id=1, file=mock_file, db=mock_db, service=mock_service)

    # Assert
    assert result["scan_id"] == 123
    assert result["summary"]["vulnerable"] == 2
    mock_worker.process_task.assert_called_once()


@pytest.mark.asyncio
async def test_upload_dependency_report_invalid_json(mock_db):
    mock_file = MagicMock(spec=UploadFile)
    mock_file.read.return_value = b"invalid json"

    with pytest.raises(ValidationException) as exc:
        await upload_dependency_report(project_id=1, file=mock_file, db=mock_db, service=MagicMock())
    assert "JSON" in str(exc.value)


@pytest.mark.asyncio
async def test_list_dependency_scans_admin(mock_user):
    # Setup
    mock_service = MagicMock()
    mock_service.list_dependency_scans.return_value = [MagicMock(spec=DependencyScan)]

    # Execute
    results = await list_dependency_scans(current_user=mock_user, service=mock_service)

    # Assert
    assert len(results) == 1


@pytest.mark.asyncio
async def test_list_dependency_scans_regular_user(mock_user):
    # Setup
    mock_user.role = "DEVELOPER"
    mock_service = MagicMock()
    mock_service.list_dependency_scans.return_value = []

    # Execute
    results = await list_dependency_scans(current_user=mock_user, service=mock_service)

    # Assert
    assert len(results) == 0
