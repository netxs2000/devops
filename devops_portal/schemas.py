from pydantic import BaseModel, Field, ConfigDict
, Any
from typing import List, Optional, Dict
from datetime import datetime

class TestStep(BaseModel):
    """结构化测试步骤模型"""
    step_number: int
    action: str
    expected_result: str

class TestCase(BaseModel):
    """测试用例核心模型"""
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(validation_alias="global_issue_id")
    iid: int = Field(validation_alias="gitlab_issue_iid")
    title: str
    priority: Optional[str] = "P2"
    test_type: Optional[str] = Field(default="Functional", validation_alias="issue_type")
    requirement_id: Optional[str] = None
    pre_conditions: List[str] = []
    steps: List[TestStep] = []
    result: str = "pending"
    web_url: Optional[str] = None
    linked_bugs: List[Dict[str, str]] = []

class ExecutionRecord(BaseModel):
    """测试执行审计记录"""
    issue_iid: int
    result: str
    executed_at: datetime
    executor: str
    executor_uid: Optional[str] = None # MDM global_user_id
    comment: Optional[str] = None
    pipeline_id: Optional[int] = None
    environment: Optional[str] = None

class TestCaseCreate(BaseModel):
    """创建新测试用例的请求载荷"""
    title: str
    priority: str
    test_type: str
    pre_conditions: str
    steps: List[Dict[str, str]]
    requirement_iid: Optional[int] = None

class RequirementSummary(BaseModel):
    """需求简要信息"""
    iid: int
    title: str
    state: str
    review_state: str = "draft"

class RequirementDetail(BaseModel):
    """需求详细信息"""
    id: int
    iid: int
    title: str
    description: Optional[str]
    state: str
    review_state: str = "draft"
    test_cases: List[TestCase] = []

class RequirementCoverage(BaseModel):
    """需求复盖率与健康度分析模型"""
    total_count: int
    approved_count: int
    covered_count: int
    passed_count: int = 0
    coverage_rate: float = 0.0
    pass_rate: float = 0.0
    risk_requirements: List[RequirementSummary] = []

class ProvinceQuality(BaseModel):
    """省份质量分布模型"""
    province: str
    bug_count: int
    pass_rate: float = 100.0

class QualityGateStatus(BaseModel):
    """质量门禁合规性状态模型"""
    is_passed: bool
    requirements_covered: bool
    p0_bugs_cleared: bool
    pipeline_stable: bool
    regional_risk_free: bool
    summary: str

class AssetTestCase(BaseModel):
    """基线库资产用例模型"""
    iid: int
    title: str
    priority: str
    test_type: str
    steps_count: int
    project_id: int

class ProvinceBenchmarking(BaseModel):
    """地域质量对标模型"""
    province: str
    bug_count: int
    resolved_count: int
    unresolved_count: int
    resolution_rate: float
    risk_score: float
    passed_count: int = 0
    coverage_rate: float = 0.0
    pass_rate: float = 0.0
    risk_requirements: List[RequirementSummary] = []

class ExecutionReport(BaseModel):
    """执行结果上报模型"""
    result: Optional[str] = None
    executor: str = "TestHub System"
    comment: Optional[str] = None
    environment: Optional[str] = "Default"

class ServiceDeskBugSubmit(BaseModel):
    """Service Desk 缺陷提交模型"""
    requester_name: Optional[str] = None
    requester_email: Optional[str] = None
    title: str
    severity: str
    priority: str = "P2"
    province: str = "nationwide"
    environment: str
    steps_to_repro: str
    actual_result: str
    expected_result: str
    attachments: Optional[List[str]] = []

class ServiceDeskRequirementSubmit(BaseModel):
    """Service Desk 需求提交模型"""
    requester_name: Optional[str] = None
    requester_email: Optional[str] = None
    title: str
    description: str
    priority: str = "P2"
    req_type: str = "feature"
    province: str = "nationwide"
    expected_delivery: Optional[str] = None
    attachments: Optional[List[str]] = []

class ServiceDeskTicket(BaseModel):
    """Service Desk 工单模型"""
    tracking_code: str
    ticket_type: str
    status: str
    gitlab_issue_iid: Optional[int]
    requester_email: str
    created_at: str
    updated_at: str

class BugCreate(BaseModel):
    """缺陷创建模型"""
    title: str
    severity: str
    priority: str = "P2"
    category: str
    source: str
    province: str
    environment: str
    steps_to_repro: str
    actual_result: str
    expected_result: str
    linked_case_iid: int
    linked_req_iid: Optional[int] = None

class RequirementCreate(BaseModel):
    """需求创建模型"""
    title: str
    description: str = ""
    priority: str = "P2"
    req_type: str = "feature"
    province: str = "nationwide"

class BugDetail(BaseModel):
    """缺陷详情模型"""
    iid: int
    title: str
    state: str
    created_at: datetime
    author: str
    web_url: str
    labels: List[str]

class MRSummary(BaseModel):
    """MR 评审统计模型"""
    total: int
    merged: int
    opened: int
    closed: int
    approved: int
    rework_needed: int
    rejected: int
    avg_discussions: float
    avg_merge_time_hours: float

class JenkinsJobSummary(BaseModel):
    """Jenkins 任务摘要"""
    id: int
    name: str
    full_name: str
    url: Optional[str]
    description: Optional[str]
    color: Optional[str]
    gitlab_project_id: Optional[int]
    last_synced_at: Optional[datetime]
    sync_status: str

class JenkinsBuildSummary(BaseModel):
    """Jenkins 构建摘要"""
    number: int
    result: Optional[str]
    duration: Optional[int]
    timestamp: Optional[datetime]
    url: Optional[str]
    trigger_user: Optional[str]

class AIResponse(BaseModel):
    """统一的 AI 接口返回模型"""
    status: str = "success"
    data: Optional[Dict[str, Any]] = None
    message: Optional[str] = None

