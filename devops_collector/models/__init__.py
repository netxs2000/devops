"""DevOps Collector Models Package

聚合所有数据模型，支持向后兼容。

架构说明:
    - 第1层: base_models.py 定义公共基础模型 (Base, Organization, User, SyncLog)
    - 第2层: 各插件定义特定模型 (GitLab, SonarQube)
    - 第3层: 本文件统一导出所有模型
"""

# 从公共基础模型导入
from .base_models import (
    Base,
    Organization,
    User,
    Location,  # MDM地理位置主数据表
    SyncLog,
    RawDataStaging,
    IdentityMapping,
    Product,
    OKRObjective,
    OKRKeyResult,
    TraceabilityLink,
    TestExecutionSummary,
    PerformanceRecord,
    Incident,
    ResourceCost,
    UserActivityProfile,
    Service,
    ServiceProjectMapping,
    SLO,
    TimestampMixin,
    RawDataMixin
)
# 从依赖扫描模块导入
from .dependency import (
    DependencyScan,
    LicenseRiskRule,
    Dependency,
    DependencyCVE
)
# 从测试管理模块导入
from .test_management import (
    TestCase,
    TestCaseIssueLink,
    Requirement,
    TestExecutionRecord
)
# 从 GitLab 插件导入特定模型
from devops_collector.plugins.gitlab.models import (
    Project,
    ProjectMember,
    Commit,
    CommitFileStats,
    Issue,
    MergeRequest,
    Pipeline,
    Deployment,
    Note,
    Tag,
    Branch,
    GitLabGroup,
    GitLabGroupMember,
    Milestone,
    GitLabIssueEvent,
    GitLabWikiLog,
    GitLabDependency,
    GitLabPackage,
    GitLabPackageFile
)

# 从 SonarQube 插件导入模型
from devops_collector.plugins.sonarqube.models import (
    SonarProject,
    SonarMeasure,
    SonarIssue
)

# 从 Jenkins 插件导入模型
try:
    from devops_collector.plugins.jenkins.models import (
        JenkinsJob,
        JenkinsBuild
    )
except ImportError:
    # 允许插件暂不存在
    JenkinsJob = None
    JenkinsBuild = None
try:
    from devops_collector.plugins.jira.models import (
        JiraProject,
        JiraBoard,
        JiraSprint,
        JiraIssue,
        JiraIssueHistory
    )
except ImportError:
    JiraProject = None
    JiraBoard = None
    JiraSprint = None
    JiraIssue = None
    JiraIssueHistory = None
    ZenTaoExecution = None
try:
    from devops_collector.plugins.nexus.models import (
        NexusComponent,
        NexusAsset
    )
except ImportError:
    NexusComponent = None
    NexusAsset = None
try:
    from devops_collector.plugins.jfrog.models import (
        JFrogArtifact,
        JFrogScan,
        JFrogVulnerabilityDetail,
        JFrogDependency
    )
except ImportError:
    JFrogArtifact = None
    JFrogScan = None
    JFrogVulnerabilityDetail = None
    JFrogDependency = None
try:
    from devops_collector.plugins.zentao.models import (
        ZenTaoProduct,
        ZenTaoIssue,
        ZenTaoExecution
    )
except ImportError:
    ZenTaoProduct = None
    ZenTaoIssue = None
    ZenTaoExecution = None

__all__ = [
    # 公共基础模型
    'Base', 'Organization', 'User', 'Location', 'SyncLog', 'RawDataStaging', 'IdentityMapping', 'Product',
    'OKRObjective', 'OKRKeyResult', 'TraceabilityLink',
    'TestExecutionSummary', 'PerformanceRecord', 'Incident', 'ResourceCost',
    'UserActivityProfile',
    'Service', 'ServiceProjectMapping', 'SLO',
    'TimestampMixin', 'RawDataMixin',
    # GitLab 模型
    'Project', 'ProjectMember', 'Commit', 'CommitFileStats',
    'Issue', 'MergeRequest', 'Pipeline', 'Deployment',
    'Note', 'Tag', 'Branch', 'GitLabGroup', 'GitLabGroupMember', 'Milestone',
    'GitLabIssueEvent',
    'GitLabWikiLog',
    'GitLabDependency',
    'GitLabPackage', 'GitLabPackageFile',
    # SonarQube 模型
    'SonarProject', 'SonarMeasure', 'SonarIssue',
    # Jira 模型
    'JiraProject', 'JiraBoard', 'JiraSprint', 'JiraIssue', 'JiraIssueHistory',
    # Jenkins 模型
    'JenkinsJob', 'JenkinsBuild',
    # JFrog 模型
    'JFrogArtifact', 'JFrogScan', 'JFrogVulnerabilityDetail', 'JFrogDependency',
    # Nexus 模型
    'NexusComponent', 'NexusAsset',
    # ZenTao 模型
    'ZenTaoProduct', 'ZenTaoIssue', 'ZenTaoExecution',
    # 测试管理
    'TestCase', 'TestCaseIssueLink', 'Requirement',
    # 依赖扫描
    'DependencyScan', 'LicenseRiskRule', 'Dependency', 'DependencyCVE'
]
# 注册全局事件监听器 (黑科技 3)
from . import events
