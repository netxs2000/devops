"""
OWASP Dependency-Check 数据模型
存储依赖扫描、许可证信息和 CVE 漏洞数据
"""

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)


JSONB = JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base_models import Base, SCDMixin, TimestampMixin


class DependencyScan(Base, TimestampMixin, SCDMixin):
    """依赖扫描记录表 (dependency_scans)。

    存储 OWASP Dependency-Check 等工具生成的扫描任务概览。

    Attributes:
        id (int): 自增主键。
        project_id (int): 关联的 GitLab 项目 ID。
        scan_date (datetime): 扫描执行时间。
        scanner_name (str): 扫描器名称 (e.g. OWASP Dependency-Check)。
        scanner_version (str): 扫描器版本。
        total_dependencies (int): 扫描发现的依赖总数。
        vulnerable_dependencies (int): 存在漏洞的依赖数。
        high_risk_licenses (int): 存在高风险许可证的依赖数。
        scan_status (str): 任务状态 (completed, failed, in_progress)。
        report_path (str): 报告文件存放路径。
        raw_json (dict): 原始报告 JSON 内容。
        project (Project): 关联的项目对象。
        dependencies (List[Dependency]): 关联的依赖明细。
    """

    __tablename__ = "dependency_scans"
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("gitlab_projects.id", ondelete="CASCADE"), nullable=False)
    scan_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    scanner_name = Column(String(50), nullable=False, default="OWASP Dependency-Check")
    scanner_version = Column(String(20))
    total_dependencies = Column(Integer, default=0)
    vulnerable_dependencies = Column(Integer, default=0)
    high_risk_licenses = Column(Integer, default=0)
    scan_status = Column(String(20), default="completed")
    ci_job_id = Column(String(50), comment="CI Job ID")
    ci_job_url = Column(String(500), comment="CI Job URL")
    commit_sha = Column(String(40), comment="Commit SHA")
    branch = Column(String(100), comment="Branch Name")
    report_url = Column(String(500), comment="Report Storage URL")
    scan_duration_seconds = Column(Float, comment="Scan Duration (Seconds)")
    raw_json = Column(JSONB)
    created_by = Column(
        UUID(as_uuid=True),
        ForeignKey("mdm_identities.global_user_id"),
        nullable=True,
        comment="创建人",
    )
    project = relationship("GitLabProject", back_populates="dependency_scans")

    dependencies = relationship("Dependency", back_populates="scan", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        """返回依赖扫描记录的字符串表示。"""
        return f"<DependencyScan(id={self.id}, project_id={self.project_id}, status='{self.scan_status}')>"


class LicenseRiskRule(Base, TimestampMixin):
    """许可证风险规则配置表 (license_risk_rules)。

    用于定义不同开源许可证的合规性风险评级。

    Attributes:
        id (int): 自增主键。
        license_name (str): 许可证名称 (e.g. GPL-3.0)。
        license_spdx_id (str): SPDX 标识符。
        risk_level (str): 风险等级 (critical, high, medium, low)。
        is_copyleft (bool): 是否为传染性许可证 (Copyleft)。
        commercial_use_allowed (bool): 是否允许商业用途。
        modification_allowed (bool): 是否允许修改源码。
        distribution_allowed (bool): 是否允许分发。
        patent_grant (bool): 是否授予专利显式许可。
        is_active (bool): 规则是否处于启用状态。
    """

    __tablename__ = "license_risk_rules"
    id = Column(Integer, primary_key=True)
    license_name = Column(String(200), nullable=False, unique=True)
    license_spdx_id = Column(String(100))
    risk_level = Column(String(20), nullable=False)
    is_copyleft = Column(Boolean, default=False)
    commercial_use_allowed = Column(Boolean, default=True)
    modification_allowed = Column(Boolean, default=True)
    distribution_allowed = Column(Boolean, default=True)
    patent_grant = Column(Boolean, default=False)
    description = Column(Text)
    policy_notes = Column(Text)
    is_active = Column(Boolean, default=True)

    def __repr__(self) -> str:
        """返回许可证风险规则的字符串表示。"""
        return f"<LicenseRiskRule(name='{self.license_name}', risk='{self.risk_level}')>"


class Dependency(Base, TimestampMixin):
    """项目依赖清单表 (dependencies)。

    存储扫描发现的每一个具体的三方类库及其安全和合规状态。

    Attributes:
        id (int): 自增主键。
        scan_id (int): 所属扫描任务 ID。
        project_id (int): 关联的项目 ID。
        package_name (str): 包名 (e.g. requests, log4j)。
        package_version (str): 版本号。
        package_manager (str): 包管理器 (maven, npm, pypi, nuget)。
        dependency_type (str): 依赖类型 (direct, transitive)。
        license_name (str): 采集到的许可证名。
        license_risk_level (str): 匹配到的许可证风险等级。
        has_vulnerabilities (bool): 是否存在 CVE 漏洞。
        highest_cvss_score (float): 最高 CVSS 评分。
        critical_cve_count (int): 严重 CVE 数量。
        is_ignored (bool): 是否标记为误报/忽略。
        ignore_reason (str): 忽略原因。
        ignore_by (str): 操作人。
        ignore_at (datetime): 操作时间。
        scan (DependencyScan): 关联的扫描任务。
        project (Project): 关联的项目对象。
        cves (List[DependencyCVE]): 关联的漏洞列表。
    """

    __tablename__ = "dependencies"
    __table_args__ = (
        UniqueConstraint("scan_id", "package_name", "package_version", name="uq_dependency_scan_package"),
    )
    id = Column(Integer, primary_key=True)
    scan_id = Column(Integer, ForeignKey("dependency_scans.id", ondelete="CASCADE"), nullable=False)
    project_id = Column(Integer, ForeignKey("gitlab_projects.id", ondelete="CASCADE"), nullable=False)
    package_name = Column(String(500), nullable=False)
    package_version = Column(String(100))
    package_manager = Column(String(50))
    dependency_type = Column(String(20), default="direct")
    license_name = Column(String(200))
    license_spdx_id = Column(String(100))
    license_url = Column(Text)
    license_risk_level = Column(String(20))
    has_vulnerabilities = Column(Boolean, default=False)
    highest_cvss_score = Column(Float)
    critical_cve_count = Column(Integer, default=0)
    high_cve_count = Column(Integer, default=0)
    medium_cve_count = Column(Integer, default=0)
    low_cve_count = Column(Integer, default=0)

    # [新增] 误报管理
    is_ignored = Column(Boolean, default=False)
    ignore_reason = Column(Text)
    ignore_by = Column(String(50))
    ignore_at = Column(DateTime(timezone=True))

    file_path = Column(Text)
    description = Column(Text)
    homepage_url = Column(Text)
    raw_data = Column(JSONB)
    scan = relationship("DependencyScan", back_populates="dependencies")

    project = relationship("GitLabProject", back_populates="dependencies")
    cves = relationship("DependencyCVE", back_populates="dependency", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        """返回项目依赖的字符串表示。"""
        return f"<Dependency(name='{self.package_name}', version='{self.package_version}')>"


class DependencyCVE(Base, TimestampMixin):
    """CVE 漏洞详情表 (dependency_cves)。

    Attributes:
        id (int): 自增主键。
        dependency_id (int): 关联的依赖 ID。
        cve_id (str): CVE 编号 (e.g. CVE-2021-44228)。
        cvss_score (float): CVSS 评分。
        cvss_vector (str): CVSS 向量。
        severity (str): 严重等级 (CRITICAL, HIGH, MEDIUM, LOW)。
        fixed_version (str): 建议修复版本。
        is_ignored (bool): 是否标记为误报/忽略。
        ignore_reason (str): 忽略原因。
        dependency (Dependency): 关联的依赖对象。
    """

    __tablename__ = "dependency_cves"
    __table_args__ = (UniqueConstraint("dependency_id", "cve_id", name="uq_dependency_cve"),)
    id = Column(Integer, primary_key=True)
    dependency_id = Column(Integer, ForeignKey("dependencies.id", ondelete="CASCADE"), nullable=False)
    cve_id = Column(String(50), nullable=False)
    cvss_score = Column(Float)
    cvss_vector = Column(String(200))
    severity = Column(String(20))
    description = Column(Text)
    published_date = Column(DateTime(timezone=True))
    last_modified_date = Column(DateTime(timezone=True))
    fixed_version = Column(String(100))
    remediation = Column(Text)
    references = Column(JSONB)

    # [新增] 误报管理
    is_ignored = Column(Boolean, default=False)
    ignore_reason = Column(Text)

    dependency = relationship("Dependency", back_populates="cves")

    def __repr__(self):
        '''"""TODO: Add description.

        Args:
            self: TODO

        Returns:
            TODO

        Raises:
            TODO
        """'''
        return f"<DependencyCVE(cve_id='{self.cve_id}', severity='{self.severity}')>"
