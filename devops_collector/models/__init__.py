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
    SyncLog,
    TimestampMixin,
    RawDataMixin
)

# 从 GitLab 插件导入特定模型
from devops_collector.plugins.gitlab.models import (
    Project,
    Commit,
    CommitFileStats,
    Issue,
    MergeRequest,
    Pipeline,
    Deployment,
    Note,
    Tag,
    Branch
)

# 从 SonarQube 插件导入模型
from devops_collector.plugins.sonarqube.models import (
    SonarProject,
    SonarMeasure,
    SonarIssue
)

__all__ = [
    # 公共基础模型
    'Base', 'Organization', 'User', 'SyncLog',
    'TimestampMixin', 'RawDataMixin',
    # GitLab 模型
    'Project', 'Commit', 'CommitFileStats',
    'Issue', 'MergeRequest', 'Pipeline', 'Deployment', 
    'Note', 'Tag', 'Branch',
    # SonarQube 模型
    'SonarProject', 'SonarMeasure', 'SonarIssue'
]
