import json
import logging

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from devops_collector.auth.auth_database import get_auth_db
from devops_collector.core.exceptions import BusinessException, ValidationException
from devops_collector.core.quality_service import QualityService
from devops_collector.models import User
from devops_collector.plugins.dependency_check.worker import DependencyCheckWorker
from devops_portal import schemas
from devops_portal.dependencies import get_current_user
from devops_portal.schemas import DependencyScanResult


def get_quality_service(db: Session = Depends(get_auth_db)) -> QualityService:
    return QualityService(db)


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/security", tags=["security"])


@router.post("/dependency-check/upload", response_model=DependencyScanResult)
async def upload_dependency_report(
    project_id: int = Form(...),
    commit_sha: str = Form(None),
    branch: str = Form(None),
    ci_job_id: str = Form(None),
    ci_job_url: str = Form(None),
    scan_duration: float = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_auth_db),
    service: QualityService = Depends(get_quality_service),
):
    """
    上传 Dependency-Check 扫描报告 (CI 集成)。

    接收 CI 流水线生成的 JSON 报告并解析入库。
    """
    try:
        content = await file.read()
        report_json = json.loads(content.decode("utf-8"))

        # 构造任务上下文
        task = {
            "project_id": project_id,
            "report_json": report_json,
            "commit_sha": commit_sha,
            "branch": branch,
            "ci_job_id": ci_job_id,
            "ci_job_url": ci_job_url,
            "duration": scan_duration,
        }

        # 同步调用 Worker
        worker = DependencyCheckWorker(db)
        scan_id = worker.process_task(task)

        # 查询结果
        scan = service.get_scan(scan_id)
        if not scan:
            raise BusinessException("Scan record creation failed", code="CREATE_FAILED", status_code=500)

        return {
            "scan_id": scan.id,
            "project_id": scan.project_id,
            "status": scan.scan_status,
            "summary": {
                "total": scan.total_dependencies or 0,
                "vulnerable": scan.vulnerable_dependencies or 0,
                "risk_licenses": scan.high_risk_licenses or 0,
            },
        }

    except json.JSONDecodeError:
        raise ValidationException("Invalid JSON file format")
    except ValueError as e:
        raise ValidationException(str(e))
    except BusinessException:
        raise
    except Exception as e:
        logger.error(f"Upload failed: {e}", exc_info=True)
        raise BusinessException(f"Upload failed internal error: {str(e)}", status_code=500)


@router.get("/dependency-scans", response_model=list[schemas.DependencyScanSummary])
async def list_dependency_scans(current_user: User = Depends(get_current_user), service: QualityService = Depends(get_quality_service)):
    """[P5] 获取 Dependency Check 扫描结果（支持组织隔离）。"""
    return service.list_dependency_scans(current_user)
