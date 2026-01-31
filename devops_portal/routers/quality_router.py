"""质量分析路由 (Quality Analysis).

处理质量门禁、各维度质量指标以及合并请求分析的 API 请求。
"""
import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from devops_collector.config import settings
from devops_portal import schemas
from devops_collector.plugins.gitlab.quality_service import QualityService
from devops_collector.plugins.gitlab.gitlab_client import GitLabClient
from devops_collector.auth.auth_database import get_auth_db
from devops_collector.auth.auth_dependency import get_user_gitlab_client
from devops_portal.dependencies import get_current_user

router = APIRouter(prefix='/quality', tags=['quality'])
logger = logging.getLogger(__name__)

def get_quality_service(
    db: Session = Depends(get_auth_db),
    client: GitLabClient = Depends(get_user_gitlab_client)
) -> QualityService:
    """获取质量分析服务实例。"""
    return QualityService(db, client)

@router.get('/projects/{project_id}/province-quality', response_model=List[schemas.ProvinceQuality])
async def get_province_quality(project_id: int, current_user=Depends(get_current_user)):
    """获取各省份的质量分布数据（已实现部门级数据隔离）。"""
    from devops_collector.config import Config
    url = f'{settings.gitlab.url}/api/v4/projects/{project_id}/issues'
    headers = {'PRIVATE-TOKEN': settings.gitlab.private_token}
    params = {'state': 'all', 'per_page': 100}
    try:
        # Use globally managed AsyncClient from Config
        if not hasattr(Config, 'http_client') or Config.http_client is None:
            import httpx
            async with httpx.AsyncClient(timeout=settings.client.timeout) as client:
                resp = await client.get(url, params=params, headers=headers)
        else:
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
            
            # Filter by province if user has a specific location
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
    service: QualityService = Depends(get_quality_service)
):
    """自动化运行质量门禁合规性检查。"""
    try:
        status = await service.get_quality_gate_status(project_id, current_user)
        return status
    except Exception as e:
        logger.error(f'Gate Check Failed: {e}')
        raise HTTPException(status_code=500, detail=str(e)) from e

@router.get('/projects/{project_id}/test-summary')
async def get_test_summary(
    project_id: int, 
    current_user=Depends(get_current_user),
    service: QualityService = Depends(get_quality_service)
):
    """获取测试用例执行状态的统计摘要。"""
    try:
        # 延迟导入以避免循环依赖
        from devops_portal.routers.test_management_router import get_test_summary as internal_summary
        return await internal_summary(project_id, current_user, None, service.test_service)
    except Exception as e:
        logger.error(f'Failed to fetch summary: {e}')
        raise HTTPException(status_code=500, detail=str(e)) from e

@router.get('/projects/{project_id}/mr-summary', response_model=schemas.MRSummary)
async def get_mr_summary(
    project_id: int,
    service: QualityService = Depends(get_quality_service)
):
    """获取并计算合并请求 (MR) 的评审统计信息。"""
    try:
        stats = await service.get_mr_analytics(project_id)
        return schemas.MRSummary(**stats)
    except Exception as e:
        logger.error(f'MR Summary failed: {e}')
        raise HTTPException(status_code=500, detail=str(e)) from e

@router.get('/projects/{project_id}/quality-report')
async def get_quality_report(
    project_id: int,
    service: QualityService = Depends(get_quality_service)
):
    """动态生成质量分析报告。"""
    try:
        report = await service.generate_report(project_id)
        return {'content': report}
    except Exception as e:
        logger.error(f'Report generation failed: {e}')
        raise HTTPException(status_code=500, detail=str(e)) from e