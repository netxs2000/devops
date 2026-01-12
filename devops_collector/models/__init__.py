"""DevOps Collector Models Package

聚合核心数据模型。
插件模型应直接从插件包导入，或通过 plugin_loader 动态加载。

架构说明:
    - 第1层: base_models.py 定义公共基础模型
    - 第2层: 核心功能模块 (dependency, test_management)
"""
from .base_models import (
    Base, Organization, User, Role, Location, Calendar, SyncLog, RawDataStaging, 
    IdentityMapping, Product, OKRObjective, OKRKeyResult, TraceabilityLink, 
    TestExecutionSummary, PerformanceRecord, Incident, ResourceCost, UserActivityProfile, 
    Service, ServiceProjectMapping, SLO, TimestampMixin, RawDataMixin, ProjectMaster, 
    ContractPaymentNode, RevenueContract, PurchaseContract, UserCredential, UserOAuthToken, 
    MetricDefinition, SystemRegistry, EntityTopology, Company, Vendor, EpicMaster, 
    ComplianceIssue, CommitMetrics, DailyDevStats, Team, TeamMember, Permission, 
    RolePermission, UserRole, LaborRateConfig, CostCode, ProjectProductRelation
)
from .dependency import DependencyScan, LicenseRiskRule, Dependency, DependencyCVE
from .test_management import GTMTestCase, GTMTestCaseIssueLink, GTMRequirement, GTMTestExecutionRecord

# 核心插件模型导入 (用于模型注册)
try:
    from devops_collector.plugins.gitlab.models import (
        GitLabProject, GitLabGroup, GitLabProjectMember, GitLabGroupMember,
        GitLabCommit, GitLabMergeRequest, GitLabIssue, GitLabPipeline,
        GitLabDeployment, GitLabTag, GitLabBranch, GitLabMilestone,
        GitLabRelease, GitLabPackage, GitLabNote
    )
    from devops_collector.plugins.sonarqube.models import SonarProject, SonarMeasure, SonarIssue
    try:
        from devops_collector.plugins.jira.models import JiraProject, JiraIssue, JiraSprint, JiraBoard
    except ImportError:
        pass
except ImportError:
    pass

__all__ = [
    'Base', 'Organization', 'User', 'Role', 'Location', 'Calendar', 'SyncLog', 'RawDataStaging', 
    'IdentityMapping', 'Product', 'OKRObjective', 'OKRKeyResult', 'TraceabilityLink', 
    'TestExecutionSummary', 'PerformanceRecord', 'Incident', 'ResourceCost', 'UserActivityProfile', 
    'Service', 'ServiceProjectMapping', 'SLO', 'TimestampMixin', 'RawDataMixin', 'ProjectMaster', 
    'ContractPaymentNode', 'RevenueContract', 'PurchaseContract', 'UserCredential', 'UserOAuthToken', 
    'MetricDefinition', 'SystemRegistry', 'EntityTopology', 'Company', 'Vendor', 'EpicMaster', 
    'ComplianceIssue', 'CommitMetrics', 'DailyDevStats', 'Team', 'TeamMember', 'Permission', 
    'RolePermission', 'UserRole', 'LaborRateConfig', 'CostCode', 'ProjectProductRelation',
    'DependencyScan', 'LicenseRiskRule', 'Dependency', 'DependencyCVE',
    'GTMTestCase', 'GTMTestCaseIssueLink', 'GTMRequirement', 'GTMTestExecutionRecord'
]

from . import events