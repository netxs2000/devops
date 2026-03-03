"""TODO: Add module description."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TestStep(BaseModel):
    """结构化测试步骤模型"""

    __test__ = False
    step_number: int
    action: str
    expected_result: str


class TestCase(BaseModel):
    """测试用例核心模型"""

    __test__ = False
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
    id: int = Field(validation_alias="global_issue_id")
    iid: int = Field(validation_alias="gitlab_issue_iid")
    title: str
    priority: str | None = "P2"
    test_type: str | None = Field(default="Functional", validation_alias="issue_type")
    requirement_id: str | None = None
    pre_conditions: list[str] = []
    steps: list[TestStep] = []
    result: str = "pending"
    web_url: str | None = None
    linked_bugs: list[dict[str, str]] = []
    project_name: str | None = None  # 所属项目名称 (用于聚合视图)


class ExecutionRecord(BaseModel):
    """测试执行审计记录"""

    issue_iid: int
    result: str
    executed_at: datetime
    executor: str
    executor_uid: str | None = None
    comment: str | None = None
    pipeline_id: int | None = None
    environment: str | None = None


class TestCaseCreate(BaseModel):
    """创建新测试用例的请求载荷"""

    __test__ = False
    title: str
    priority: str
    test_type: str
    pre_conditions: str
    steps: list[dict[str, str]]
    requirement_iid: int | None = None
    product_id: str | None = None
    org_id: str | None = None


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
    description: str | None
    state: str
    review_state: str = "draft"
    test_cases: list[TestCase] = []


class RequirementCoverage(BaseModel):
    """需求复盖率与健康度分析模型"""

    total_count: int
    approved_count: int
    covered_count: int
    passed_count: int = 0
    coverage_rate: float = 0.0
    pass_rate: float = 0.0
    risk_requirements: list[RequirementSummary] = []


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

    __test__ = False
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
    risk_requirements: list[RequirementSummary] = []


class ExecutionReport(BaseModel):
    """执行结果上报模型"""

    result: str | None = None
    executor: str = "TestHub System"
    comment: str | None = None
    environment: str | None = "Default"


class ServiceDeskBugSubmit(BaseModel):
    """Service Desk 缺陷提交模型"""

    requester_name: str | None = None
    requester_email: str | None = None
    title: str
    severity: str
    priority: str = "P2"
    province: str = "nationwide"
    environment: str
    steps_to_repro: str
    actual_result: str
    expected_result: str
    bug_category: str | None = "code-error"
    attachments: list[str] | None = []


class ServiceDeskRequirementSubmit(BaseModel):
    """Service Desk 需求提交模型"""

    requester_name: str | None = None
    requester_email: str | None = None
    title: str
    description: str
    priority: str = "P2"
    req_type: str = "feature"
    province: str = "nationwide"
    expected_delivery: str | None = None
    attachments: list[str] | None = []


class ServiceDeskTicket(BaseModel):
    """Service Desk 工单模型"""

    tracking_code: str
    ticket_type: str
    status: str
    gitlab_issue_iid: int | None
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
    linked_req_iid: int | None = None


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
    labels: list[str]


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
    url: str | None
    description: str | None
    color: str | None
    gitlab_project_id: int | None
    last_synced_at: datetime | None
    sync_status: str


class JenkinsBuildSummary(BaseModel):
    """Jenkins 构建摘要"""

    number: int
    result: str | None
    duration: int | None
    timestamp: datetime | None
    url: str | None
    trigger_user: str | None


class AIResponse(BaseModel):
    """统一的 AI 接口返回模型"""

    status: str = "success"
    data: dict[str, Any] | None = None
    message: str | None = None


class IdentityMappingCreate(BaseModel):
    """创建外部身份映射的请求模型"""

    global_user_id: uuid.UUID
    source_system: str
    external_user_id: str
    external_username: str | None = None
    external_email: str | None = None


class IdentityMappingView(IdentityMappingCreate):
    """外部身份映射视图模型"""

    model_config = ConfigDict(from_attributes=True)
    id: int
    user_name: str | None = None
    hr_relationship: str | None = None
    mapping_status: str
    confidence_score: float
    last_active_at: datetime | None = None


class IdentityMappingUpdateStatus(BaseModel):
    """更新身份映射状态的请求模型"""

    mapping_status: str


class TeamMemberView(BaseModel):
    """虚拟团队成员视图"""

    model_config = ConfigDict(from_attributes=True)
    user_id: uuid.UUID
    full_name: str
    role_code: str
    allocation_ratio: float


class TeamView(BaseModel):
    """业务虚拟团队视图"""

    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    team_code: str
    description: str | None = None
    parent_id: int | None = None
    org_id: str | None = None
    leader_id: uuid.UUID | None = None
    leader_name: str | None = None
    members: list[TeamMemberView] = []


class TeamCreate(BaseModel):
    """创建虚拟团队的请求载荷"""

    name: str
    team_code: str
    description: str | None = None
    parent_id: int | None = None
    org_id: str | None = None
    leader_id: uuid.UUID | None = None


class TeamMemberCreate(BaseModel):
    """添加团队成员的请求载荷"""

    user_id: uuid.UUID
    role_code: str | None = "MEMBER"
    allocation_ratio: float | None = 1.0


class UserFullProfile(BaseModel):
    """用户全景画像模型"""

    global_user_id: uuid.UUID
    full_name: str
    username: str | None
    primary_email: str
    employee_id: str | None
    department_name: str | None
    is_active: bool
    hr_relationship: str | None = None
    identities: list[IdentityMappingView] = []
    teams: list[dict[str, Any]] = []


class ProductView(BaseModel):
    """产品视图模型"""

    model_config = ConfigDict(from_attributes=True)
    product_id: str
    product_name: str
    product_description: str
    category: str | None = None
    lifecycle_status: str
    matching_patterns: list[str] | None = Field(None, description="自动识别匹配模式列表")


class ProductCreate(BaseModel):
    """创建产品的请求模型"""

    product_id: str
    product_name: str
    product_description: str
    category: str | None = None
    owner_team_id: str | None = None
    product_manager_id: uuid.UUID | None = None
    version_schema: str = "semver"
    matching_patterns: list[str] | None = Field(None, description="自动识别匹配模式列表")


class ProjectProductRelationView(BaseModel):
    """项目与产品关联视图模型"""

    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: str
    product_id: str
    relation_type: str
    allocation_ratio: float
    product_name: str | None = None


class ProjectProductRelationCreate(BaseModel):
    """创建项目产品关联的请求模型"""

    project_id: str
    product_id: str
    relation_type: str = "PRIMARY"
    allocation_ratio: float = 1.0


class OrganizationCreate(BaseModel):
    """创建组织的请求模型"""

    org_id: str
    org_name: str
    org_level: int | None = 1
    parent_org_id: str | None = None
    manager_user_id: uuid.UUID | None = None
    is_active: bool | None = True
    cost_center: str | None = None


class OrganizationView(OrganizationCreate):
    """组织视图模型"""

    model_config = ConfigDict(from_attributes=True)
    id: int
    manager_name: str | None = None
    parent_name: str | None = None


class ImportSummary(BaseModel):
    """导入结果汇总模型"""

    total_processed: int
    success_count: int
    failure_count: int
    errors: list[dict[str, Any]] = []


class TraceabilityMatrixItem(BaseModel):
    """追溯矩阵行数据模型"""

    requirement: RequirementSummary
    test_cases: list[TestCase] = []
    defects: list[BugDetail] = []
    merge_requests: list[dict[str, Any]] = []
    commits: list[dict[str, Any]] = []


class JFrogArtifactSummary(BaseModel):
    """JFrog 制品摘要"""

    model_config = ConfigDict(from_attributes=True)
    id: int = Field(..., description="数据库唯一 ID")
    repo: str = Field(..., description="仓库名称")
    path: str = Field(..., description="制品路径")
    name: str = Field(..., description="制品文件名")
    version: str | None = Field(None, description="版本号")
    package_type: str | None = Field(None, description="包类型 (Maven/Docker/etc)")
    size_bytes: int | None = Field(None, description="文件大小 (Bytes)")
    created_at: datetime | None = Field(None, description="创建时间")


class NexusComponentSummary(BaseModel):
    """Nexus 组件摘要"""

    model_config = ConfigDict(from_attributes=True)
    id: str = Field(..., description="Nexus 内部组件 ID")
    repository: str = Field(..., description="仓库名称")
    format: str | None = Field(None, description="格式 (maven2/npm/docker)")
    group: str | None = Field(None, description="组织/分组 (GroupID)")
    name: str = Field(..., description="组件名称")
    version: str | None = Field(None, description="版本号")
    product_id: str | None = Field(None, description="绑定的 MDM 产品代码")


class DependencyScanResult(BaseModel):
    """依赖扫描结果返回"""

    scan_id: int
    project_id: int
    status: str
    summary: dict[str, int]


class DependencyScanSummary(BaseModel):
    """依赖扫描摘要模型"""

    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int
    scan_date: datetime
    scanner_name: str
    scanner_version: str | None = None
    total_dependencies: int | None = 0
    vulnerable_dependencies: int | None = 0
    high_risk_licenses: int | None = 0
    scan_status: str
    ci_job_url: str | None = None
    project: dict[str, Any] | None = None
