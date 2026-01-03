"""DevOps Collector Models Package

聚合所有数据模型，支持向后兼容。

架构说明:
    - 第1层: base_models.py 定义公共基础模型 (Base, Organization, User, SyncLog)
    - 第2层: 各插件定义特定模型 (GitLab, SonarQube)
    - 第3层: 本文件统一导出所有模型
"""
from .base_models import Base, Organization, User, Role, Location, Calendar, SyncLog, RawDataStaging, IdentityMapping, Product, OKRObjective, OKRKeyResult, TraceabilityLink, TestExecutionSummary, PerformanceRecord, Incident, ResourceCost, UserActivityProfile, Service, ServiceProjectMapping, SLO, TimestampMixin, RawDataMixin, ProjectMaster, ContractPaymentNode, RevenueContract, PurchaseContract, UserCredential, UserOAuthToken, MetricDefinition, SystemRegistry, EntityTopology, Company, Vendor, EpicMaster, ComplianceIssue
from .dependency import DependencyScan, LicenseRiskRule, Dependency, DependencyCVE
from .test_management import TestCase, TestCaseIssueLink, Requirement, TestExecutionRecord

def _import_plugin_models():
    '''"""TODO: Add description.

Args:
    TODO

Returns:
    TODO

Raises:
    TODO
"""'''
    global Project, ProjectMember, Commit, CommitFileStats, Issue, MergeRequest, Pipeline, Deployment, Note, Tag, Branch, GitLabGroup, GitLabGroupMember, Milestone, GitLabIssueEvent, GitLabWikiLog, GitLabDependency, GitLabPackage, GitLabPackageFile
    global SonarProject, SonarMeasure, SonarIssue, JenkinsJob, JenkinsBuild, JiraProject, JiraBoard, JiraSprint, JiraIssue, JiraIssueHistory, NexusComponent, NexusAsset, JFrogArtifact, JFrogScan, JFrogVulnerabilityDetail, JFrogDependency, ZenTaoProduct, ZenTaoIssue, ZenTaoExecution
    from devops_collector.plugins.gitlab.models import Project, ProjectMember, Commit, CommitFileStats, Issue, MergeRequest, Pipeline, Deployment, Note, Tag, Branch, GitLabGroup, GitLabGroupMember, Milestone, GitLabIssueEvent, GitLabWikiLog, GitLabDependency, GitLabPackage, GitLabPackageFile
    from devops_collector.plugins.sonarqube.models import SonarProject, SonarMeasure, SonarIssue
    try:
        from devops_collector.plugins.jenkins.models import JenkinsJob, JenkinsBuild
    except ImportError:
        JenkinsJob = JenkinsBuild = None
    try:
        from devops_collector.plugins.jira.models import JiraProject, JiraBoard, JiraSprint, JiraIssue, JiraIssueHistory
    except ImportError:
        JiraProject = JiraBoard = JiraSprint = JiraIssue = JiraIssueHistory = None
    try:
        from devops_collector.plugins.nexus.models import NexusComponent, NexusAsset
    except ImportError:
        NexusComponent = NexusAsset = None
    try:
        from devops_collector.plugins.jfrog.models import JFrogArtifact, JFrogScan, JFrogVulnerabilityDetail, JFrogDependency
    except ImportError:
        JFrogArtifact = JFrogScan = JFrogVulnerabilityDetail = JFrogDependency = None
    try:
        from devops_collector.plugins.zentao.models import ZenTaoProduct, ZenTaoIssue, ZenTaoExecution
    except ImportError:
        ZenTaoProduct = ZenTaoIssue = ZenTaoExecution = None
from devops_collector.plugins.gitlab.models import Project, ProjectMember, Commit, CommitFileStats, Issue, MergeRequest, Pipeline, Deployment, Note, Tag, Branch, GitLabGroup, GitLabGroupMember, Milestone, GitLabIssueEvent, GitLabWikiLog, GitLabDependency, GitLabPackage, GitLabPackageFile
from devops_collector.plugins.sonarqube.models import SonarProject, SonarMeasure, SonarIssue
try:
    from devops_collector.plugins.jenkins.models import JenkinsJob, JenkinsBuild
except ImportError:
    JenkinsJob = JenkinsBuild = None
try:
    from devops_collector.plugins.jira.models import JiraProject, JiraBoard, JiraSprint, JiraIssue, JiraIssueHistory
except ImportError:
    JiraProject = JiraBoard = JiraSprint = JiraIssue = JiraIssueHistory = None
try:
    from devops_collector.plugins.nexus.models import NexusComponent, NexusAsset
except ImportError:
    NexusComponent = NexusAsset = None
try:
    from devops_collector.plugins.jfrog.models import JFrogArtifact, JFrogScan, JFrogVulnerabilityDetail, JFrogDependency
except ImportError:
    JFrogArtifact = JFrogScan = JFrogVulnerabilityDetail = JFrogDependency = None
try:
    from devops_collector.plugins.zentao.models import ZenTaoProduct, ZenTaoIssue, ZenTaoExecution
except ImportError:
    ZenTaoProduct = ZenTaoIssue = ZenTaoExecution = None
__all__ = ['Base', 'Organization', 'User', 'Role', 'Location', 'Calendar', 'SyncLog', 'RawDataStaging', 'IdentityMapping', 'Product', 'OKRObjective', 'OKRKeyResult', 'TraceabilityLink', 'TestExecutionSummary', 'PerformanceRecord', 'Incident', 'ResourceCost', 'UserActivityProfile', 'Service', 'ServiceProjectMapping', 'SLO', 'TimestampMixin', 'RawDataMixin', 'ProjectMaster', 'ContractPaymentNode', 'RevenueContract', 'PurchaseContract', 'UserCredential', 'UserOAuthToken', 'MetricDefinition', 'SystemRegistry', 'EntityTopology', 'Company', 'Vendor', 'EpicMaster', 'ComplianceIssue', 'Project', 'ProjectMember', 'Commit', 'CommitFileStats', 'Issue', 'MergeRequest', 'Pipeline', 'Deployment', 'Note', 'Tag', 'Branch', 'GitLabGroup', 'GitLabGroupMember', 'Milestone', 'GitLabIssueEvent', 'GitLabWikiLog', 'GitLabDependency', 'GitLabPackage', 'GitLabPackageFile', 'SonarProject', 'SonarMeasure', 'SonarIssue', 'JiraProject', 'JiraBoard', 'JiraSprint', 'JiraIssue', 'JiraIssueHistory', 'JenkinsJob', 'JenkinsBuild', 'JFrogArtifact', 'JFrogScan', 'JFrogVulnerabilityDetail', 'JFrogDependency', 'NexusComponent', 'NexusAsset', 'ZenTaoProduct', 'ZenTaoIssue', 'ZenTaoExecution', 'TestCase', 'TestCaseIssueLink', 'Requirement', 'DependencyScan', 'LicenseRiskRule', 'Dependency', 'DependencyCVE']
from . import events