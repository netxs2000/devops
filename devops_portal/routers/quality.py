# -*- coding: utf-8 -*-
"""Quality and analytics router."""
import logging
import asyncio
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import httpx

from devops_collector.config import Config
from devops_portal import schemas
from devops_collector.gitlab_sync.services.testing_service import TestingService
from devops_collector.auth import router as auth_router
from devops_portal.dependencies import get_current_user, filter_issues_by_province

router = APIRouter(prefix="/projects/{project_id}", tags=["quality"])
logger = logging.getLogger(__name__)

@router.get("/province-quality", response_model=List[schemas.ProvinceQuality])
async def get_province_quality(project_id: int, current_user = Depends(get_current_user)):
    """获取各省份的质量分布数据（已实现部门级数据隔离）。"""
    url = f"{Config.GITLAB_URL}/api/v4/projects/{project_id}/issues"
    headers = {"PRIVATE-TOKEN": Config.GITLAB_PRIVATE_TOKEN}
    params = {"state": "all", "per_page": 100}

    try:
        # P0 FIX: Replaced blocking requests with async httpx
        resp = await Config.http_client.get(url, params=params, headers=headers)
        resp.raise_for_status()
        issues = resp.json()

        # 获取当前用户的省份权限范围（从location对象获取）
        user_location = getattr(current_user, 'location', None)
        user_province = user_location.short_name if user_location else '全国'  # 默认全国权限
        
        stats = {}
        for issue in issues:
            labels = issue.get('labels', [])
            province = "nationwide"
            is_bug = "type::bug" in labels
            
            for l in labels:
                if l.startswith("province::"):
                    province = l.split("::")[1]
                    break
            
            # 数据隔离逻辑：根据用户省份过滤
            if user_province != '全国' and province != user_province:
                continue  # 跳过非当前用户省份的数据
            
            if province not in stats:
                stats[province] = {"bug_count": 0}
            
            if is_bug:
                stats[province]["bug_count"] += 1

        return [
            schemas.ProvinceQuality(province=p, bug_count=v["bug_count"])
            for p, v in stats.items()
        ]
    except Exception as e:
        logger.error(f"Failed to fetch province quality: {e}")
        return []

@router.get("/requirements/stats", response_model=schemas.RequirementCoverage)
async def get_requirement_stats(
    project_id: int, 
    current_user = Depends(get_current_user),
    db: Session = Depends(auth_router.get_db)
):
    """获取项目的需求复盖率与健康度统计。"""
    try:
        service = TestingService()
        # 1. 获取所有需求 (Using new service method)
        reqs = await service.list_requirements(project_id, current_user, db)
        total_count = len(reqs)
        approved_reqs = [r for r in reqs if r.review_state == "approved"]
        approved_count = len(approved_reqs)

        if approved_count == 0:
            return schemas.RequirementCoverage(
                total_count=total_count,
                approved_count=0,
                covered_count=0,
                passed_count=0,
                coverage_rate=0.0,
                pass_rate=0.0,
                risk_requirements=[]
            )

        # 2. 并行获取每个 Approved 需求的详情（包含关联用例）
        details = await asyncio.gather(*[service.get_requirement_detail(project_id, r.iid) for r in approved_reqs])
        
        covered_count = 0
        passed_count = 0
        risk_reqs = []

        for req in details:
            if not req: continue
            has_cases = len(req.test_cases) > 0
            if has_cases:
                covered_count += 1
                
                # 检查健康度：是否所有用例都 Passed
                all_passed = all(tc.result == "passed" for tc in req.test_cases)
                any_failed = any(tc.result == "failed" for tc in req.test_cases)
                
                if all_passed:
                    passed_count += 1
                
                if any_failed:
                    risk_reqs.append(schemas.RequirementSummary(iid=req.iid, title=req.title, state=req.state, review_state=req.review_state))
            else:
                # 审核通过但无用例，视为高风险（漏测风险）
                risk_reqs.append(schemas.RequirementSummary(iid=req.iid, title=req.title, state=req.state, review_state=req.review_state))

        return schemas.RequirementCoverage(
            total_count=total_count,
            approved_count=approved_count,
            covered_count=covered_count,
            passed_count=passed_count,
            coverage_rate=(covered_count / approved_count * 100) if approved_count > 0 else 0.0,
            pass_rate=(passed_count / covered_count * 100) if covered_count > 0 else 0.0,
            risk_requirements=risk_reqs
        )
    except Exception as e:
        logger.error(f"Req Stats Failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/quality-gate", response_model=schemas.QualityGateStatus)
async def get_quality_gate(
    project_id: int,
    current_user = Depends(get_current_user), # Needed for isolation checks
    db: Session = Depends(auth_router.get_db)
):
    """自动化运行质量门禁合规性检查。"""
    try:
        service = TestingService()
        
        # 1. 获取需求统计 (Recalculate logic here to avoid dependency issues)
        reqs = await service.list_requirements(project_id, current_user, db)
        approved_reqs = [r for r in reqs if r.review_state == "approved"]
        if not approved_reqs:
             req_covered = False
        else:
             # Sample check of first few or count cases?
             # For gate check speed, we might assume approved with cases = covered?
             # Or we need full detail. Let's get full detail for approved.
             # Optimize: Only check if they have cases, don't need full parsing.
             # But service.get_requirement_detail fetches cases.
             # Let's parallel fetch.
             details = await asyncio.gather(*[service.get_requirement_detail(project_id, r.iid) for r in approved_reqs])
             covered_count = sum(1 for r in details if r and len(r.test_cases) > 0)
             coverage_rate = (covered_count / len(approved_reqs) * 100)
             req_covered = coverage_rate >= 80.0
        
        # 2. 获取缺陷数据 (检查 S0 严重程度)
        bugs_url = f"{Config.GITLAB_URL}/api/v4/projects/{project_id}/issues"
        headers = {"PRIVATE-TOKEN": Config.GITLAB_PRIVATE_TOKEN}
        params = {"labels": "type::bug,severity::S0", "state": "opened"}
        
        p0_resp = await Config.http_client.get(bugs_url, params=params, headers=headers)
        p0_count = len(p0_resp.json()) if p0_resp.is_success else 0
        p0_cleared = p0_count == 0
        
        # 3. 检查流水线稳定性 (最近一次)
        pipe_url = f"{Config.GITLAB_URL}/api/v4/projects/{project_id}/pipelines"
        pipe_resp = await Config.http_client.get(pipe_url, params={"per_page": 1}, headers=headers)
        pipe_stable = False
        if pipe_resp.is_success and pipe_resp.json():
            pipe_stable = pipe_resp.json()[0]['status'] == 'success'
            
        # 4. 检查地域风险 (Reuse get_province_quality logic or call it?)
        # Since get_province_quality is an endpoint in this router, we can call it?
        # But it expects Depends. We can extract logic or mock call?
        # Extracting logic is safer.
        # Let's just do the check manually here to avoid recursive endpoint calls.
        prov_issues_resp = await Config.http_client.get(bugs_url.replace("labels", "xxx"), params={"state":"all"}, headers=headers)
        # Actually standard issue fetch
        all_issues_resp = await Config.http_client.get(f"{Config.GITLAB_URL}/api/v4/projects/{project_id}/issues", params={"state": "all", "per_page": 100}, headers=headers)
        
        high_risk_provinces = []
        if all_issues_resp.is_success:
             all_issues = all_issues_resp.json()
             # Apply isolation? Gate check usually is global or based on user view?
             # If user is admin, global.
             
             # Count bugs per province
             prov_stats = {}
             for issue in all_issues:
                 if "type::bug" not in issue.get('labels', []): continue
                 
                 prov = "nationwide"
                 for l in issue.get('labels', []):
                     if l.startswith("province::"):
                         prov = l.split("::")[1]
                         break
                 prov_stats[prov] = prov_stats.get(prov, 0) + 1
             
             high_risk_provinces = [p for p, count in prov_stats.items() if count > 10]

        regional_free = len(high_risk_provinces) == 0
        
        is_all_passed = all([req_covered, p0_cleared, pipe_stable, regional_free])
        
        summary = "质量门禁通过，准予发布。" if is_all_passed else "质量门禁拦截，存在合规性风险。"
        
        return schemas.QualityGateStatus(
            is_passed=is_all_passed,
            requirements_covered=req_covered,
            p0_bugs_cleared=p0_cleared,
            pipeline_stable=pipe_stable,
            regional_risk_free=regional_free,
            summary=summary
        )
    except Exception as e:
        logger.error(f"Gate Check Failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/test-summary")
async def get_test_summary(project_id: int, current_user = Depends(get_current_user)):
    """获取测试用例执行状态的统计摘要，用于图表展示。"""
    url = f"{Config.GITLAB_URL}/api/v4/projects/{project_id}/issues"
    params = {
        "labels": "type::test",
        "state": "all",
        "per_page": 100
    }
    headers = {"PRIVATE-TOKEN": Config.GITLAB_PRIVATE_TOKEN}

    try:
        response = await Config.http_client.get(url, params=params, headers=headers)
        response.raise_for_status()
        issues = response.json()

        # P1 Data Isolation - Using utility function
        from devops_portal.dependencies import filter_issues_by_privacy
        # Need to pass db session? main.py used filter_issues_by_privacy without db session 
        # because the old version didn't need it? 
        # The OLD filter_issues_by_privacy in main.py called `get_user_org_scope_ids` which created its own SessionLocal.
        # The NEW one in security.py requires `db`.
        # We need to inject db here.
        
        from devops_collector.auth.database import SessionLocal
        with SessionLocal() as db:
            issues = filter_issues_by_privacy(db, issues, current_user)

        summary = {"passed": 0, "failed": 0, "blocked": 0, "pending": 0, "total": len(issues)}

        for issue in issues:
            labels = issue.get('labels', [])
            result = "pending"
            for label in labels:
                if label.startswith("test-result::"):
                    result = label.split("::")[1]
                    break
            summary[result] = summary.get(result, 0) + 1

        return summary
    except Exception as e:
        logger.error(f"Failed to fetch summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/mr-summary", response_model=schemas.MRSummary)
async def get_mr_summary(project_id: int):
    """获取并计算合并请求 (MR) 的评审统计信息 (Service 重构版)。"""
    try:
        service = TestingService()
        stats = await service.get_mr_summary_stats(project_id)
        return schemas.MRSummary(**stats)
    except Exception as e:
        logger.error(f"MR Summary failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/quality-report")
async def get_quality_report(project_id: int):
    """[UX] 动态生成基于最新 GitLab 数据的质量分析报告。"""
    service = TestingService()
    report = await service.generate_quality_report(project_id)
    return {"content": report}
