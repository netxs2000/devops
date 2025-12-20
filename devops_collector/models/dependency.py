"""
OWASP Dependency-Check 数据模型
存储依赖扫描、许可证信息和 CVE 漏洞数据
"""
from sqlalchemy import Column, Integer, String, Boolean, Float, Text, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from devops_collector.models import Base


class DependencyScan(Base):
    """依赖扫描记录表"""
    __tablename__ = 'dependency_scans'
    
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    scan_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    scanner_name = Column(String(50), nullable=False, default='OWASP Dependency-Check')
    scanner_version = Column(String(20))
    total_dependencies = Column(Integer, default=0)
    vulnerable_dependencies = Column(Integer, default=0)
    high_risk_licenses = Column(Integer, default=0)
    scan_status = Column(String(20), default='completed')  # completed, failed, in_progress
    report_path = Column(Text)
    raw_json = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # 关系
    project = relationship('Project', back_populates='dependency_scans')
    dependencies = relationship('Dependency', back_populates='scan', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f"<DependencyScan(id={self.id}, project_id={self.project_id}, status={self.scan_status})>"


class LicenseRiskRule(Base):
    """许可证风险规则表"""
    __tablename__ = 'license_risk_rules'
    
    id = Column(Integer, primary_key=True)
    license_name = Column(String(200), nullable=False, unique=True)
    license_spdx_id = Column(String(100))
    risk_level = Column(String(20), nullable=False)  # critical, high, medium, low
    is_copyleft = Column(Boolean, default=False)
    commercial_use_allowed = Column(Boolean, default=True)
    modification_allowed = Column(Boolean, default=True)
    distribution_allowed = Column(Boolean, default=True)
    patent_grant = Column(Boolean, default=False)
    description = Column(Text)
    policy_notes = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<LicenseRiskRule(name={self.license_name}, risk={self.risk_level})>"


class Dependency(Base):
    """依赖清单表"""
    __tablename__ = 'dependencies'
    __table_args__ = (
        UniqueConstraint('scan_id', 'package_name', 'package_version', name='uq_dependency_scan_package'),
    )
    
    id = Column(Integer, primary_key=True)
    scan_id = Column(Integer, ForeignKey('dependency_scans.id', ondelete='CASCADE'), nullable=False)
    project_id = Column(Integer, ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    
    # 依赖基本信息
    package_name = Column(String(500), nullable=False)
    package_version = Column(String(100))
    package_manager = Column(String(50))  # maven, npm, pypi, nuget, etc.
    dependency_type = Column(String(20), default='direct')  # direct, transitive
    
    # 许可证信息
    license_name = Column(String(200))
    license_spdx_id = Column(String(100))
    license_url = Column(Text)
    license_risk_level = Column(String(20))
    
    # 漏洞信息
    has_vulnerabilities = Column(Boolean, default=False)
    highest_cvss_score = Column(Float)
    critical_cve_count = Column(Integer, default=0)
    high_cve_count = Column(Integer, default=0)
    medium_cve_count = Column(Integer, default=0)
    low_cve_count = Column(Integer, default=0)
    
    # 元数据
    file_path = Column(Text)
    description = Column(Text)
    homepage_url = Column(Text)
    raw_data = Column(JSONB)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # 关系
    scan = relationship('DependencyScan', back_populates='dependencies')
    project = relationship('Project', back_populates='dependencies')
    cves = relationship('DependencyCVE', back_populates='dependency', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f"<Dependency(name={self.package_name}, version={self.package_version}, risk={self.license_risk_level})>"


class DependencyCVE(Base):
    """CVE 漏洞详情表"""
    __tablename__ = 'dependency_cves'
    __table_args__ = (
        UniqueConstraint('dependency_id', 'cve_id', name='uq_dependency_cve'),
    )
    
    id = Column(Integer, primary_key=True)
    dependency_id = Column(Integer, ForeignKey('dependencies.id', ondelete='CASCADE'), nullable=False)
    
    # CVE 信息
    cve_id = Column(String(50), nullable=False)
    cvss_score = Column(Float)
    cvss_vector = Column(String(200))
    severity = Column(String(20))  # CRITICAL, HIGH, MEDIUM, LOW
    
    # 漏洞描述
    description = Column(Text)
    published_date = Column(DateTime(timezone=True))
    last_modified_date = Column(DateTime(timezone=True))
    
    # 修复建议
    fixed_version = Column(String(100))
    remediation = Column(Text)
    
    # 引用链接
    references = Column(JSONB)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 关系
    dependency = relationship('Dependency', back_populates='cves')
    
    def __repr__(self):
        return f"<DependencyCVE(cve_id={self.cve_id}, severity={self.severity}, score={self.cvss_score})>"
