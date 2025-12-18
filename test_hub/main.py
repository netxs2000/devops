"""GitLab Test Management Hub - Prototype.

This is a prototype for secondary development to simulate GitLab Ultimate Test Cases.
It parses Issue descriptions into structured Test Case data.
"""

import json
import re
import logging
import requests
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from devops_collector.config import Config

# Configure logging
logging.basicConfig(level=Config.LOG_LEVEL)
logger = logging.getLogger('TestHub')

app = FastAPI(title="GitLab Test Hub (Clone Ultimate)")

# Mount static files for the frontend
app.mount("/static", StaticFiles(directory="test_hub/static"), name="static")

@app.get("/")
async def serve_index():
    """Serve the main frontend page."""
    return FileResponse("test_hub/static/index.html")

class TestStep(BaseModel):
    """Structured test step matching Ultimate style."""
    step_number: int
    action: str
    expected_result: str

class TestCase(BaseModel):
    """Structured Test Case model."""
    id: int
    iid: int
    title: str
    priority: str
    test_type: str
    requirement_id: Optional[str]
    pre_conditions: List[str]
    steps: List[TestStep]
    result: str
    web_url: str

class MRSummary(BaseModel):
    """Summary of Merge Requests for review analytics."""
    total: int
    merged: int
    opened: int
    closed: int
    approved: int
    rework_needed: int
    rejected: int
    avg_discussions: float
    avg_merge_time_hours: float

def parse_markdown_to_test_case(issue: dict) -> TestCase:
    """Parses GitLab Issue Markdown description into a structured TestCase object.
    
    Args:
        issue: The raw issue dictionary from GitLab API.
        
    Returns:
        A structured TestCase object.
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
            
    return TestCase(
        id=issue['id'],
        iid=issue['iid'],
        title=issue['title'],
        priority=priority,
        test_type=test_type,
        requirement_id=req_id,
        pre_conditions=[p.strip() for p in pre_conditions],
        steps=steps,
        result=result,
        web_url=issue['web_url']
    )

@app.get("/projects/{project_id}/test-cases", response_model=List[TestCase])
async def list_test_cases(project_id: int):
    """Fetch and parse all test cases from a GitLab project."""
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
        
        test_cases = [parse_markdown_to_test_case(issue) for issue in issues]
        return test_cases
    except Exception as e:
        logger.error(f"Failed to fetch test cases: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/projects/{project_id}/test-summary")
async def get_test_summary(project_id: int):
    """Get count summary of test cases by result for charting."""
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
    """Fetch and calculate Merge Request review statistics."""
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
            # 1. Basic State
            stats[mr['state']] += 1
            
            # 2. Review Labels (Based on our new convention)
            labels = mr.get('labels', [])
            if "review-result::approved" in labels: stats["approved"] += 1
            if "review-result::rework" in labels: stats["rework_needed"] += 1
            if "review-result::rejected" in labels: stats["rejected"] += 1
            
            # 3. Discussion Count
            stats["total_discussions"] += mr.get('user_notes_count', 0)
            
            # 4. Merge Time Calculation
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

@app.post("/projects/{project_id}/test-cases/{issue_iid}/execute")
async def execute_test_case(project_id: int, issue_iid: int, result: str):
    """Execute a test case and update GitLab labels/state."""
    if result not in ["passed", "failed", "blocked"]:
        raise HTTPException(status_code=400, detail="Invalid result status")
        
    url = f"{Config.GITLAB_URL}/api/v4/projects/{project_id}/issues/{issue_iid}"
    headers = {"PRIVATE-TOKEN": Config.GITLAB_PRIVATE_TOKEN}
    
    # 1. First, get current labels to remove old test-result labels
    try:
        get_resp = requests.get(url, headers=headers)
        get_resp.raise_for_status()
        current_labels = get_resp.json().get('labels', [])
        
        # Filter out existing test-result labels
        new_labels = [l for l in current_labels if not l.startswith("test-result::")]
        new_labels.append(f"test-result::{result}")
        
        # 2. Update the issue
        payload = {
            "labels": ",".join(new_labels)
        }
        
        # If passed, we automatically close it as per our template logic
        if result == "passed":
            payload["state_event"] = "close"
        else:
            payload["state_event"] = "reopen" # Ensure it's open if failed/blocked
            
        put_resp = requests.put(url, json=payload, headers=headers)
        put_resp.raise_for_status()
        
        return {"status": "success", "new_result": result, "new_state": put_resp.json().get('state')}
        
    except Exception as e:
        logger.error(f"Failed to execute test case #{issue_iid}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/webhook")
async def gitlab_webhook(request: Request):
    """Handle incoming GitLab Webhooks for real-time sync."""
    try:
        payload = await request.json()
        event_type = request.headers.get("X-Gitlab-Event")
        
        if event_type == "Issue Hook":
            object_attr = payload.get("object_attributes", {})
            labels = [l.get("title") for l in payload.get("labels", [])]
            issue_iid = object_attr.get("iid")
            action = object_attr.get("action")
            
            # Logic: Only care about Test Cases
            if "type::test" in labels:
                logger.info(f"Webhook Received: Test Case #{issue_iid} was {action}")
                
                # Here you could implement:
                # 1. Real-time browser notification via WebSockets
                # 2. Update a local database cache
                # 3. Trigger secondary automation (e.g. notify QA group in DingTalk/WeCom)
                
                if action == "close" and "test-result::passed" in labels:
                    logger.info(f"Test Case #{issue_iid} passed and archived.")
            
        return {"status": "accepted"}
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    # In a real dev environment, you would run this via CLI
    uvicorn.run(app, host="0.0.0.0", port=8000)
