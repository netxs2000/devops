from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey, BigInteger, Float
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime, timezone
from devops_collector.models.base_models import Base, User, Product

class JFrogArtifact(Base):
    """JFrog 制品模型 (jfrog_artifacts)。
    
    存储从 Artifactory 采集的制品元数据，支持 SLSA 溯源。

    Attributes:
        id (int): 自增主键。
        repo (str): 仓库名称。
        path (str): 制品路径。
        name (str): 制品文件名。
        version (str): 版本号。
        package_type (str): 包类型 (docker, maven, pypi 等)。
        size_bytes (int): 文件大小 (字节)。
        sha256 (str): SHA256 校验码。
        download_count (int): 下载次数。
        last_downloaded_at (datetime): 最近下载时间。
        build_name (str): 关联的构建名称。
        build_number (str): 关联的构建号。
        build_url (str): 构建详情 URL。
        vcs_url (str): 源码仓库地址。
        vcs_revision (str): 源码修订版本 (Commit Hash)。
        builder_id (str): 构建平台标识。
        is_signed (int): 是否已签名 (0: 否, 1: 是)。
        promotion_status (str): 晋级状态 (staging, released 等)。
        properties (dict): 自定义属性 (JSON)。
        created_by_id (UUID): 创建者的 OneID。
        created_by_name (str): 创建者显示名。
        product_id (int): 关联的产品 ID。
        created_by (User): 关联的用户对象。
        product (Product): 关联的产品对象。
    """
    __tablename__ = 'jfrog_artifacts'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    repo = Column(String(100), nullable=False)
    path = Column(String(500), nullable=False)
    name = Column(String(200), nullable=False)
    version = Column(String(100))
    package_type = Column(String(50))
    
    size_bytes = Column(BigInteger)
    sha256 = Column(String(64))
    
    download_count = Column(Integer, default=0)
    last_downloaded_at = Column(DateTime(timezone=True))
    
    build_name = Column(String(200))
    build_number = Column(String(50))
    build_url = Column(String(500))
    vcs_url = Column(String(500))
    vcs_revision = Column(String(100))
    
    builder_id = Column(String(200))
    build_type = Column(String(100))
    is_signed = Column(Integer, default=0)
    external_parameters = Column(JSON)
    build_started_at = Column(DateTime(timezone=True))
    build_ended_at = Column(DateTime(timezone=True))
    
    promotion_status = Column(String(50))
    properties = Column(JSON)
    
    created_by_id = Column(
        UUID(as_uuid=True), ForeignKey('mdm_identities.global_user_id')
    )
    created_by_name = Column(String(100))
    product_id = Column(Integer, ForeignKey('products.id'))
    
    created_by = relationship("User")
    product = relationship("Product")
    
    created_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True))
    raw_data = Column(JSON)

    def __repr__(self) -> str:
        return f"<JFrogArtifact(name='{self.name}', version='{self.version}')>"


class JFrogScan(Base):
    """JFrog Xray 扫描结果模型。

    Attributes:
        id (int): 自增主键。
        artifact_id (int): 关联的制品 ID。
        critical_count (int): 严重漏洞数。
        high_count (int): 高危漏洞数。
        medium_count (int): 中危漏洞数。
        low_count (int): 低危漏洞数。
        violation_count (int): 策略违反数。
        is_compliant (int): 是否合规 (1: 是, 0: 否)。
        scan_time (datetime): 扫描时间。
        artifact (JFrogArtifact): 关联的制品。
    """
    __tablename__ = 'jfrog_scans'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    artifact_id = Column(Integer, ForeignKey('jfrog_artifacts.id'))
    
    critical_count = Column(Integer, default=0)
    high_count = Column(Integer, default=0)
    medium_count = Column(Integer, default=0)
    low_count = Column(Integer, default=0)
    
    violation_count = Column(Integer, default=0)
    is_compliant = Column(Integer)
    
    scan_time = Column(DateTime(timezone=True))
    raw_data = Column(JSON)
    
    artifact = relationship("JFrogArtifact")

    def __repr__(self) -> str:
        return f"<JFrogScan(artifact_id={self.artifact_id}, compliant={self.is_compliant})>"


class JFrogVulnerabilityDetail(Base):
    """漏洞详情明细表。

    Attributes:
        id (int): 自增主键。
        artifact_id (int): 关联的制品 ID。
        cve_id (str): CVE 编号。
        severity (str): 严重程度。
        cvss_score (float): CVSS 评分。
        component (str): 受影响的组件名。
        fixed_version (str): 修复版本。
        description (str): 漏洞描述。
    """
    __tablename__ = 'jfrog_vulnerability_details'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    artifact_id = Column(Integer, ForeignKey('jfrog_artifacts.id'))
    
    cve_id = Column(String(50), index=True)
    severity = Column(String(20))
    cvss_score = Column(Float)
    component = Column(String(200))
    fixed_version = Column(String(100))
    description = Column(String)
    
    artifact = relationship("JFrogArtifact")

    def __repr__(self) -> str:
        return f"<JFrogVulnerabilityDetail(cve='{self.cve_id}', severity='{self.severity}')>"


class JFrogDependency(Base):
    """制品依赖树模型 (SBoM)。

    Attributes:
        id (int): 自增主键。
        artifact_id (int): 关联的制品 ID。
        name (str): 依赖项名称。
        version (str): 依赖项版本。
        package_type (str): 包类型。
        scope (str): 依赖范围 (compile, runtime 等)。
    """
    __tablename__ = 'jfrog_dependencies'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    artifact_id = Column(Integer, ForeignKey('jfrog_artifacts.id'))
    
    name = Column(String(200), nullable=False)
    version = Column(String(100))
    package_type = Column(String(50))
    scope = Column(String(50))
    
    artifact = relationship("JFrogArtifact")

    def __repr__(self) -> str:
        return f"<JFrogDependency(name='{self.name}', version='{self.version}')>"
