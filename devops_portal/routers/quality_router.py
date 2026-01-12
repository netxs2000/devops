"""质量分析路由 (Quality Analysis).

处理质量门禁、各维度质量指标以及合并请求分析的 API 请求。
"""
import logging
import asyncio
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import httpx

from devops_collector.config import Config
from devops_portal import schemas
from devops_collector.plugins.gitlab.test_management_service import TestManagementService
from devops_collector.plugins.gitlab.client import GitLabClient
from devops_collector.auth.router import get_db
from devops_collector.auth.user_dependencies import get_user_gitlab_client
from devops_portal.dependencies import get_current_user, filter_issues_by_province

router = APIRouter(prefix='/quality', tags=['quality'])
logger = logging.getLogger(__name__)

def get_test_management_service(
    db: Session = Depends(get_db),
    client: GitLabClient = Depends(get_user_gitlab_client)
) -> TestManagementService:
    """获取测试管理服务实例。"""
    return TestManagementService(db, client)

@router.get('/projects/{project_id}/province-quality', response_model=List[schemas.ProvinceQuality])
async def get_province_quality(project_id: int, current_user=Depends(get_current_user)):
    """获取各省份的质量分布数据（已实现部门级数据隔离）。"""
    url = f'{Config.GITLAB_URL}/api/v4/projects/{project_id}/issues'
    headers = {'PRIVATE-TOKEN': Config.GITLAB_PRIVATE_TOKEN}
    params = {'state': 'all', 'per_page': 100}
    try:
        resp = await Config.http_client.get(url, params=params, headers=headers)
        resp.raise_for_status()
        issues = resp.json()
        
        user_location = getattr(current_user, 'location', None)
        user_province = user_location.short_name if user_location else '全国'
        
        stats = {}
        for issue in issues:
            labels = issue.get('labels', [])
            province = 'nationwide'
            is_bug = 'type::bug' in labels
            for l in labels:
                if l.startswith('province::'):
                    province = l.split('::')[1]
                    break
            
            if user_province != '全国' and province != user_province:
                continue
                
            if province not in stats:
                stats[province] = {'bug_count': 0}
            if is_bug:
                stats[province]['bug_count'] += 1
                
        return [schemas.ProvinceQuality(province=p, bug_count=v['bug_count']) for p, v in stats.items()]
    except Exception as e:
        logger.error(f'Failed to fetch province quality: {e}')
        return []

@router.get('/projects/{project_id}/quality-gate', response_model=schemas.QualityGateStatus)
async def get_quality_gate(
    project_id: int, 
    current_user=Depends(get_current_user), 
    db: Session=Depends(get_db),
    service: TestManagementService = Depends(get_test_management_service)
):
    """自动化运行质量门禁合规性检查。"""
    try:
        # 1. 需求覆盖率检查
        reqs = await service.list_requirements(project_id, current_user, db)
        approved_reqs = [r for r in reqs if r.review_state == 'approved']
        if not approved_reqs:
            req_covered = False
        else:
            details = await asyncio.gather(*[service.get_requirement_detail(project_id, r.iid) for r in approved_reqs])
            covered_count = sum((1 for r in details if r and len(r.test_cases) > 0))
            coverage_rate = covered_count / len(approved_reqs) * 100
            req_covered = coverage_rate >= 80.0
            
        # 2. P0 Bug 检查
        client = service.client
        p0_issues = list(client.get_project_issues(project_id))
        p0_count = 0
        for issue in p0_issues:
            labels = issue.get('labels', [])
            if 'type::bug' in labels and 'severity::S0' in labels and issue['state'] == 'opened':
                p0_count += 1
        p0_cleared = p0_count == 0
        
        # 3. 流水线健康度
        pipelines = list(client.get_project_pipelines(project_id, per_page=1))
        pipe_stable = False
        if pipelines:
            pipe_stable = pipelines[0]['status'] == 'success'
            
        # 4. 地域风险检查
        prov_stats = {}
        for issue in p0_issues:
            if 'type::bug' not in issue.get('labels', []):
                continue
            prov = 'nationwide'
            for l in issue.get('labels', []):
                if l.startswith('province::'):
                    prov = l.split('::')[1]
                    break
            prov_stats[prov] = prov_stats.get(prov, 0) + 1
        high_risk_provinces = [p for p, count in prov_stats.items() if count > 10]
        regional_free = len(high_risk_provinces) == 0
        
        is_all_passed = all([req_covered, p0_cleared, pipe_stable, regional_free])
        summary = '质量门禁通过，准予发布。' if is_all_passed else '质量门禁拦截，存在合规性风险。'
        
        return schemas.QualityGateStatus(
            is_passed=is_all_passed,
            requirements_covered=req_covered,
            p0_bugs_cleared=p0_cleared,
            pipeline_stable=pipe_stable,
            regional_risk_free=regional_free,
            summary=summary
        )
    except Exception as e:
        logger.error(f'Gate Check Failed: {e}')
        raise HTTPException(status_code=500, detail=str(e))

@router.get('/projects/{project_id}/test-summary')
async def get_test_summary(
    project_id: int, 
    current_user=Depends(get_current_user),
    service: TestManagementService = Depends(get_test_management_service)
):
    """获取测试用例执行状态的统计摘要。"""
    try:
        # 这里复用 test_management_router 的逻辑
        from devops_portal.routers.test_management_router import get_test_summary as internal_summary
        return await internal_summary(project_id, current_user, None, service)
    except Exception as e:
        logger.error(f'Failed to fetch summary: {e}')
        raise HTTPException(status_code=500, detail=str(e))

@router.get('/projects/{project_id}/mr-summary', response_model=schemas.MRSummary)
async def get_mr_summary(
    project_id: int,
    service: TestManagementService = Depends(get_test_management_service)
):
    """获取并计算合并请求 (MR) 的评审统计信息。"""
    try:
        stats = await service.get_mr_summary_stats(project_id)
        return schemas.MRSummary(**stats)
    except Exception as e:
        logger.error(f'MR Summary failed: {e}')
        raise HTTPException(status_code=500, detail=str(e))

@router.get('/projects/{project_id}/quality-report')
async def get_quality_report(
    project_id: int,
    service: TestManagementService = Depends(get_test_management_service)
):
    """动态生成质量分析报告。"""
    try:
        report = await service.generate_quality_report(project_id)
        return {'content': report}
    except Exception as e:
        logger.error(f'Report generation failed: {e}')
        raise HTTPException(status_code=500, detail=str(e))