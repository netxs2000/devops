"""测试管理路由模块 (Test Management).

处理测试用例、需求跟踪、缺陷管理以及 AI 辅助测试生成的 API 请求。
"""
import logging
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
import urllib.parse

from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Query, Body, Request, Response
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
from starlette.responses import JSONResponse

from devops_portal import schemas
from devops_collector.auth.auth_database import get_auth_db
from devops_collector.auth.auth_dependency import get_user_gitlab_client
from devops_portal.dependencies import get_current_user, check_permission
from devops_collector.plugins.gitlab.test_management_service import TestManagementService
from devops_collector.plugins.gitlab.gitlab_client import GitLabClient
from devops_portal.state import GLOBAL_QUALITY_ALERTS, EXECUTION_HISTORY

router = APIRouter(prefix='/test-management', tags=['test-management'])
logger = logging.getLogger(__name__)

def get_test_management_service(
    db: Session = Depends(get_auth_db),
    client: GitLabClient = Depends(get_user_gitlab_client)
) -> TestManagementService:
    """获取测试管理服务实例。"""
    return TestManagementService(db, client)

@router.get('/projects/{project_id}/test-cases', response_model=List[schemas.TestCase])
async def list_test_cases(
    project_id: int, 
    current_user=Depends(get_current_user), 
    db: Session=Depends(get_auth_db),
    service: TestManagementService = Depends(get_test_management_service)
):
    """获取并解析 GitLab 项目中的所有测试用例。"""
    try:
        test_cases = await service.get_test_cases(db, project_id, current_user)
        return test_cases
    except Exception as e:
        logger.error(f'Failed to fetch test cases: {e}')
        raise HTTPException(status_code=500, detail=str(e))

@router.post('/projects/{project_id}/test-cases')
async def create_test_case(
    project_id: int, 
    data: schemas.TestCaseCreate, 
    current_user=Depends(check_permission(['maintainer', 'admin'])),
    service: TestManagementService = Depends(get_test_management_service)
):
    """在线录入并创建测试用例。"""
    try:
        issue = await service.create_test_case(
            project_id=project_id, 
            title=data.title, 
            priority=data.priority, 
            test_type=data.test_type, 
            pre_conditions=data.pre_conditions.split('\n') if isinstance(data.pre_conditions, str) else data.pre_conditions, 
            steps=[s.dict() for s in data.steps], 
            requirement_id=str(data.requirement_iid) if data.requirement_iid else None, 
            creator=current_user.full_name
        )
        return {'status': 'success', 'issue': issue}
    except Exception as e:
        logger.error(f'Failed to create test case: {e}')
        raise HTTPException(status_code=500, detail=str(e))

@router.post('/projects/{project_id}/test-cases/import')
async def import_test_cases(
    project_id: int, 
    file: UploadFile=File(...), 
    current_user=Depends(check_permission(['maintainer', 'admin'])),
    service: TestManagementService = Depends(get_test_management_service)
):
    """批量从 Excel/CSV 导入测试用例。"""
    try:
        import pandas as pd
        import io
        contents = await file.read()
        if file.filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(contents))
        else:
            df = pd.read_excel(io.BytesIO(contents))
        import_items = []
        for _, row in df.iterrows():
            raw_steps = str(row.get('steps', ''))
            steps = []
            for s in raw_steps.split('\n'):
                if '|' in s:
                    parts = s.split('|')
                    steps.append({'action': parts[0].strip(), 'expected': parts[1].strip()})
                elif s.strip():
                    steps.append({'action': s.strip(), 'expected': '无'})
            import_items.append({
                'title': str(row.get('title', 'Untitled')), 
                'priority': str(row.get('priority', 'P2')), 
                'test_type': str(row.get('test_type', '功能测试')), 
                'requirement_id': str(row.get('requirement_id', '')) if not pd.isna(row.get('requirement_id')) else None, 
                'pre_conditions': str(row.get('pre_conditions', '')).split('\n'), 
                'steps': steps
            })
        result = await service.batch_import_test_cases(project_id, import_items)
        return result
    except ImportError:
        raise HTTPException(status_code=500, detail="Server missing 'pandas' or 'openpyxl' libraries.")
    except Exception as e:
        logger.error(f'Batch import failed: {e}')
        raise HTTPException(status_code=500, detail=str(e))

@router.post('/projects/{project_id}/test-cases/clone')
async def clone_test_cases(
    project_id: int, 
    source_project_id: int=Query(...), 
    current_user=Depends(check_permission(['maintainer', 'admin'])),
    service: TestManagementService = Depends(get_test_management_service)
):
    """从源项目克隆所有测试用例到当前项目。"""
    try:
        result = await service.clone_test_cases_from_project(source_project_id, project_id)
        return result
    except Exception as e:
        logger.error(f'Project clone failed: {e}')
        raise HTTPException(status_code=500, detail=str(e))

@router.post('/projects/{project_id}/test-cases/generate-from-ac')
async def generate_steps_from_ac(
    project_id: int, 
    requirement_iid: int=Query(...), 
    current_user=Depends(get_current_user),
    service: TestManagementService = Depends(get_test_management_service)
):
    """[AI] 根据关联需求的验收标准自动生成测试步骤。"""
    try:
        result = await service.generate_steps_from_requirement(project_id, requirement_iid)
        return result
    except Exception as e:
        logger.error(f'AI Step Generation failed: {e}')
        raise HTTPException(status_code=500, detail=str(e))

@router.get('/projects/{project_id}/requirements', response_model=List[schemas.RequirementSummary])
async def list_requirements(
    project_id: int, 
    current_user=Depends(get_current_user), 
    db: Session=Depends(get_auth_db),
    service: TestManagementService = Depends(get_test_management_service)
):
    """获取项目中的所有需求。"""
    try:
        return await service.list_requirements(project_id, current_user, db)
    except Exception as e:
        logger.error(f'Failed to list requirements: {e}')
        raise HTTPException(status_code=500, detail=str(e))

@router.get('/projects/{project_id}/requirements/{iid}', response_model=schemas.RequirementDetail)
async def get_requirement_detail(
    project_id: int, 
    iid: int, 
    current_user=Depends(get_current_user),
    service: TestManagementService = Depends(get_test_management_service)
):
    """获取单个需求详情。"""
    try:
        req = await service.get_requirement_detail(project_id, iid)
        if not req:
            raise HTTPException(status_code=404, detail='Requirement not found')
        return req
    except Exception as e:
        logger.error(f'Failed to get requirement: {e}')
        raise HTTPException(status_code=500, detail=str(e))

@router.post('/projects/{project_id}/requirements')
async def create_requirement(
    project_id: int, 
    data: schemas.RequirementCreate, 
    current_user=Depends(get_current_user),
    service: TestManagementService = Depends(get_test_management_service)
):
    """创建新的需求。"""
    try:
        result = await service.create_requirement(
            project_id=project_id, 
            title=data.title, 
            priority=data.priority, 
            category=data.req_type, 
            business_value=data.description, 
            acceptance_criteria=[], 
            creator_name=current_user.full_name
        )
        return result
    except Exception as e:
        logger.error(f'Failed to create requirement: {e}')
        raise HTTPException(status_code=500, detail=str(e))

@router.get('/projects/{project_id}/bugs', response_model=List[schemas.BugDetail])
async def get_project_bugs(
    project_id: int,
    service: TestManagementService = Depends(get_test_management_service)
):
    """获取项目中所有的缺陷。"""
    # 逻辑可以移入 service，这里暂留或简化
    try:
        client = service.client
        issues = client.get_project_issues(project_id)
        bugs = []
        for issue in issues:
            labels = issue.get('labels', [])
            if 'type::bug' in labels or 'bug' in labels:
                bugs.append(schemas.BugDetail(
                    iid=issue['iid'], 
                    title=issue['title'], 
                    state=issue['state'], 
                    created_at=datetime.fromisoformat(issue['created_at'].replace('Z', '+00:00')), 
                    author=issue['author']['name'], 
                    web_url=issue['web_url'], 
                    labels=labels
                ))
        return bugs
    except Exception as e:
        logger.error(f'Failed to fetch bugs: {e}')
        raise HTTPException(status_code=500, detail=str(e))

@router.post('/projects/{project_id}/defects')
async def create_defect(
    project_id: int, 
    data: schemas.BugCreate, 
    current_user=Depends(get_current_user),
    service: TestManagementService = Depends(get_test_management_service)
):
    """QA 专业缺陷提报接口。"""
    try:
        result = await service.create_defect(
            project_id=project_id, 
            title=data.title, 
            severity=data.severity, 
            priority=data.priority, 
            category=data.category, 
            env=data.environment, 
            steps=data.steps_to_repro, 
            expected=data.expected_result, 
            actual=data.actual_result, 
            reporter_name=current_user.full_name, 
            related_test_case_iid=data.linked_case_iid
        )
        return result
    except Exception as e:
        logger.error(f'Failed to report defect: {e}')
        raise HTTPException(status_code=500, detail=str(e))

@router.post('/projects/{project_id}/test-cases/{issue_iid}/execute')
async def execute_test_case(
    project_id: int, 
    issue_iid: int, 
    result: str=Query(None), 
    report: Optional[schemas.ExecutionReport]=None, 
    current_user=Depends(check_permission(['tester', 'maintainer', 'admin'])),
    service: TestManagementService = Depends(get_test_management_service)
):
    """执行测试用例并更新 GitLab 标签、状态及审计记录。"""
    final_result = result or (report.result if report else None)
    if not final_result or final_result not in ['passed', 'failed', 'blocked']:
        raise HTTPException(status_code=400, detail='Invalid result status')
    executor = f'{current_user.full_name} ({current_user.primary_email})'
    try:
        success = await service.execute_test_case(project_id, issue_iid, final_result, executor)
        return {'status': 'success', 'new_result': final_result}
    except Exception as e:
        logger.error(f'Failed to execute test case #{issue_iid}: {e}')
        raise HTTPException(status_code=500, detail=str(e))

@router.get('/projects/{project_id}/test-summary')
async def get_test_summary(
    project_id: int, 
    current_user=Depends(get_current_user), 
    db: Session=Depends(get_auth_db),
    service: TestManagementService = Depends(get_test_management_service)
):
    """获取测试用例执行状态的统计摘要。"""
    try:
        issues = await service.get_test_cases(db, project_id, current_user)
        summary = {'passed': 0, 'failed': 0, 'blocked': 0, 'pending': 0, 'total': len(issues)}
        for issue in issues:
            res = issue.result
            summary[res] = summary.get(res, 0) + 1
        return summary
    except Exception as e:
        logger.error(f'Failed to fetch summary: {e}')
        raise HTTPException(status_code=500, detail=str(e))

@router.get('/global/alerts')
async def get_global_alerts():
    """获取全网质量同步预警。"""
    return GLOBAL_QUALITY_ALERTS