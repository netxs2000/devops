from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey, BigInteger, Float
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from devops_collector.models.base_models import Base, User, Product

class JFrogArtifact(Base):
    """JFrog 制品模型。"""
    __tablename__ = 'jfrog_artifacts'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    repo = Column(String(100), nullable=False)
    path = Column(String(500), nullable=False)
    name = Column(String(200), nullable=False)
    version = Column(String(100))
    package_type = Column(String(50)) # docker, maven, pypi, etc.
    
    size_bytes = Column(BigInteger)
    sha256 = Column(String(64))
    
    download_count = Column(Integer, default=0)
    last_downloaded_at = Column(DateTime(timezone=True))
    
    # 构建与可追溯性
    build_name = Column(String(200))
    build_number = Column(String(50))
    build_url = Column(String(500))
    vcs_url = Column(String(500))
    vcs_revision = Column(String(100)) # Git Commit Hash
    
    # SLSA 溯源与合规 (Level 2/3)
    builder_id = Column(String(200)) # 标识构建平台
    build_type = Column(String(100)) # 标识构建任务类型
    is_signed = Column(Integer, default=0) # 0: 未签名, 1: 已签名
    external_parameters = Column(JSON) # 存储构建外部参数 (L3 要求)
    build_started_at = Column(DateTime(timezone=True))
    build_ended_at = Column(DateTime(timezone=True))
    
    # 晋级与属性
    promotion_status = Column(String(50)) # e.g., 'staging', 'released'
    properties = Column(JSON) # 存储自定义属性
    
    # 关联
    created_by_id = Column(Integer, ForeignKey('users.id'))
    created_by_name = Column(String(100)) # 冗余记录创建人名称
    product_id = Column(Integer, ForeignKey('products.id'))
    
    created_by = relationship("User")
    product = relationship("Product")
    
    created_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True))
    raw_data = Column(JSON)


class JFrogScan(Base):
    """JFrog Xray 扫描生命周期概览。"""
    __tablename__ = 'jfrog_scans'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    artifact_id = Column(Integer, ForeignKey('jfrog_artifacts.id'))
    
    # 漏洞概览统计
    critical_count = Column(Integer, default=0)
    high_count = Column(Integer, default=0)
    medium_count = Column(Integer, default=0)
    low_count = Column(Integer, default=0)
    
    # 策略合规
    violation_count = Column(Integer, default=0)
    is_compliant = Column(Integer) # 0/1 indicator
    
    scan_time = Column(DateTime(timezone=True))
    raw_data = Column(JSON)
    
    artifact = relationship("JFrogArtifact")


class JFrogVulnerabilityDetail(Base):
    """单独存储每一个漏洞详情，便于全局检索漏洞。"""
    __tablename__ = 'jfrog_vulnerability_details'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    artifact_id = Column(Integer, ForeignKey('jfrog_artifacts.id'))
    
    cve_id = Column(String(50), index=True) # e.g., CVE-2021-44228
    severity = Column(String(20)) # Critical, High, etc.
    cvss_score = Column(Float)
    component = Column(String(200)) # 受影响的依赖库
    fixed_version = Column(String(100))
    description = Column(String)
    
    artifact = relationship("JFrogArtifact")


class JFrogDependency(Base):
    """制品依赖树模型 (SBoM)。"""
    __tablename__ = 'jfrog_dependencies'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    artifact_id = Column(Integer, ForeignKey('jfrog_artifacts.id'))
    
    name = Column(String(200), nullable=False)
    version = Column(String(100))
    package_type = Column(String(50))
    scope = Column(String(50)) # compile, runtime, etc.
    
    # 关联
    artifact = relationship("JFrogArtifact")
