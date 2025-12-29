# -*- coding: utf-8 -*-
"""GitLab 测试管理中台 - 原型验证版

本模块作为 GitLab 社区版 (CE) 的辅助中台，通过解析 Issue 描述来实现结构化测试用例管理，
并模拟了 GitLab 企业版的测试管理功能（如执行审计、缺陷关联、流水线联动等）。
"""

import json
import logging
import random
import re
import secrets
import urllib.parse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Union

import requests
import uvicorn
from fastapi import FastAPI, HTTPException, Request, File, UploadFile, Query, Depends
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import schemas
from devops_collector.config import Config
from devops_collector.auth import services as auth_services
from devops_collector.auth import router as auth_router
from fastapi.security import OAuth2PasswordBearer
from fastapi.responses import FileResponse, PlainTextResponse, StreamingResponse
import asyncio

# 配置日志记录
logging.basicConfig(level=Config.LOG_LEVEL)
logger = logging.getLogger('TestHub')

# SSE 通知队列：{user_id: [Queue]}
NOTIFICATION_QUEUES: Dict[str, List[asyncio.Queue]] = {}

app = FastAPI(title="GitLab 测试管理中台 (Test Management Hub)")
app.include_router(auth_router.router)

# 全局内存缓存
EXECUTION_HISTORY: Dict[int, List[schemas.ExecutionRecord]] = {}
RECENT_PROJECTS: set = set()
PIPELINE_STATUS: Dict[int, Dict[str, Any]] = {}
GLOBAL_QUALITY_ALERTS: List[Dict[str, Any]] = []
SERVICE_DESK_TICKETS: Dict[str, Dict[str, Any]] = {}

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

async def get_current_user(
    token: Optional[str] = Query(None),
    auth_header: str = Depends(oauth2_scheme),
    db: Session = Depends(auth_router.get_db)
):
    """获取当前 MDM 认证用户。支持 Header 和 Query Token。"""
    final_token = token or auth_header
    if not final_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        payload = auth_services.jwt.decode(final_token, auth_services.SECRET_KEY, algorithms=[auth_services.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except auth_services.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user = auth_services.get_user_by_email(db, email=email)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user

async def push_notification(
    user_ids: Union[str, List[str]], 
    message: str, 
    type: str = 'info',
    metadata: Optional[Dict[str, Any]] = None
):
    """推送通知到 SSE（支持单播/多播/广播）。
    
    Args:
        user_ids: 接收者ID（单个str或List，特殊值 "ALL" 表示全员广播）
        message: 通知消息内容
        type: 通知类型 (info/success/warning/error)
        metadata: 附加元数据（如关联的 issue_id, project_id 等）
    
    Examples:
        # 单播
        await push_notification("user-uuid-123", "Hello", "info")
        
        # 多播
        await push_notification(["user-1", "user-2"], "Team notification", "warning")
        
        # 广播
        await push_notification("ALL", "System maintenance", "info")
    """
    # 解析目标用户列表
    if isinstance(user_ids, str):
        if user_ids == "ALL":
            # 全员广播：推送给所有在线用户
            target_users = list(NOTIFICATION_QUEUES.keys())
            logger.info(f"Broadcasting notification to all {len(target_users)} connected users")
        else:
            target_users = [user_ids]
    else:
        target_users = user_ids
    
    # 构建通知数据（包含时间戳和元数据）
    data = json.dumps({
        "message": message, 
        "type": type,
        "metadata": metadata or {},
        "timestamp": datetime.now().isoformat()
    })
    
    # 推送到目标用户的所有连接
    success_count = 0
    failed_users = []
    
    for user_id in target_users:
        if user_id in NOTIFICATION_QUEUES:
            for q in NOTIFICATION_QUEUES[user_id]:
                try:
                    await q.put(data)
                    success_count += 1
                except Exception as e:
                    logger.error(f"Failed to push notification to user {user_id}: {e}")
                    failed_users.append(user_id)
        else:
            logger.debug(f"User {user_id} not connected to SSE stream, skipping notification")
    
    logger.info(f"Notification sent: {success_count} queues, {len(target_users)} target users, {len(failed_users)} failures")


async def get_project_stakeholders(project_id: int) -> List[str]:
    """获取项目干系人的用户ID列表（P2 定向推送支持）。
    
    优先从mdm_location表的区域负责人获取，兜底逻辑为返回空列表。
    
    Args:
        project_id: GitLab 项目 ID
        
    Returns:
        List[str]: 干系人的global_user_id列表
    """
    stakeholders = []
    
    try:
        from devops_collector.auth.database import SessionLocal
        from devops_collector.models.gitlab_models import Project
        from devops_collector.models.gitlab_models import Project
        from devops_collector.models.base_models import Location, Product
        
        db = SessionLocal()
        try:
            # 方案1: 从GitLab项目关联的Location获取区域负责人
            project = db.query(Project).filter(Project.gitlab_project_id == project_id).first()
            
            if project and hasattr(project, 'location_id') and project.location_id:
                location = db.query(Location).filter(Location.location_id == project.location_id).first()
                if location and location.manager_user_id:
                    stakeholders.append(str(location.manager_user_id))
                    logger.info(f"Found location manager {location.manager_user_id} for project {project_id}")
            
            # 方案2: 从Product表的产品经理/测试经理获取（如果项目关联了产品）
            product = db.query(Product).filter(Product.project_id == project_id).first()
            if product:
                managers = [
                    product.product_manager_id,
                    product.dev_manager_id,
                    product.test_manager_id,
                    product.release_manager_id
                ]
                # 过滤None并转为str
                product_stakeholders = [str(uid) for uid in managers if uid]
                stakeholders.extend(product_stakeholders)
                logger.info(f"Found product stakeholders for project {project_id}: {product_stakeholders}")
            
            logger.info(f"Found {len(stakeholders)} stakeholders for project {project_id}")
        finally:
            db.close()
    
    except Exception as e:
        logger.warning(f"Failed to query project stakeholders: {e}, returning empty list")
    
    return stakeholders


async def get_requirement_author(project_id: int, req_iid: int) -> Optional[str]:
    """获取需求创建者的用户ID（P2 定向推送支持）。
    
    Args:
        project_id: GitLab 项目 ID
        req_iid: 需求 Issue IID
        
    Returns:
        Optional[str]: 创建者的global_user_id,未找到返回None
    """
    url = f"{Config.GITLAB_URL}/api/v4/projects/{project_id}/issues/{req_iid}"
    headers = {"PRIVATE-TOKEN": Config.GITLAB_PRIVATE_TOKEN}
    
    try:
        resp = requests.get(url, headers=headers, timeout=5)
        if resp.ok:
            issue_data = resp.json()
            author_email = issue_data.get('author', {}).get('email')
            
            if author_email:
                # 从MDM用户表查询global_user_id
                from devops_collector.auth import services as auth_services
                from devops_collector.auth.database import SessionLocal
                
                db = SessionLocal()
                try:
                    user = auth_services.get_user_by_email(db, email=author_email)
                    if user:
                        logger.info(f"Found requirement author {user.global_user_id} for req #{req_iid}")
                        return str(user.global_user_id)
                finally:
                    db.close()
        
        return None
    except Exception as e:
        logger.error(f"Failed to get requirement author: {e}")
        return None


async def get_testcase_author(project_id: int, tc_iid: int) -> Optional[str]:
    """获取测试用例创建者的用户ID（P2 定向推送支持）。
    
    Args:
        project_id: GitLab 项目 ID
        tc_iid: 测试用例 Issue IID
        
    Returns:
        Optional[str]: 创建者的global_user_id,未找到返回None
    """
    # 实现逻辑与get_requirement_author相同
    return await get_requirement_author(project_id, tc_iid)


@app.get("/notifications/stream")
async def notification_stream(current_user = Depends(get_current_user)):
    """SSE 通知流，实现实时状态更新推送。"""
    user_id = str(current_user.global_user_id)
    
    async def event_generator():
        # 为每个连接创建一个 Queue
        queue = asyncio.Queue()
        if user_id not in NOTIFICATION_QUEUES:
            NOTIFICATION_QUEUES[user_id] = []
        NOTIFICATION_QUEUES[user_id].append(queue)
        
        try:
            # 初始连接确认
            yield f"data: {json.dumps({'message': 'System Connected', 'type': 'success'})}\n\n"
            
            while True:
                data = await queue.get()
                yield f"data: {data}\n\n"
        except asyncio.CancelledError:
            # 连接断开时清理
            NOTIFICATION_QUEUES[user_id].remove(queue)
            if not NOTIFICATION_QUEUES[user_id]:
                del NOTIFICATION_QUEUES[user_id]
            raise

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# 挂载前端静态文件
app.mount("/static", StaticFiles(directory="test_hub/static"), name="static")


@app.get("/")
async def serve_index():
    """提供主前端页面。

    Returns:
        FileResponse: index.html 文件响应。
    """
    return FileResponse("test_hub/static/index.html")


def parse_markdown_to_test_case(issue: Dict[str, Any]) -> schemas.TestCase:
    """将 GitLab Issue 的 Markdown 描述解析为结构化 TestCase 对象。

    Args:
        issue: 从 GitLab API 获取的原始 Issue 字典。

    Returns:
        TestCase: 结构化测试用例对象。
    """
    desc = issue.get('description', '')
    labels = issue.get('labels', [])
    
    # 1. Parse Priority & Type from description or labels
    priority_match = re.search(r"用例优先级\]: \[(P\d)", desc)
    priority = priority_match.group(1) if priority_match else "P2"
    
    type_match = re.search(r"测试类型\]: \[(.*?)\]", desc)
    test_type = type_match.group(1) if type_match else "功能测试"
    
    req_match = re.search(r"关联需求\]: # (\d+)", desc)
    req_id = req_match.group(1) if req_match else None
    
    # 2. Parse Pre-conditions
    pre_conditions = re.findall(r"- \[ \] (.*)", desc.split("## 🛠️ 前置条件")[1].split("---")[0]) if "## 🛠️ 前置条件" in desc else []
    
    # 3. Parse Steps & Expected Results (This is a simplified parser for the demo)
    steps = []
    # Logic: Look for numbered lists under steps and expected results
    # For a real product, we'd use a more robust Markdown parser or hidden JSON blocks.
    step_actions = re.findall(r"\d+\. \*\*操作描述\*\*: (.*)", desc)
    expected_results = re.findall(r"\d+\. \*\*反馈\*\*: (.*)", desc)
    
    for i, action in enumerate(step_actions):
        steps.append(TestStep(
            step_number=i + 1,
            action=action,
            expected_result=expected_results[i] if i < len(expected_results) else "无"
        ))
    
    # 4. Determine Result Label
    result = "pending"
    for label in labels:
        if label.startswith("test-result::"):
            result = label.split("::")[1]
            break
            
    return schemas.TestCase(
        id=issue['id'],
        iid=issue['iid'],
        title=issue['title'],
        priority=priority,
        test_type=test_type,
        requirement_id=req_id,
        pre_conditions=[p.strip() for p in pre_conditions],
        steps=steps,
        result=result,
        web_url=issue['web_url'],
        linked_bugs=[] # Will be populated by a separate link check
    )

def extract_bugs_from_links(issue: Dict[str, Any]) -> List[Dict[str, str]]:
    """从 GitLab Issue 链接或提及中模拟提取关联的缺陷。

    通过解析描述中的特定模式（如 'Bug: #123'）来查找关联的缺陷。

    Args:
        issue: 原始 Issue 字典。

    Returns:
        List[Dict[str, str]]: 关联缺陷的结构化列表。
    """
    desc = issue.get('description', '')
    # 模拟正则表达式匹配
    bug_matches = re.findall(r"(?:Bug|缺陷|Fixed by|Related to)\]?: #(\d+)", desc)
    return [{"iid": bug_id, "title": f"Potential Defect #{bug_id}"} for bug_id in bug_matches]


@app.get("/projects/{project_id}/test-cases", response_model=List[schemas.TestCase])
async def list_test_cases(project_id: int):
    """获取并解析 GitLab 项目中的所有测试用例。

    Args:
        project_id: GitLab 项目 ID。

    Returns:
        List[TestCase]: 解析后的测试用例列表。

    Raises:
        HTTPException: GitLab API 调用失败时抛出。
    """
    url = f"{Config.GITLAB_URL}/api/v4/projects/{project_id}/issues"
    params = {
        "labels": "type::test",
        "state": "all",
        "per_page": 100
    }
    headers = {"PRIVATE-TOKEN": Config.GITLAB_PRIVATE_TOKEN}

    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        issues = response.json()

        test_cases = []
        for issue in issues:
            tc = parse_markdown_to_test_case(issue)
            tc.linked_bugs = extract_bugs_from_links(issue)
            test_cases.append(tc)

        return test_cases
    except Exception as e:
        logger.error(f"Failed to fetch test cases: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/projects/{project_id}/test-summary")
async def get_test_summary(project_id: int):
    """获取测试用例执行状态的统计摘要，用于图表展示。

    Args:
        project_id: GitLab 项目 ID。

    Returns:
        dict: 包含各状态数量的统计字典。

    Raises:
        HTTPException: GitLab API 调用失败时抛出。
    """
    url = f"{Config.GITLAB_URL}/api/v4/projects/{project_id}/issues"
    params = {
        "labels": "type::test",
        "state": "all",
        "per_page": 100
    }
    headers = {"PRIVATE-TOKEN": Config.GITLAB_PRIVATE_TOKEN}

    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        issues = response.json()

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

@app.get("/projects/{project_id}/mr-summary", response_model=MRSummary)
async def get_mr_summary(project_id: int):
    """获取并计算合并请求 (MR) 的评审统计信息。

    Args:
        project_id: GitLab 项目 ID。

    Returns:
        MRSummary: MR 评审统计摘要。

    Raises:
        HTTPException: GitLab API 调用失败时抛出。
    """
    url = f"{Config.GITLAB_URL}/api/v4/projects/{project_id}/merge_requests"
    headers = {"PRIVATE-TOKEN": Config.GITLAB_PRIVATE_TOKEN}
    params = {"state": "all", "per_page": 100}

    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        mrs = response.json()

        stats = {
            "total": len(mrs),
            "merged": 0, "opened": 0, "closed": 0,
            "approved": 0, "rework_needed": 0, "rejected": 0,
            "total_discussions": 0,
            "total_merge_time_sec": 0.0
        }

        for mr in mrs:
            # 1. 基础状态统计
            stats[mr['state']] += 1

            # 2. 评审标签统计 (基于自定义规范)
            labels = mr.get('labels', [])
            if "review-result::approved" in labels: stats["approved"] += 1
            if "review-result::rework" in labels: stats["rework_needed"] += 1
            if "review-result::rejected" in labels: stats["rejected"] += 1

            # 3. 讨论数统计
            stats["total_discussions"] += mr.get('user_notes_count', 0)

            # 4. 合并时长计算
            if mr['state'] == 'merged' and mr.get('merged_at'):
                created_at = datetime.fromisoformat(mr['created_at'].replace('Z', '+00:00'))
                merged_at = datetime.fromisoformat(mr['merged_at'].replace('Z', '+00:00'))
                stats["total_merge_time_sec"] += (merged_at - created_at).total_seconds()

        return MRSummary(
            total=stats["total"],
            merged=stats["merged"],
            opened=stats["opened"],
            closed=stats["closed"],
            approved=stats["approved"],
            rework_needed=stats["rework_needed"],
            rejected=stats["rejected"],
            avg_discussions=round(stats["total_discussions"] / stats["total"], 2) if stats["total"] > 0 else 0,
            avg_merge_time_hours=round(stats["total_merge_time_sec"] / (stats["merged"] * 3600), 2) if stats["merged"] > 0 else 0
        )
    except Exception as e:
        logger.error(f"Failed to fetch MR summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/projects/{project_id}/province-quality", response_model=List[ProvinceQuality])
async def get_province_quality(project_id: int, current_user = Depends(get_current_user)):
    """获取各省份的质量分布数据（已实现部门级数据隔离）。
    
    基于登录用户的 province 属性自动过滤数据：
    - 如果用户 province 为 'nationwide'：返回全量数据
    - 如果用户 province 为具体省份（如 'guangdong'）：仅返回该省份数据
    """
    url = f"{Config.GITLAB_URL}/api/v4/projects/{project_id}/issues"
    headers = {"PRIVATE-TOKEN": Config.GITLAB_PRIVATE_TOKEN}
    params = {"state": "all", "per_page": 100}

    try:
        resp = requests.get(url, params=params, headers=headers)
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
            ProvinceQuality(province=p, bug_count=v["bug_count"])
            for p, v in stats.items()
        ]
    except Exception as e:
        logger.error(f"Failed to fetch province quality: {e}")
        return []

@app.get("/projects/{project_id}/quality-gate", response_model=QualityGateStatus)
async def get_quality_gate(project_id: int):
    """自动化运行质量门禁合规性检查。"""
    try:
        # 1. 获取需求统计
        stats = await get_requirement_stats(project_id)
        req_covered = stats.coverage_rate >= 80.0
        
        # 2. 获取缺陷数据 (检查 S0 严重程度)
        bugs_url = f"{Config.GITLAB_URL}/api/v4/projects/{project_id}/issues"
        headers = {"PRIVATE-TOKEN": Config.GITLAB_PRIVATE_TOKEN}
        params = {"labels": "type::bug,severity::S0", "state": "opened"}
        p0_resp = requests.get(bugs_url, params=params, headers=headers)
        p0_count = len(p0_resp.json()) if p0_resp.ok else 0
        p0_cleared = p0_count == 0
        
        # 3. 检查流水线稳定性 (最近一次)
        pipe_url = f"{Config.GITLAB_URL}/api/v4/projects/{project_id}/pipelines"
        pipe_resp = requests.get(pipe_url, params={"per_page": 1}, headers=headers)
        pipe_stable = False
        if pipe_resp.ok and pipe_resp.json():
            pipe_stable = pipe_resp.json()[0]['status'] == 'success'
            
        # 4. 检查地域风险
        prov_data = await get_province_quality(project_id)
        # 假设单省份 Bug > 10 为风险项
        high_risk_provinces = [p for p in prov_data if p.bug_count > 10]
        regional_free = len(high_risk_provinces) == 0
        
        is_all_passed = all([req_covered, p0_cleared, pipe_stable, regional_free])
        
        summary = "质量门禁通过，准予发布。" if is_all_passed else "质量门禁拦截，存在合规性风险。"
        
        if not is_all_passed:
            # P2改造: 查询项目干系人进行定向推送
            notify_users = await get_project_stakeholders(project_id)
            
            # 兜底策略：如果未配置项目负责人，则全员广播
            if not notify_users:
                logger.warning(f"No stakeholders found for project {project_id}, using broadcast mode")
                notify_users = "ALL"
            
            asyncio.create_task(push_notification(
                notify_users,
                f"🚨 项目 {project_id} 质量门禁拦截: {summary}",
                "warning",
                metadata={
                    "project_id": project_id, 
                    "gate_status": "blocked",
                    "requirements_covered": req_covered,
                    "p0_bugs_cleared": p0_cleared,
                    "pipeline_stable": pipe_stable,
                    "regional_risk_free": regional_risk_free
                }
            ))


        return schemas.QualityGateStatus(
            is_passed=is_all_passed,
            requirements_covered=req_covered,
            p0_bugs_cleared=p0_cleared,
            pipeline_stable=pipe_stable,
            regional_risk_free=regional_free,
            summary=summary
        )
    except Exception as e:
        logger.error(f"Quality gate check failed: {e}")
        return QualityGateStatus(
            is_passed=False, requirements_covered=False, p0_bugs_cleared=False,
            pipeline_stable=False, regional_risk_free=False, summary=f"校验异常: {str(e)}"
        )

# --- 资产化测试用例库 (Asset Library) ---

@app.get("/assets/test-cases", response_model=List[AssetTestCase])
async def list_asset_test_cases(label: Optional[str] = Query(None)):
    """从公共基线库拉取可复用的测试资产，支持按标签过滤。"""
    # 假设基线库项目 ID 在配置文件中定义，若无则使用默认值或第一个项目的 ID 作为演示
    asset_project_id = getattr(Config, 'ASSET_LIBRARY_PROJECT_ID', None)
    if not asset_project_id:
        return []

    url = f"{Config.GITLAB_URL}/api/v4/projects/{asset_project_id}/issues"
    headers = {"PRIVATE-TOKEN": Config.GITLAB_PRIVATE_TOKEN}
    params = {"labels": "type::test", "state": "opened", "per_page": 50}
    if label:
        params["labels"] += f",{label}"
    
    try:
        resp = requests.get(url, headers=headers, params=params)
        if not resp.ok:
            return []
        
        issues = resp.json()
        assets = []
        for issue in issues:
            # 简单解析步骤数（示例逻辑）
            steps = re.findall(r"\| \d+ \|", issue.get("description", ""))
            assets.append(AssetTestCase(
                iid=issue["iid"],
                title=issue["title"],
                priority=next((l.split("::")[1] for l in issue["labels"] if l.startswith("priority::")), "P2"),
                test_type=next((l.split("::")[1] for l in issue["labels"] if l.startswith("test-type::")), "Functional"),
                steps_count=len(steps),
                project_id=asset_project_id
            ))
        return assets
    except Exception as e:
        logger.error(f"Failed to fetch assets: {e}")
        return []

@app.post("/projects/{project_id}/test-cases/import-from-asset")
async def import_from_asset(project_id: int, asset_iid: int, asset_project_id: int):
    """从基线库克隆一个测试用例资产到当前项目。"""
    headers = {"PRIVATE-TOKEN": Config.GITLAB_PRIVATE_TOKEN}
    
    try:
        # 1. 获取资产详情
        asset_url = f"{Config.GITLAB_URL}/api/v4/projects/{asset_project_id}/issues/{asset_iid}"
        asset_resp = requests.get(asset_url, headers=headers)
        if not asset_resp.ok:
            raise HTTPException(status_code=404, detail="Asset not found")
        
        asset_data = asset_resp.json()
        
        # 2. 在当前项目创建新 Issue
        create_url = f"{Config.GITLAB_URL}/api/v4/projects/{project_id}/issues"
        new_payload = {
            "title": f"[CLONE] {asset_data['title']}",
            "description": asset_data["description"],
            "labels": ",".join(asset_data["labels"])
        }
        create_resp = requests.post(create_url, headers=headers, json=new_payload)
        
        if create_resp.ok:
            new_issue = create_resp.json()
            return {"status": "success", "new_iid": new_issue["iid"], "message": "资产导入成功"}
        else:
            raise HTTPException(status_code=500, detail="Failed to create localized test case")
            
    except Exception as e:
        logger.error(f"Import asset failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/projects/{project_id}/province-benchmarking", response_model=List[ProvinceBenchmarking])
async def get_province_benchmarking(project_id: int, current_user = Depends(get_current_user)):
    """获取地域质量横向对标数据（已实现部门级数据隔离）。
    
    基于登录用户的 province 属性自动过滤数据：
    - 如果用户 province 为 'nationwide'：返回所有省份的对标数据
    - 如果用户 province 为具体省份（如 'guangdong'）：仅返回该省份的数据
    
    Args:
        project_id: GitLab 项目 ID
        current_user: 自动注入的当前登录用户（通过 MDM Token 解析）
    
    Returns:
        List[ProvinceBenchmarking]: 过滤后的省份质量对标数据列表
    """
    issues_url = f"{Config.GITLAB_URL}/api/v4/projects/{project_id}/issues"
    headers = {"PRIVATE-TOKEN": Config.GITLAB_PRIVATE_TOKEN}
    params = {"labels": "type::bug", "state": "all", "per_page": 100}
    
    try:
        resp = requests.get(issues_url, headers=headers, params=params)
        if not resp.ok: return []
        
        issues = resp.json()
        
        # 获取当前用户的省份权限范围（从location对象获取）
        user_location = getattr(current_user, 'location', None)
        user_province = user_location.short_name if user_location else '全国'  # 默认全国权限
        logger.info(f"User {current_user.primary_email} accessing province data with scope: {user_province}")
        
        stats = {}
        
        for issue in issues:
            province = next((l.split("::")[1] for l in issue["labels"] if l.startswith("province::")), "nationwide")
            severity = next((l.split("::")[1] for l in issue["labels"] if l.startswith("severity::")), "S2")
            is_closed = issue["state"] == "closed"
            
            # 数据隔离逻辑：根据用户省份过滤
            if user_province != '全国' and province != user_province:
                continue  # 跳过非当前用户省份的数据
            
            if province not in stats:
                stats[province] = {"total": 0, "resolved": 0, "risk_weight": 0}
            
            stats[province]["total"] += 1
            if is_closed:
                stats[province]["resolved"] += 1
            else:
                # 风险权重：S0=10, S1=5, S2=2, S3=1
                weight = {"S0": 10, "S1": 5, "S2": 2, "S3": 1}.get(severity, 1)
                stats[province]["risk_weight"] += weight
        
        benchmarks = []
        for p, s in stats.items():
            res_rate = (s["resolved"] / s["total"] * 100) if s["total"] > 0 else 100
            # 风险评分归一化处理（示例：累计权重超过30分为高位100）
            risk_score = min(100, (s["risk_weight"] / 30.0) * 100)
            
            benchmarks.append(ProvinceBenchmarking(
                province=p,
                bug_count=s["total"],
                resolved_count=s["resolved"],
                unresolved_count=s["total"] - s["resolved"],
                resolution_rate=round(res_rate, 1),
                risk_score=round(risk_score, 1)
            ))
        
        # 按风险评分降序排列
        return sorted(benchmarks, key=lambda x: x.risk_score, reverse=True)
    except Exception as e:
        logger.error(f"Benchmarking failed: {e}")
        return []

async def sync_requirement_health_to_gitlab(project_id: int, requirement_iid: int):
    """根据关联测试用例的状态，自动同步需求的健康状态到 GitLab。
    
    逻辑：
    - 如果所有关联用例均通过 -> status::satisfied
    - 如果存在任何关联用例失败 -> status::failed
    - 如果没有任何关联用例 -> 保持现状
    """
    headers = {"PRIVATE-TOKEN": Config.GITLAB_PRIVATE_TOKEN}
    try:
        # 1. 获取需求详情（包含用例结果）
        req_detail = await get_requirement_detail(project_id, requirement_iid)
        if not req_detail.test_cases:
            return

        # 2. 计算目标状态
        all_passed = all(tc.result == "passed" for tc in req_detail.test_cases)
        any_failed = any(tc.result == "failed" for tc in req_detail.test_cases)
        
        target_status = None
        if all_passed:
            target_status = "satisfied"
        elif any_failed:
            target_status = "failed"
            
        if not target_status:
            return

        # 3. 更新 GitLab 标签 (status::*)
        url = f"{Config.GITLAB_URL}/api/v4/projects/{project_id}/issues/{requirement_iid}"
        get_resp = requests.get(url, headers=headers)
        get_resp.raise_for_status()
        current_labels = get_resp.json().get('labels', [])

        new_labels = [l for l in current_labels if not l.startswith("status::")]
        new_labels.append(f"status::{target_status}")

        requests.put(url, json={"labels": ",".join(new_labels)}, headers=headers)

        # 4. 自动审计
        comment_body = (
            f"🤖 **TestHub 自动化状态反馈**\n"
            f"- **需求状态更新**: {target_status.upper()}\n"
            f"- **触发原因**: 关联的所有测试用例已完成验证\n"
            f"- **结果详情**: {len(req_detail.test_cases)} 个用例已同步"
        )
        requests.post(f"{url}/notes", json={"body": comment_body}, headers=headers)
        logger.info(f"Auto-synced requirement #{requirement_iid} status to {target_status}")

    except Exception as e:
        logger.error(f"Failed to auto-sync requirement status: {e}")


@app.post("/projects/{project_id}/test-cases/{issue_iid}/execute")
async def execute_test_case(project_id: int, issue_iid: int, result: str = Query(...), report: Optional[ExecutionReport] = None):
    """执行测试用例并更新 GitLab 标签、状态及审计记录。

    Args:
        project_id: GitLab 项目 ID。
        issue_iid: 项目内议题 IID。
        result: 执行结果 (passed/failed/blocked)。
        report: 详细执行报表内容。
    """
    final_result = result or (report.result if report else None)
    if not final_result or final_result not in ["passed", "failed", "blocked"]:
        raise HTTPException(status_code=400, detail="Invalid result status")
    
    executor = f"{current_user.full_name} ({current_user.primary_email})"
    executor_uid = str(current_user.global_user_id)
    comment = report.comment if report else None

    url = f"{Config.GITLAB_URL}/api/v4/projects/{project_id}/issues/{issue_iid}"
    headers = {"PRIVATE-TOKEN": Config.GITLAB_PRIVATE_TOKEN}

    try:
        # 1. 获取当前标签，移除旧的执行结果标签
        get_resp = requests.get(url, headers=headers)
        get_resp.raise_for_status()
        current_labels = get_resp.json().get('labels', [])

        new_labels = [l for l in current_labels if not l.startswith("test-result::")]
        new_labels.append(f"test-result::{final_result}")

        # 2. 更新议题状态
        payload = {
            "labels": ",".join(new_labels)
        }

        if final_result == "passed":
            payload["state_event"] = "close"
        else:
            payload["state_event"] = "reopen"

        put_resp = requests.put(url, json=payload, headers=headers)
        put_resp.raise_for_status()

        # 2.5 在 GitLab 中添加评论反馈 (增强社区版的可追溯性)
        comment_url = f"{Config.GITLAB_URL}/api/v4/projects/{project_id}/issues/{issue_iid}/notes"
        comment_body = (
            f"🚀 **测试执行反馈**\n"
            f"- **结果**: {final_result.upper()}\n"
            f"- **执行人**: {executor}\n"
            f"- **时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        if comment:
            comment_body += f"\n- **详情**: {comment}"
        try:
            requests.post(comment_url, json={"body": comment_body}, headers=headers)
        except Exception as e:
            logger.warning(f"Failed to post note to GitLab: {e}")

        # 3. 记录本地审计历史 (模拟数据库)
        if issue_iid not in EXECUTION_HISTORY:
            EXECUTION_HISTORY[issue_iid] = []

        record = schemas.ExecutionRecord(
            issue_iid=issue_iid,
            result=final_result,
            executed_at=datetime.now(),
            executor=executor,
            comment=comment,
            pipeline_id=PIPELINE_STATUS.get(project_id, {}).get("id")
        )
        EXECUTION_HISTORY[issue_iid].insert(0, record)

        # --- 增强：自动化反馈钩子 ---
        try:
            # 1. 解析当前测试用例以查找关联的需求 IID
            tc_obj = parse_markdown_to_test_case(get_resp.json())
            
            # --- 黑科技 2.0：失败自动提单 (Auto-Issue) ---
            if final_result == "failed":
                bug_title = f"自动捕获缺陷: {tc_obj.title}"
                bug_desc = (
                    f"### 🤖 TestHub 自动报障系统\n"
                    f"检测到测试执行失败，已自动开启排障流。\n\n"
                    f"- **关联用例**: #{issue_iid} ({tc_obj.web_url})\n"
                    f"- **执行人**: {executor}\n"
                    f"- **失败详情**: {comment if comment else '未提供详细错误信息'}\n"
                    f"- **环境**: {report.environment if report else 'Default'}\n"
                )
                
                bug_payload = {
                    "title": bug_title,
                    "description": bug_desc,
                    "labels": f"type::bug,status::opened,severity::S2,priority::P2,origin::auto-robot"
                }
                
                bug_resp = requests.post(
                    f"{Config.GITLAB_URL}/api/v4/projects/{project_id}/issues",
                    headers=headers,
                    json=bug_payload
                )
                if bug_resp.status_code == 201:
                    bug_iid = bug_resp.json().get("iid")
                    logger.info(f"Auto-Issue created: #{bug_iid} for test case #{issue_iid}")
                    # 在用例评论中追加 Bug 链接
                    link_note = f"⚠️ **已自动提单监控**: [Bug #{bug_iid}]({bug_resp.json().get('web_url')})"
                    requests.post(comment_url, json={"body": link_note}, headers=headers)

            # --- 黑科技 3.0：全网同步预警 (Global Sync Alert) ---
            if final_result == "failed":
                province = next((l.split("::")[1] for l in current_labels if l.startswith("province::")), "全国")
                alert = {
                    "id": len(GLOBAL_QUALITY_ALERTS) + 1,
                    "province": province.upper(),
                    "project_id": project_id,
                    "title": tc_obj.title,
                    "time": datetime.now().strftime('%H:%M:%S'),
                    "has_evidence": "📸" in (comment or ""),
                    "level": "critical" if "S0" in ",".join(current_labels) else "warning"
                }
                GLOBAL_QUALITY_ALERTS.insert(0, alert)
                if len(GLOBAL_QUALITY_ALERTS) > 15: GLOBAL_QUALITY_ALERTS.pop() # 仅保持最新 15 条
                
                
                # --- P2改造：多方定向推送测试失败通知 ---
                # 收集通知对象: 执行者 + 用例创建者 + 需求负责人
                notify_users = [executor_uid]  # 包含执行者本人
                
                # 1. 通知用例创建者(如果不是执行者本人)
                tc_author_id = await get_testcase_author(project_id, issue_iid)
                if tc_author_id and tc_author_id != executor_uid:
                    notify_users.append(tc_author_id)
                    logger.info(f"Added test case author {tc_author_id} to notification list")
                
                # 2. 如果关联了需求,通知需求负责人
                if tc_obj.requirement_id:
                    req_author = await get_requirement_author(project_id, int(tc_obj.requirement_id))
                    if req_author and req_author not in notify_users:
                        notify_users.append(req_author)
                        logger.info(f"Added requirement author {req_author} to notification list")
                
                # 推送通知
                if notify_users:
                    asyncio.create_task(push_notification(
                        notify_users,
                        f"⚠️ 测试用例 #{issue_iid} 执行失败: {tc_obj.title}",
                        "error",
                        metadata={
                            "issue_iid": issue_iid,
                            "project_id": project_id,
                            "test_case_title": tc_obj.title,
                            "severity": "critical" if "S0" in ",".join(current_labels) else "normal",
                            "province": province,
                            "executor": executor,
                            "requirement_id": tc_obj.requirement_id
                        }
                    ))


            if tc_obj.requirement_id:
                req_iid = int(tc_obj.requirement_id)
                import asyncio
                # 异步触发需求状态评估
                asyncio.create_task(sync_requirement_health_to_gitlab(project_id, req_iid))
        except Exception as e:
            logger.error(f"Auto-feedback hook failed for test case {issue_iid}: {e}")
        
        return {
            "status": "success",
            "new_result": result,
            "new_state": put_resp.json().get('state'),
            "history": EXECUTION_HISTORY[issue_iid][:5]
        }

    except Exception as e:
        logger.error(f"Failed to execute test case #{issue_iid}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/projects/{project_id}/rtm-report")
async def export_rtm_report(project_id: int):
    """生成端到端需求跟踪矩阵 (Requirement Traceability Matrix) 报告。"""
    try:
        # 1. 获取所有需求及关联用例详情
        reqs = await list_requirements(project_id)
        approved_reqs = [r for r in reqs if r.review_state == "approved"]
        
        # 并行获取详情
        import asyncio
        details = await asyncio.gather(*[get_requirement_detail(project_id, r.iid) for r in approved_reqs])
        
        # 2. 生成 Markdown 内容
        md = f"# 📋 端到端需求跟踪矩阵 (RTM) 报告\n"
        md += f"> **生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        md += f"> **项目 ID**: {project_id}\n\n"
        
        # 摘要信息
        total_reqs = len(approved_reqs)
        covered_reqs = sum(1 for r in details if r.test_cases)
        coverage_pct = round((covered_reqs / total_reqs * 100), 2) if total_reqs > 0 else 0
        
        md += "## 📊 追溯摘要\n"
        md += f"- **已审核需求总数**: {total_reqs}\n"
        md += f"- **已关联用例需求**: {covered_reqs}\n"
        md += f"- **全流程追溯覆盖率**: {coverage_pct}%\n\n"
        
        md += "## 📑 跟踪明细矩阵\n"
        md += "| 需求 IID | 需求名称 | 关联测试用例 (IID) | 验证状态 | 最后执行结果 |\n"
        md += "| :--- | :--- | :--- | :--- | :--- |\n"
        
        for req in details:
            status_map = {"satisfied": "✅ 满足", "failed": "❌ 失败", "closed": "✅ 满足"}
            req_status = status_map.get(req.state, "📝 验证中")
            
            if not req.test_cases:
                md += f"| #{req.iid} | {req.title} | *未关联* | ⚠ 未覆盖 | - |\n"
            else:
                for idx, tc in enumerate(req.test_cases):
                    res_tag = "🟢 PASS" if tc.result == "passed" else ("🔴 FAIL" if tc.result == "failed" else "🟡 PENDING")
                    if idx == 0:
                        md += f"| #{req.iid} | {req.title} | #{tc.iid} {tc.title} | {req_status} | {res_tag} |\n"
                    else:
                        md += f"| | | #{tc.iid} {tc.title} | | {res_tag} |\n"
        
        # 3. 增强：需求变更历史追踪 (Change History)
        md += "\n## 🕓 需求评审历史与变更轨迹\n"
        md += "| 关联需求 | 变更动作 | 评审人/执行者 | 变更时间 | 备注 |\n"
        md += "| :--- | :--- | :--- | :--- | :--- |\n"
        
        headers = {"PRIVATE-TOKEN": Config.GITLAB_PRIVATE_TOKEN}
        for req in details:
            try:
                # 获取该 Issue 的所有评论 (Notes)
                notes_url = f"{Config.GITLAB_URL}/api/v4/projects/{project_id}/issues/{req.iid}/notes"
                notes_resp = requests.get(notes_url, headers=headers)
                if notes_resp.status_code == 200:
                    notes = notes_resp.json()
                    # 过滤评审相关的审计评论
                    review_notes = [n for n in notes if "需求评审状态变更" in n.get('body', '')]
                    for n in review_notes:
                        body = n.get('body', '')
                        # 简单提取状态：从 "- **目标状态**: XXX" 中解析
                        state_match = re.search(r"\*\*目标状态\*\*: (.*)", body)
                        target_state = state_match.group(1).strip() if state_match else "UNKNOWN"
                        
                        # 提取时间
                        time_match = re.search(r"\*\*时间\*\*: (.*)", body)
                        change_time = time_match.group(1).strip() if time_match else n.get('created_at')
                        
                        md += f"| #{req.iid} | 流转至 `{target_state}` | 系统/评审员 | {change_time} | 自动审计存档 |\n"
            except Exception as e:
                logger.warning(f"Failed to fetch notes for audit: {e}")

        md += "\n---\n*Report generated by TestHub System*"
        
        # 3. 返回文件流
        from fastapi.responses import Response
        return Response(
            content=md,
            media_type="text/markdown",
            headers={"Content-Disposition": f"attachment; filename=RTM_Report_P{project_id}.md"}
        )
    except Exception as e:
        logger.error(f"Failed to generate RTM report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/projects/{project_id}/upload")
async def upload_file_to_gitlab(project_id: int, file: UploadFile = File(...)):
    """将图片或附件上传至 GitLab 项目存储空间。"""
    try:
        url = f"{Config.GITLAB_URL}/api/v4/projects/{project_id}/uploads"
        headers = {"PRIVATE-TOKEN": Config.GITLAB_PRIVATE_TOKEN}
        
        content = await file.read()
        files = {"file": (file.filename, content)}
        
        resp = requests.post(url, headers=headers, files=files)
        if resp.status_code != 201:
            raise Exception(f"GitLab upload failed: {resp.text}")
            
        data = resp.json()
        # 返回 GitLab 要求的 markdown 引用格式
        return {"markdown": data.get("markdown"), "url": data.get("full_path")}
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        return HTTPException(status_code=500, detail=str(e))

@app.post("/projects/{project_id}/test-cases/{iid}/generate-code")
async def generate_unit_test_code(project_id: int, iid: int, request: Request):
    """基于人工测试用例步骤，生成具备『自动回传联动』能力的智能脚本模板。"""
    try:
        # 1. 获取用例详情
        case = await get_test_case_detail(project_id, iid)
        
        # 2. 自动探测中台服务地址以便回传
        base_url = str(request.base_url).rstrip('/')
        
        # 3. 构造代码生成模板 (注入上报基因)
        steps_logic = ""
        for s in case.steps:
            steps_logic += f"            # Step {s['step_number']}: {s['action']}\n"
            steps_logic += f"            # Expected: {s['expected_result']}\n"
            steps_logic += f"            self.assertTrue(True) # TODO: 这里填入对应的自动化操作 (如 Selenium click/requests get)\n\n"

        code_template = f'''"""
Unit Test for Case #{case.iid}: {case.title}
-----------------------------------------------------------
Generated by TestHub Magic Engine [Test-as-Code Live Sync]
This script will automatically sync execution status back to Hub.
"""
import unittest
import requests
import json
import logging
from datetime import datetime

class Test{case.iid}_LiveSync(unittest.TestCase):
    """具备实时同步能力的测试类"""
    
    HUB_URL = "{base_url}" 
    PROJECT_ID = {project_id}
    CASE_IID = {case.iid}
    PRIVATE_TOKEN = "{Config.GITLAB_PRIVATE_TOKEN[:5]}***" # 建议安全处理

    def setUp(self):
        """测试前置准备 - Pre-condition: {case.pre_conditions}"""
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger("RobotSync")

    def upload_screenshot(self, file_path):
        """黑科技：将失败截图上传至 GitLab 资产库"""
        try:
            upload_url = f"{{self.HUB_URL}}/static/projects/{{self.PROJECT_ID}}/upload" # 修正为中台中转代理
            with open(file_path, "rb") as f:
                resp = requests.post(upload_url, files={{"file": f}}, timeout=10)
                if resp.status_code == 200:
                    return resp.json().get("markdown")
        except Exception as e:
            self.logger.error(f"Screenshot upload failed: {{e}}")
        return None

    def report_status(self, result, error_msg=None, screenshot_md=None):
        """将机器人执行结果及资产证据上报给 TestHub"""
        try:
            endpoint = f"{{self.HUB_URL}}/projects/{{self.PROJECT_ID}}/test-cases/{{self.CASE_IID}}/execute?result={{result}}"
            comment = f"Auto-Sync Failure: {{error_msg}}" if error_msg else "Auto-Sync Success: All steps passed."
            if screenshot_md:
                comment += f"\\n\\n📸 **失败现场证据**:\\n{{screenshot_md}}"

            payload = {{"executor": "Robot AI 🤖", "comment": comment}}
            requests.post(endpoint, json=payload, timeout=5)
            self.logger.info(f"Successfully synced {{result}} status and evidence back to Hub.")
        except Exception as e:
            self.logger.error(f"Failed to sync with Hub: {{e}}")

    def test_logic(self):
        """执行人工定义的测试流 (包含自动侦测现场)"""
        try:
            self.logger.info("Starting automated flow for #{case.iid}...")
{steps_logic}
            self.report_status("passed")
        except Exception as e:
            # 自动化黑科技：检测到异常，触发“证据保存”
            screenshot_path = f"error_case_{case.iid}.png"
            # self.driver.save_screenshot(screenshot_path) # Selenium/Playwright 示例
            self.logger.error(f"Detected failure, capturing evidence...")
            
            # 模拟生成现场证据 (实际环境中由框架生成)
            with open(screenshot_path, "w") as f: f.write("Mock Image Content") 
            
            img_md = self.upload_screenshot(screenshot_path)
            self.report_status("failed", str(e), screenshot_md=img_md)
            raise e

if __name__ == '__main__':
    unittest.main()
'''
        return {"iid": iid, "code": code_template}
    except Exception as e:
        logger.error(f"Magic Generation Failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/projects/{project_id}/test-report")
async def export_test_report(project_id: int):
    """生成包含测试执行与缺陷全景分析的 Markdown 质量报告。

    Args:
        project_id: GitLab 项目 ID。

    Returns:
        PlainTextResponse: Markdown 报告文件流响应。

    Raises:
        HTTPException: 报告生成过程出错时抛出。
    """
    url = f"{Config.GITLAB_URL}/api/v4/projects/{project_id}/issues"
    params = {"labels": "type::test", "state": "all", "per_page": 100}
    headers = {"PRIVATE-TOKEN": Config.GITLAB_PRIVATE_TOKEN}

    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        issues = response.json()

        test_cases = []
        for issue in issues:
            tc = parse_markdown_to_test_case(issue)
            tc.linked_bugs = extract_bugs_from_links(issue)
            test_cases.append(tc)

        # 统计摘要
        summary = {"passed": 0, "failed": 0, "blocked": 0, "pending": 0, "total": len(test_cases), "bugs_count": 0}
        for tc in test_cases:
            summary[tc.result] += 1
            summary["bugs_count"] += len(tc.linked_bugs)

        pass_rate = round((summary['passed'] / summary['total']) * 100, 2) if summary['total'] > 0 else 0

        # 获取项目中所有的缺陷用于深度分析
        bugs_details = []
        try:
            bug_resp = requests.get(f"{Config.GITLAB_URL}/api/v4/projects/{project_id}/issues", params={"state": "all", "per_page": 100}, headers=headers)
            if bug_resp.ok:
                all_issues = bug_resp.json()
                for is_data in all_issues:
                    labels = [l.lower() for l in is_data.get('labels', [])]
                    if any(kw in "".join(labels) for kw in ['bug', '缺陷', 'defect']):
                        bugs_details.append(is_data)
        except Exception:
            pass

        # 生成 Markdown 内容
        report = f"# 🧪 测试全景质量报告 - PID: {project_id}\n\n"
        report += f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        report += f"**报告类型**: 定制化二开测试管理模块自动化导报\n\n"

        report += "## 📊 质量核心指标 (Quality Dashboard)\n\n"
        report += f"- **总用例数 (Total Scenarios)**: {summary['total']}\n"
        report += f"- **发现缺陷总数 (Defects Found)**: `{len(bugs_details)}` {'🔥' if len(bugs_details) > 5 else '✅'}\n"
        report += f"- **用例通过率 (Success Rate)**: `{pass_rate}%` {'✅' if pass_rate >= 90 else '⚠️'}\n"
        report += f"- **分布详情**: {summary['passed']} 通过 | {summary['failed']} 失败 | {summary['blocked']} 阻塞 | {summary['pending']} 待执行\n\n"

        report += "## 🐞 缺陷全景分析 (Defect Landscape)\n\n"
        if not bugs_details:
            report += "> *当前项目未录入任何缺陷记录。*\n\n"
        else:
            report += "| IID | 缺陷标题 | 状态 | 报告人 | 创建日期 |\n"
            report += "|:---|:---|:---|:---|:---|\n"
            for b_data in bugs_details:
                state_icon = "🔴 OPEN" if b_data['state'] == 'opened' else "🟢 FIXED"
                report += f"| #{b_data['iid']} | [{b_data['title']}]({b_data['web_url']}) | {state_icon} | {b_data.get('author',{}).get('name')} | {b_data['created_at'][:10]} |\n"
            report += "\n"

        report += "## 🧪 用例执行细节 (Test Execution Details)\n\n"
        report += "| IID | 标题 | 结果 | 关联缺陷 (Bugs) | 需求引用 |\n"
        report += "|:---|:---|:---|:---|:---|\n"

        for tc in test_cases:
            result_icon = {"passed": "✅ Pass", "failed": "❌ Fail", "blocked": "🚫 Block", "pending": "⏳ Pend"}.get(tc.result, "❓ Unknown")
            bug_links = ", ".join([f"[#{b['iid']}]" for b in tc.linked_bugs]) if tc.linked_bugs else "-"
            report += f"| #{tc.iid} | [{tc.title}]({tc.web_url}) | {result_icon} | {bug_links} | #{tc.requirement_id or 'N/A'} |\n"

        report += "\n---\n*本报告由 GitLab 社区版二开测试管理中台自动生成。不可篡改。*"

        return PlainTextResponse(report, headers={
            "Content-Disposition": f"attachment; filename=quality_report_p{project_id}.md"
        })

    except Exception as e:
        logger.error(f"Failed to generate report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/recent-projects")
async def get_recent_projects():
    """获取最近访问的项目列表。

    Returns:
        list: 项目 ID 列表。
    """
    return list(RECENT_PROJECTS)


@app.get("/projects/{project_id}/test-cases/{issue_iid}/history")
async def get_execution_history(issue_iid: int):
    """获取指定测试用例的模拟审计历史记录。

    Args:
        issue_iid: 测试用例 IID。

    Returns:
        list: 执行记录列表。
    """
    return EXECUTION_HISTORY.get(issue_iid, [])

@app.get("/projects/{project_id}/test-cases/{issue_iid}/bug-link")
async def get_bug_report_link(project_id: int, issue_iid: int):
    """生成预填故障详情的 GitLab 'New Issue' 链接。

    Args:
        project_id: GitLab 项目 ID。
        issue_iid: 测试用例 IID。

    Returns:
        dict: 包含生成链接的字典。
    """
    base_url = f"{Config.GITLAB_URL}/api/v4/projects/{project_id}/issues/{issue_iid}"
    headers = {"PRIVATE-TOKEN": Config.GITLAB_PRIVATE_TOKEN}
    resp = requests.get(base_url, headers=headers).json()

    title = f"Bug found in: {resp.get('title', 'Test Case')}"
    description = (
        f"### 🛡️ Test Failure Report\n\n"
        f"- **Target Case**: #{issue_iid} ({resp.get('web_url')})\n"
        f"- **Detected At**: {datetime.now().isoformat()}\n"
        f"- **Reproduction**: See steps in linked test case.\n\n"
        f"### 📝 Additional Context\nAutomatically generated via QA Hub."
    )

    params = {
        "issue[title]": title,
        "issue[description]": description,
        "add_labels": "type::bug,status::confirmed"
    }

    if resp.get('web_url'):
        web_base = resp['web_url'].split('/-/issues')[0]
        link = f"{web_base}/-/issues/new?{urllib.parse.urlencode(params)}"
        return {"url": link}

    return {"url": "#"}


@app.post("/projects/{project_id}/test-cases")
async def create_test_case(project_id: int, data: TestCaseCreate):
    """将表单数据转换为 Markdown 模板，并在 GitLab 中创建新的测试用例议题。

    Args:
        project_id: GitLab 项目 ID。
        data: 创建用例的载荷数据。

    Returns:
        dict: 创建成功后的议题信息。

    Raises:
        HTTPException: GitLab API 调用失败时抛出。
    """
    # 1. 构造 Markdown 描述内容
    md = "## 📋 测试概览\n"
    md += f"- **优先级**: {data.priority}\n"
    md += f"- **测试类型**: {data.test_type}\n"
    if data.requirement_id:
        md += f"- **关联需求**: #{data.requirement_id}\n"

    md += f"\n## 🛠️ 前置条件\n{data.pre_conditions or '无'}\n"

    md += "\n## 📝 测试步骤\n"
    for i, step in enumerate(data.steps):
        md += f"{i+1}. **操作描述**: {step['action']}\n"
        md += f"   **反馈**: {step['expected']}\n"

    md += "\n\n--- \n*Generated by GitLab Test Hub*"

    # 2. 调用 GitLab API 创建议题
    url = f"{Config.GITLAB_URL}/api/v4/projects/{project_id}/issues"
    headers = {"PRIVATE-TOKEN": Config.GITLAB_PRIVATE_TOKEN}
    payload = {
        "title": data.title,
        "description": md,
        "labels": "type::test"
    }

    try:
        resp = requests.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        return {"status": "success", "issue": resp.json()}
    except Exception as e:
        logger.error(f"Failed to create test case: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/projects/{project_id}/bugs", response_model=List[BugDetail])
async def get_project_bugs(project_id: int):
    """获取项目中所有的缺陷，用于追踪修复进度。

    Args:
        project_id: GitLab 项目 ID。

    Returns:
        List[BugDetail]: 缺陷详情列表。

    Raises:
        HTTPException: GitLab API 调用失败时抛出。
    """
    url = f"{Config.GITLAB_URL}/api/v4/projects/{project_id}/issues"
    params = {"state": "all", "per_page": 100}
    headers = {"PRIVATE-TOKEN": Config.GITLAB_PRIVATE_TOKEN}

    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        issues = response.json()

        bugs = []
        for issue in issues:
            labels = [l.lower() for l in issue.get('labels', [])]
            if any(kw in "".join(labels) for kw in ['bug', '缺陷', 'defect']):
                bugs.append(BugDetail(
                    iid=issue['iid'],
                    title=issue['title'],
                    state=issue['state'],
                    created_at=datetime.fromisoformat(issue['created_at'].replace('Z', '+00:00')),
                    author=issue.get('author', {}).get('name', 'Unknown'),
                    web_url=issue['web_url'],
                    labels=issue.get('labels', [])
                ))
        return bugs
    except Exception as e:
        logger.error(f"Failed to fetch bugs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/projects/{project_id}/pipeline-status")
async def get_project_pipeline_status(project_id: int):
    """返回通过 Webhook 同步的项目最新流水线数据。

    Args:
        project_id: GitLab 项目 ID。

    Returns:
        dict: 流水线状态数据。
    """
    return PIPELINE_STATUS.get(project_id, {"status": "unknown"})


@app.post("/webhook")
async def gitlab_webhook(request: Request):
    """处理来自 GitLab 的 Webhook 实时同步请求。

    Args:
        request: FastAPI 请求对象。

    Returns:
        dict: 处理状态结果。
    """
    try:
        payload = await request.json()
        event_type = request.headers.get("X-Gitlab-Event")

        if event_type == "Issue Hook":
            object_attr = payload.get("object_attributes", {})
            labels = [l.get("title") for l in payload.get("labels", [])]
            issue_iid = object_attr.get("iid")
            action = object_attr.get("action")

            if "type::test" in labels:
                logger.info(f"Webhook Received: Test Case #{issue_iid} was {action}")
            

            # --- 核心增强：需求状态双向同步感应 ---
            if "type::requirement" in labels:
                p_id = payload.get("project", {}).get("id")
                review_state = "draft"
                status_state = "pending"
                
                for l in labels:
                    if l.startswith("review-state::"):
                        review_state = l.replace("review-state::", "")
                    if l.startswith("status::"):
                        status_state = l.replace("status::", "")

                logger.info(f"Requirement Sync: #{issue_iid} in Project {p_id} updated: review={review_state}, status={status_state}, action={action}")
                
                # 如果是 Close 操作，自动触发健康度评估
                if action == "close":
                    logger.warning(f"Requirement #{issue_iid} was CLOSED in GitLab UI.")
                    import asyncio
                    asyncio.create_task(sync_requirement_health_to_gitlab(p_id, issue_iid))

                # P2改造: 需求评审状态变更通知
                if action == "update" and review_state != "draft":
                    try:
                        # 1. 获取需求作者
                        author_id = await get_requirement_author(p_id, issue_iid)
                        # 2. 获取项目干系人 (从Product/Location)
                        stakeholders = await get_project_stakeholders(p_id)
                        
                        notify_targets = set(stakeholders)
                        if author_id:
                            notify_targets.add(author_id)
                        
                        if notify_targets:
                            asyncio.create_task(push_notification(
                                list(notify_targets),
                                f"📢 需求评审状态更新: #{issue_iid} 已流转至 [{review_state}]",
                                "info",
                                metadata={
                                    "project_id": p_id,
                                    "issue_iid": issue_iid,
                                    "type": "requirement_review",
                                    "new_state": review_state
                                }
                            ))
                            logger.info(f"Sent review notification to {len(notify_targets)} users")
                    except Exception as e:
                        logger.error(f"Failed to send review notification: {e}")
            
            # --- Service Desk 工单双向同步（GitLab → Service Desk）---
            if "origin::service-desk" in labels:
                p_id = payload.get("project", {}).get("id")
                
                # 查找对应的工单
                for tracking_code, ticket in SERVICE_DESK_TICKETS.items():
                    if (ticket.get("gitlab_issue_iid") == issue_iid and 
                        ticket.get("project_id") == p_id):
                        
                        # 同步状态
                        old_status = ticket.get("status")
                        new_status = old_status
                        
                        if object_attr.get("state") == "closed":
                            new_status = "completed"
                        elif "in-progress" in labels:
                            new_status = "in-progress"
                        elif "rejected" in labels or "status::rejected" in labels:
                            new_status = "rejected"
                        elif object_attr.get("state") == "opened":
                            new_status = "pending"
                        
                        ticket["status"] = new_status
                        
                        # 同步标题（去除 [Service Desk] 前缀）
                        title = object_attr.get("title", "")
                        if title.startswith("[Service Desk] "):
                            title = title.replace("[Service Desk] ", "")
                        ticket["title"] = title
                        
                        # 同步更新时间
                        ticket["updated_at"] = object_attr.get("updated_at", ticket["updated_at"])
                        
                        # 持久化保存
                        save_service_desk_tickets()
                        
                        logger.info(f"✅ Service Desk Sync: {tracking_code} status updated from GitLab: {old_status} → {new_status}")
                        break


        # 处理流水线事件
        if event_type == "Pipeline Hook":
            p_id = payload.get("project", {}).get("id")
            if p_id:
                obj = payload.get("object_attributes", {})
                PIPELINE_STATUS[p_id] = {
                    "id": obj.get("id"),
                    "status": obj.get("status"),
                    "ref": obj.get("ref"),
                    "sha": obj.get("sha")[:8] if obj.get("sha") else "N/A",
                    "finished_at": obj.get("finished_at"),
                    "user_name": payload.get("user_name")
                }
                logger.info(f"Pipeline Sync: Project {p_id} is now {obj.get('status')}")

                # 实时推送告警：如果流水线失败，推送到对应的提交人
                if obj.get("status") == "failed":
                    user_email = payload.get("user_email")
                    if user_email:
                        db = SessionLocal()
                        try:
                            # 1. 通知Commit作者
                            target_user = auth_services.get_user_by_email(db, user_email)
                            notify_uids = []
                            
                            if target_user:
                                notify_uids.append(str(target_user.global_user_id))
                                
                            # 2. P2改造: 通知项目干系人 (Product Managers etc)
                            stakeholders = await get_project_stakeholders(p_id)
                            notify_uids.extend(stakeholders)
                            
                            # 去重
                            final_notify_list = list(set(notify_uids))
                            
                            # 兜底：如果没找到人，广播
                            if not final_notify_list:
                                logger.warning(f"No stakeholders found for pipeline failure in {p_id}")
                                # final_notify_list = "ALL"  # 避免噪音，暂时不全员广播
                            
                            if final_notify_list:
                                asyncio.create_task(push_notification(
                                    final_notify_list,
                                    f"❌ 流水线失败告警: 项目 {p_id} ({obj.get('ref')}) 执行失败，请及时处理。",
                                    "error",
                                    metadata={
                                        "project_id": p_id,
                                        "pipeline_id": obj.get("id"),
                                        "status": "failed",
                                        "committer": user_email
                                    }
                                ))
                        finally:
                            db.close()

        return {"status": "accepted"}
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return {"status": "error", "message": str(e)}

async def get_user_project_access_level(project_id: int, user_id: int) -> int:
    """获取用户在 GitLab 项目中的访问等级。
    
    Access Levels:
    - 10: Guest
    - 20: Reporter
    - 30: Developer
    - 40: Maintainer
    - 50: Owner
    """
    url = f"{Config.GITLAB_URL}/api/v4/projects/{project_id}/members/all/{user_id}"
    headers = {"PRIVATE-TOKEN": Config.GITLAB_PRIVATE_TOKEN}
    
    try:
        resp = requests.get(url, headers=headers)
        if resp.status_code == 200:
            return resp.json().get("access_level", 0)
        return 0
    except Exception as e:
        logger.error(f"Failed to fetch user access level: {e}")
        return 0


@app.post("/projects/{project_id}/requirements/check-conflicts")
async def check_requirement_conflicts(project_id: int, req: RequirementCreate):
    """黑科技：在需求保存前进行语义冲突探测。"""
    try:
        # 1. 获取所有已存在的需求
        existing_reqs = await list_requirements(project_id)
        
        conflicts = []
        new_text = f"{req.title} {req.description}".lower()
        
        # 定义一些互斥关键词对 (示例逻辑)
        mutually_exclusive = [
            ("实名", "匿名"), ("必须登录", "无需登录"), 
            ("权限验证", "取消验证"), ("增删改", "只读"),
            ("付费", "免费"), ("HTTPS", "HTTP")
        ]

        for ex in existing_reqs:
            # 简单模拟获取详情（实际生产中应优化为批量查询或索引搜索）
            ex_text = f"{ex.title}".lower() # 简化版仅比对标题
            
            # 关键词重叠度计算
            words_new = set(re.findall(r'\w+', new_text))
            words_ex = set(re.findall(r'\w+', ex_text))
            intersection = words_new.intersection(words_ex)
            similarity = len(intersection) / max(len(words_new), 1)
            
            # 逻辑互斥检测
            conflict_reason = None
            for p1, p2 in mutually_exclusive:
                if (p1 in new_text and p2 in ex_text) or (p2 in new_text and p1 in ex_text):
                    conflict_reason = f"逻辑矛盾预警：检测到互斥特性『{p1}』与『{p2}』同时出现在当前需求与 #{ex.iid} 中。"
                    break

            if similarity > 0.4 or conflict_reason:
                conflicts.append({
                    "iid": ex.iid,
                    "title": ex.title,
                    "similarity": round(similarity * 100, 1),
                    "reason": conflict_reason or f"内容重叠度较高 ({round(similarity*100)}%)，请确认为非重复定义。"
                })

        conflicts.sort(key=lambda x: x['similarity'], reverse=True)
        return {"conflicts": conflicts[:3]}
    except Exception as e:
        logger.error(f"Conflict Sentry Error: {e}")
        return {"conflicts": []}


@app.get("/projects/{project_id}/test-cases/deduplication-report")
async def deduplicate_test_cases(project_id: int):
    """黑科技：扫描并识别冗余测试用例。"""
    try:
        # 1. 获取全量用例
        cases = await list_test_cases(project_id)
        if len(cases) < 2:
            return {"groups": [], "estimated_saving": "0%"}

        redundant_groups = []
        processed_iids = set()

        def get_features(case):
            # 提取特征文本：标题 + 步骤描述
            steps_text = " ".join([s.action for s in case.steps])
            return set(re.findall(r'\w+', (case.title + " " + steps_text).lower()))

        case_features = {c.iid: get_features(c) for c in cases}

        for i in range(len(cases)):
            c1 = cases[i]
            if c1.iid in processed_iids:
                continue

            current_group = []
            f1 = case_features[c1.iid]

            for j in range(i + 1, len(cases)):
                c2 = cases[j]
                if c2.iid in processed_iids:
                    continue

                f2 = case_features[c2.iid]
                # 计算 Jaccard 相似度
                intersection = len(f1.intersection(f2))
                union = len(f1.union(f2))
                similarity = intersection / union if union > 0 else 0

                if similarity > 0.7:  # 相似度阈值
                    if not current_group:
                        current_group.append({"iid": c1.iid, "title": c1.title})
                    current_group.append({"iid": c2.iid, "title": c2.title, "similarity": round(similarity * 100)})
                    processed_iids.add(c2.iid)

            if current_group:
                redundant_groups.append(current_group)
                processed_iids.add(c1.iid)

        # 估算节省工作量 (简单公式：冗余用例数 / 总数)
        redundant_count = sum(len(g) - 1 for g in redundant_groups)
        saving = round((redundant_count / len(cases)) * 100) if cases else 0

        return {
            "groups": redundant_groups,
            "estimated_saving": f"{saving}%",
            "total_scanned": len(cases)
        }
    except Exception as e:
        logger.error(f"Deduplication scan failed: {e}")
        return {"groups": [], "estimated_saving": "0%"}


@app.get("/projects/{project_id}/requirements", response_model=List[RequirementSummary])
async def list_requirements(project_id: int):
    """获取项目中的所有需求（基于 GitHub Issue 的 type::requirement 标签模拟）。

    Args:
        project_id: GitLab 项目 ID。

    Returns:
        List[RequirementSummary]: 需求列表。
    """
    url = f"{Config.GITLAB_URL}/api/v4/projects/{project_id}/issues"
    params = {
        "labels": "type::requirement",
        "state": "all",
        "per_page": 100
    }
    headers = {"PRIVATE-TOKEN": Config.GITLAB_PRIVATE_TOKEN}

    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        issues = response.json()

        reqs = []
        for issue in issues:
            labels = issue.get('labels', [])
            review_state = "draft"
            for label in labels:
                if label.startswith("review-state::"):
                    review_state = label.split("::")[1]
                    break
            
            reqs.append(RequirementSummary(
                iid=issue['iid'],
                title=issue['title'],
                state=issue['state'],
                review_state=review_state
            ))
        return reqs
    except Exception as e:
        logger.error(f"Failed to fetch requirements: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/projects/{project_id}/requirements/{iid}", response_model=RequirementDetail)
async def get_requirement_detail(project_id: int, iid: int):
    """获取单个需求的详情及其关联的测试用例。

    Args:
        project_id: 项目 ID。
        iid: 需求 IID。

    Returns:
        RequirementDetail: 需求详情。
    """
    headers = {"PRIVATE-TOKEN": Config.GITLAB_PRIVATE_TOKEN}
    
    try:
        # 获取需求议题
        req_url = f"{Config.GITLAB_URL}/api/v4/projects/{project_id}/issues/{iid}"
        req_resp = requests.get(req_url, headers=headers)
        req_resp.raise_for_status()
        req_data = req_resp.json()
        
        # 提取评审状态
        labels = req_data.get('labels', [])
        review_state = "draft"
        for label in labels:
            if label.startswith("review-state::"):
                review_state = label.split("::")[1]
                break

        # 获取关联该需求的测试用例
        # 在模拟方案中，我们通过搜索描述中包含 "关联需求]: # IID" 的议题来实现关联
        search_url = f"{Config.GITLAB_URL}/api/v4/projects/{project_id}/issues"
        search_params = {
            "labels": "type::test",
            "search": f"关联需求]: # {iid}"
        }
        test_resp = requests.get(search_url, params=search_params, headers=headers)
        test_resp.raise_for_status()
        test_issues = test_resp.json()

        test_cases = [parse_markdown_to_test_case(issue) for issue in test_issues]

        return RequirementDetail(
            id=req_data['id'],
            iid=req_data['iid'],
            title=req_data['title'],
            description=req_data.get('description'),
            state=req_data['state'],
            review_state=review_state,
            test_cases=test_cases
        )
    except Exception as e:
        logger.error(f"Failed to fetch requirement detail: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/projects/{project_id}/requirements", response_model=RequirementSummary)
async def create_requirement(project_id: int, data: RequirementCreate):
    """创建新的需求（在 GitLab 中创建带有 type::requirement 标签的议题）。

    Args:
        project_id: 项目 ID。
        data: 需求数据。
    """
    url = f"{Config.GITLAB_URL}/api/v4/projects/{project_id}/issues"
    headers = {"PRIVATE-TOKEN": Config.GITLAB_PRIVATE_TOKEN}
    payload = {
        "title": data.title,
        "description": data.description or "业务需求描述",
        "labels": "type::requirement,review-state::draft"
    }

    try:
        resp = requests.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        res = resp.json()
        return RequirementSummary(iid=res['iid'], title=res['title'], state=res['state'], review_state="draft")
    except Exception as e:
        logger.error(f"Failed to create requirement: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/projects/{project_id}/requirements/{iid}/review")
async def update_requirement_review_state(
    project_id: int, 
    iid: int, 
    review_state: str, 
    current_user = Depends(get_current_user)
):
    """更新需求的评审状态（自动穿透 Service Desk 用户身份）。
    
    Args:
        project_id: 项目 ID。
        iid: 需求 IID。
        review_state: 目标状态 (draft, under-review, approved, rejected)。
        current_user: 当前认证用户。
    """
    if review_state not in ["draft", "under-review", "approved", "rejected"]:
        raise HTTPException(status_code=400, detail="Invalid review state")

    # 动态获取当前操作者的 GitLab ID
    user_id = current_user.global_user_id
    
    # 获取邮箱以做审计日志
    operator_email = current_user.primary_email

    # 权限校验：Approve 和 Reject 需要 Maintainer (40+) 权限
    if review_state in ["approved", "rejected"]:
        access_level = await get_user_project_access_level(project_id, user_id)
        if access_level < 40:
            raise HTTPException(
                status_code=403, 
                detail=f"Permission Denied: Need Maintainer role (Level 40), but your level is {access_level}"
            )

    url = f"{Config.GITLAB_URL}/api/v4/projects/{project_id}/issues/{iid}"
    headers = {"PRIVATE-TOKEN": Config.GITLAB_PRIVATE_TOKEN}

    try:
        # 获取当前标签，移除旧的评审状态标签
        get_resp = requests.get(url, headers=headers)
        get_resp.raise_for_status()
        issue_data = get_resp.json()
        current_labels = issue_data.get('labels', [])

        new_labels = [l for l in current_labels if not l.startswith("review-state::")]
        new_labels.append(f"review-state::{review_state}")

        # 更新标签
        payload = {"labels": ",".join(new_labels)}
        put_resp = requests.put(url, json=payload, headers=headers)
        put_resp.raise_for_status()

        # 添加审计评论
        comment_url = f"{url}/notes"
        comment_body = (
            f"💠 **需求评审状态变更**\n"
            f"- **目标状态**: {review_state.upper()}\n"
            f"- **操作者**: {operator_email} (GitLab ID: {user_id})\n"
            f"- **权限等级**: {'Maintainer+' if review_state in ['approved', 'rejected'] else 'User'}\n"
            f"- **时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"- **结果**: { '✅ 已准入' if review_state == 'approved' else ('❌ 已驳回' if review_state == 'rejected' else '📝 流转中') }"
        )
        requests.post(comment_url, json={"body": comment_body}, headers=headers)

        # --- P2改造：通知需求提出者 ---
        req_author = await get_requirement_author(project_id, iid)
        if req_author and req_author != str(current_user.global_user_id):
            state_emoji = {"approved": "✅", "rejected": "❌", "under-review": "🔄", "draft": "📝"}.get(review_state, "📝")
            asyncio.create_task(push_notification(
                req_author,
                f"{state_emoji} 您的需求#{iid} 已被 {current_user.full_name} 评审为: {review_state}",
                "info" if review_state == "approved" else ("error" if review_state == "rejected" else "warning"),
                metadata={
                    "req_iid": iid,
                    "project_id": project_id,
                    "new_state": review_state,
                    "reviewer": current_user.full_name,
                    "reviewer_email": operator_email
                }
            ))
            logger.info(f"Sent review notification to requirement author {req_author}")

        return {"status": "success", "review_state": review_state, "reviewer_id": user_id}
    except Exception as e:
        logger.error(f"Failed to update review state for requirement #{iid}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/projects/{project_id}/requirements/stats", response_model=RequirementCoverage)
async def get_requirement_stats(project_id: int):
    """获取项目的需求复盖率与健康度统计。"""
    try:
        # 1. 获取所有需求
        reqs = await list_requirements(project_id)
        total_count = len(reqs)
        approved_reqs = [r for r in reqs if r.review_state == "approved"]
        approved_count = len(approved_reqs)

        if approved_count == 0:
            return RequirementCoverage(
                total_count=total_count,
                approved_count=0,
                covered_count=0,
                passed_count=0,
                coverage_rate=0.0,
                pass_rate=0.0,
                risk_requirements=[]
            )

        # 2. 并行获取每个 Approved 需求的详情（包含关联用例）
        import asyncio
        details = await asyncio.gather(*[get_requirement_detail(project_id, r.iid) for r in approved_reqs])
        
        covered_count = 0
        passed_count = 0
        risk_reqs = []

        for req in details:
            has_cases = len(req.test_cases) > 0
            if has_cases:
                covered_count += 1
                
                # 检查健康度：是否所有用例都 Passed
                all_passed = all(tc.result == "passed" for tc in req.test_cases)
                any_failed = any(tc.result == "failed" for tc in req.test_cases)
                
                if all_passed:
                    passed_count += 1
                
                if any_failed:
                    risk_reqs.append(RequirementSummary(iid=req.iid, title=req.title, state=req.state, review_state=req.review_state))
            else:
                # 审核通过但无用例，视为高风险（漏测风险）
                risk_reqs.append(RequirementSummary(iid=req.iid, title=req.title, state=req.state, review_state=req.review_state))

        return RequirementCoverage(
            total_count=total_count,
            approved_count=approved_count,
            covered_count=covered_count,
            passed_count=passed_count,
            coverage_rate=round((covered_count / approved_count) * 100, 2),
            pass_rate=round((passed_count / approved_count) * 100, 2) if covered_count > 0 else 0.0,
            risk_requirements=risk_reqs
        )
    except Exception as e:
        logger.error(f"Failed to calculate requirement stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/global/alerts")
async def get_global_alerts():
    """获取全网质量同步预警（黑科技：跨地域实时感知）。"""
    return GLOBAL_QUALITY_ALERTS


# --- Service Desk (业务方自助服务台) ---

@app.post("/service-desk/submit-bug")
async def submit_bug_via_service_desk(
    project_id: int, 
    data: ServiceDeskBugSubmit, 
    current_user = Depends(get_current_user)
):
    """业务方通过 Service Desk 提交缺陷。
    
    Args:
        project_id: GitLab 项目 ID。
        data: Bug 提交数据。
        current_user: 当前认证用户。
    """
    try:
        # 获取操作者 GitLab ID
        user_id = str(current_user.global_user_id)
        # 覆盖提交人信息为当前登录用户
        data.requester_name = current_user.full_name
        data.requester_email = current_user.primary_email
        # 参数验证
        valid_severities = ["S0", "S1", "S2", "S3"]
        valid_environments = ["production", "staging", "test", "development"]
        
        if data.severity not in valid_severities:
            raise HTTPException(
                status_code=400, 
                detail=f"无效的严重程度：{data.severity}。有效值：{', '.join(valid_severities)}"
            )
        
        if data.environment not in valid_environments:
            raise HTTPException(
                status_code=400,
                detail=f"无效的环境：{data.environment}。有效值：{', '.join(valid_environments)}"
            )
        
        tracking_code = f"BUG-{datetime.now().strftime('%Y%m%d')}-{len(SERVICE_DESK_TICKETS) + 1:03d}"
        
        description = f"""## 🐛 业务方缺陷报告 (Service Desk)

**报告人**: {data.requester_name} ({data.requester_email})  
**操作者 GitLab ID**: {user_id}
**追踪码**: {tracking_code}

### 缺陷信息
- **严重程度**: {data.severity}
- **优先级**: {data.priority}
- **省份/地域**: {data.province}
- **环境**: {data.environment}

### 复现步骤
{data.steps_to_repro}

### 实际结果
{data.actual_result}

### 期望结果
{data.expected_result}

### 附件
{chr(10).join([f'- {att}' for att in data.attachments]) if data.attachments else '无'}

---
*此缺陷由业务方通过 Service Desk 提交，请及时处理并回复。*
"""
        
        url = f"{Config.GITLAB_URL}/api/v4/projects/{project_id}/issues"
        headers = {"PRIVATE-TOKEN": Config.GITLAB_PRIVATE_TOKEN}
        
        payload = {
            "title": f"[Service Desk] {data.title}",
            "description": description,
            "labels": f"type::bug,severity::{data.severity},priority::{data.priority},province::{data.province},origin::service-desk"
        }
        
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        issue_data = response.json()
        
        ticket = {
            "tracking_code": tracking_code,
            "ticket_type": "bug",
            "status": "pending",
            "gitlab_issue_iid": issue_data.get("iid"),
            "gitlab_issue_url": issue_data.get("web_url"),
            "requester_name": data.requester_name,
            "requester_email": data.requester_email,
            "title": data.title,
            "project_id": project_id,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        SERVICE_DESK_TICKETS[tracking_code] = ticket
        save_service_desk_tickets()  # 持久化保存
        
        logger.info(f"Service Desk Bug created: {tracking_code} -> Issue #{issue_data.get('iid')}")
        
        return {
            "status": "success",
            "tracking_code": tracking_code,
            "gitlab_issue_iid": issue_data.get("iid"),
            "gitlab_issue_url": issue_data.get("web_url"),
            "message": f"缺陷已提交成功！追踪码: {tracking_code}，我们会尽快处理并通过邮件通知您。"
        }
        
    except Exception as e:
        logger.error(f"Service Desk Bug submission failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/service-desk/submit-requirement")
async def submit_requirement_via_service_desk(
    project_id: int, 
    data: ServiceDeskRequirementSubmit, 
    current_user = Depends(get_current_user)
):
    """业务方通过 Service Desk 提交需求。
    
    Args:
        project_id: GitLab 项目 ID。
        data: 需求提交数据。
        current_user: 当前认证用户。
    """
    try:
        # 获取操作者 GitLab ID
        user_id = str(current_user.global_user_id)
        # 覆盖提交人信息为当前登录用户
        data.requester_name = current_user.full_name
        data.requester_email = current_user.primary_email
        # 参数验证
        valid_req_types = ["feature", "enhancement", "bugfix"]
        
        if data.req_type not in valid_req_types:
            raise HTTPException(
                status_code=400,
                detail=f"无效的需求类型：{data.req_type}。有效值：{', '.join(valid_req_types)}"
            )
        
        tracking_code = f"REQ-{datetime.now().strftime('%Y%m%d')}-{len(SERVICE_DESK_TICKETS) + 1:03d}"
        
        description = f"""## 📋 业务方需求提交 (Service Desk)

**提交人**: {data.requester_name} ({data.requester_email})  
**操作者 GitLab ID**: {user_id}
**追踪码**: {tracking_code}

### 需求信息
- **需求类型**: {data.req_type}
- **优先级**: {data.priority}
- **省份/地域**: {data.province}
- **期望交付时间**: {data.expected_delivery or '未指定'}

### 需求描述
{data.description}

---
*此需求由业务方通过 Service Desk 提交，请评审后进入开发流程。*
"""
        
        url = f"{Config.GITLAB_URL}/api/v4/projects/{project_id}/issues"
        headers = {"PRIVATE-TOKEN": Config.GITLAB_PRIVATE_TOKEN}
        
        payload = {
            "title": f"[Service Desk] {data.title}",
            "description": description,
            "labels": f"type::requirement,req-type::{data.req_type},priority::{data.priority},province::{data.province},origin::service-desk,review-state::draft"
        }
        
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        issue_data = response.json()
        
        ticket = {
            "tracking_code": tracking_code,
            "ticket_type": "requirement",
            "status": "pending",
            "gitlab_issue_iid": issue_data.get("iid"),
            "gitlab_issue_url": issue_data.get("web_url"),
            "requester_name": data.requester_name,
            "requester_email": data.requester_email,
            "title": data.title,
            "project_id": project_id,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        SERVICE_DESK_TICKETS[tracking_code] = ticket
        save_service_desk_tickets()  # 持久化保存
        
        logger.info(f"Service Desk Requirement created: {tracking_code} -> Issue #{issue_data.get('iid')}")
        
        return {
            "status": "success",
            "tracking_code": tracking_code,
            "gitlab_issue_iid": issue_data.get("iid"),
            "gitlab_issue_url": issue_data.get("web_url"),
            "message": f"需求已提交成功！追踪码: {tracking_code}，我们会进行评审并通过邮件通知您。"
        }
        
    except Exception as e:
        logger.error(f"Service Desk Requirement submission failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/service-desk/track/{tracking_code}")
async def track_service_desk_ticket(tracking_code: str):
    """通过追踪码查询工单状态（无需登录）。"""
    if tracking_code not in SERVICE_DESK_TICKETS:
        raise HTTPException(status_code=404, detail="工单不存在，请检查追踪码是否正确")
    
    ticket = SERVICE_DESK_TICKETS[tracking_code]
    
    # 从 GitLab 获取最新状态
    if ticket.get("gitlab_issue_iid") and ticket.get("project_id"):
        try:
            issue_url = f"{Config.GITLAB_URL}/api/v4/projects/{ticket['project_id']}/issues/{ticket['gitlab_issue_iid']}"
            headers = {"PRIVATE-TOKEN": Config.GITLAB_PRIVATE_TOKEN}
            response = requests.get(issue_url, headers=headers)
            
            if response.status_code == 200:
                issue = response.json()
                if issue.get("state") == "closed":
                    ticket["status"] = "completed"
                elif "in-progress" in issue.get("labels", []):
                    ticket["status"] = "in-progress"
                
                ticket["updated_at"] = issue.get("updated_at", ticket["updated_at"])
        except Exception as e:
            logger.warning(f"Failed to sync ticket status from GitLab: {e}")
    
    return schemas.ServiceDeskTicket(**ticket)


@app.get("/service-desk/tickets")
async def list_service_desk_tickets(email: Optional[str] = None):
    """获取 Service Desk 工单列表。"""
    tickets = list(SERVICE_DESK_TICKETS.values())
    
    if email:
        tickets = [t for t in tickets if t.get("requester_email") == email]
    
    tickets.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    return tickets


@app.patch("/service-desk/tickets/{tracking_code}/status")
async def update_service_desk_ticket_status(
    tracking_code: str, 
    new_status: str,
    comment: Optional[str] = None
):
    """更新 Service Desk 工单状态，并双向同步到 GitLab Issue。
    
    Args:
        tracking_code: 工单追踪码。
        new_status: 新状态（pending, in-progress, completed, rejected）。
        comment: 可选的状态变更备注。
    
    Returns:
        dict: 更新结果，包含同步状态。
    
    Raises:
        HTTPException: 工单不存在或状态无效时抛出。
    """
    if tracking_code not in SERVICE_DESK_TICKETS:
        raise HTTPException(status_code=404, detail="工单不存在，请检查追踪码是否正确")
    
    valid_statuses = ["pending", "in-progress", "completed", "rejected"]
    if new_status not in valid_statuses:
        raise HTTPException(
            status_code=400, 
            detail=f"无效的状态：{new_status}。有效值：{', '.join(valid_statuses)}"
        )
    
    ticket = SERVICE_DESK_TICKETS[tracking_code]
    old_status = ticket["status"]
    
    # 如果状态没有变化，直接返回
    if old_status == new_status:
        return {
            "status": "success",
            "tracking_code": tracking_code,
            "message": "状态未变化",
            "current_status": new_status
        }
    
    # 更新本地状态
    ticket["status"] = new_status
    ticket["updated_at"] = datetime.now().isoformat()
    
    # 同步到 GitLab
    gitlab_sync_success = False
    gitlab_sync_message = ""
    
    if ticket.get("gitlab_issue_iid") and ticket.get("project_id"):
        try:
            issue_url = f"{Config.GITLAB_URL}/api/v4/projects/{ticket['project_id']}/issues/{ticket['gitlab_issue_iid']}"
            headers = {"PRIVATE-TOKEN": Config.GITLAB_PRIVATE_TOKEN}
            
            # 获取当前 Issue 信息
            get_response = requests.get(issue_url, headers=headers)
            get_response.raise_for_status()
            current_issue = get_response.json()
            current_labels = current_issue.get("labels", [])
            
            # 构建更新载荷
            update_payload = {}
            
            # 根据状态更新 GitLab
            if new_status == "completed":
                # 关闭 Issue
                update_payload["state_event"] = "close"
                gitlab_sync_message = "已关闭 GitLab Issue"
                
            elif new_status == "rejected":
                # 关闭 Issue 并添加 rejected 标签
                update_payload["state_event"] = "close"
                if "status::rejected" not in current_labels:
                    current_labels.append("status::rejected")
                    update_payload["labels"] = ",".join(current_labels)
                gitlab_sync_message = "已关闭 GitLab Issue 并标记为已拒绝"
                
            elif new_status == "in-progress":
                # 添加 in-progress 标签
                if "in-progress" not in current_labels:
                    current_labels.append("in-progress")
                    update_payload["labels"] = ",".join(current_labels)
                # 如果 Issue 是关闭的，重新打开
                if current_issue.get("state") == "closed":
                    update_payload["state_event"] = "reopen"
                gitlab_sync_message = "已添加处理中标签"
                
            elif new_status == "pending":
                # 移除 in-progress 标签
                if "in-progress" in current_labels:
                    current_labels.remove("in-progress")
                    update_payload["labels"] = ",".join(current_labels)
                # 如果 Issue 是关闭的，重新打开
                if current_issue.get("state") == "closed":
                    update_payload["state_event"] = "reopen"
                gitlab_sync_message = "已移除处理中标签"
            
            # 添加状态变更评论
            if comment:
                comment_text = f"**状态变更**: {old_status} → {new_status}\n\n{comment}"
            else:
                comment_text = f"**状态变更**: {old_status} → {new_status}\n\n*此变更由 Service Desk 系统自动同步。*"
            
            comment_url = f"{issue_url}/notes"
            comment_payload = {"body": comment_text}
            requests.post(comment_url, json=comment_payload, headers=headers)
            
            # 执行 Issue 更新
            if update_payload:
                response = requests.put(issue_url, json=update_payload, headers=headers)
                response.raise_for_status()
            
            gitlab_sync_success = True
            logger.info(f"✅ Service Desk → GitLab Sync: {tracking_code} status updated: {old_status} → {new_status}")
        
        except Exception as e:
            logger.error(f"❌ Failed to sync status to GitLab for {tracking_code}: {e}")
            gitlab_sync_message = f"GitLab 同步失败: {str(e)}"
            # 不抛出异常，允许本地状态更新成功
    else:
        gitlab_sync_message = "未关联 GitLab Issue，仅更新本地状态"
    
    # 持久化保存
    save_service_desk_tickets()
    
    # 推送实时通知到前端通知中心 (SSE)
    # 获取关联用户的 UUID 字符串
    user_email = ticket.get("requester_email")
    # 这里我们通过 email 查找 NOTIFICATION_QUEUES 中的对应连接
    # 为了简化，我们直接向所有该 email 订阅的连接推送
    # 在实际 MDM 中，我们会通过 email 关联到 global_user_id
    from devops_collector.auth import services as auth_services
    db = SessionLocal()
    target_user = auth_services.get_user_by_email(db, user_email)
    if target_user:
        target_uid = str(target_user.global_user_id)
        asyncio.create_task(push_notification(
            target_uid, 
            f"您的工单 [{tracking_code}] 状态已更新为: {new_status}", 
            "info" if new_status != 'rejected' else 'error'
        ))
    db.close()

    return {
        "status": "success",
        "tracking_code": tracking_code,
        "old_status": old_status,
        "new_status": new_status,
        "gitlab_synced": gitlab_sync_success,
        "gitlab_message": gitlab_sync_message,
        "message": f"工单状态已从 {old_status} 更新为 {new_status}"
    }



# ==================== Service Desk Auth Endpoints (Deprecated / Replaced) ====================
# The following endpoints are replaced by the standard /auth endpoints in devops_collector.auth.router
# We keep the /service-desk/my-tickets endpoint but update it to use the new authentication.

@app.get("/service-desk/my-tickets")
async def get_my_tickets(current_user = Depends(get_current_user)):
    """获取当前用户的工单列表（需要登录）
    
    Args:
        current_user: 当前认证用户
    
    Returns:
        dict: 包含用户信息和工单列表
    """
    email = current_user.primary_email
    
    # 获取该邮箱的所有工单
    my_tickets = [
        ticket for ticket in SERVICE_DESK_TICKETS.values()
        if ticket.get("requester_email") == email
    ]
    
    # 按创建时间倒序
    my_tickets.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    # 统计各状态工单数
    stats = {
        "total": len(my_tickets),
        "pending": len([t for t in my_tickets if t.get("status") == "pending"]),
        "in_progress": len([t for t in my_tickets if t.get("status") == "in-progress"]),
        "completed": len([t for t in my_tickets if t.get("status") == "completed"]),
        "rejected": len([t for t in my_tickets if t.get("status") == "rejected"])
    }
    
    return {
        "status": "success",
        "email": email,
        "stats": stats,
        "tickets": my_tickets
    }






if __name__ == "__main__":
    # 启动时加载 Service Desk 数据
    load_service_desk_tickets()
    # load_service_desk_users() # Removed legacy auth
    uvicorn.run(app, host="0.0.0.0", port=8000)
