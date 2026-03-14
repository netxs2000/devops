"""Nexus 插件数据模型。"""

from sqlalchemy import JSON, BigInteger, Column, DateTime, ForeignKey, String, Index
from sqlalchemy.orm import relationship

from devops_collector.models.base_models import (
    Base,
    OwnableMixin,
    SCDMixin,
    TimestampMixin,
)


class NexusComponent(Base, TimestampMixin, SCDMixin, OwnableMixin):
    """Nexus 组件模型 (nexus_components)。

    Attributes:
        id (str): Nexus 内部组件 ID。
        repository (str): 仓库名称。
        format (str): 格式 (maven2, npm, docker 等)。
        group (str): 组织/分组。
        name (str): 组件名称。
        version (str): 版本号。
        product_id (str): 关联的产品 ID。
        product (Product): 关联的产品对象。
        assets (List[NexusAsset]): 该组件包含的资产列表。
    """

    __tablename__ = "nexus_components"
    id = Column(String(100), primary_key=True)
    repository = Column(String(100), nullable=False)
    format = Column(String(50))
    group = Column(String(255))
    name = Column(String(255), nullable=False)
    version = Column(String(100))
    product_id = Column(String(100), ForeignKey("mdm_product.product_id"), nullable=True)
    commit_sha = Column(String(100), index=True)  # 新增：直接存储 Git Commit SHA，提升 DORA 关联性能

    # 索引优化：为常用的查询组合建立联合索引
    __table_args__ = (
        Index('ix_nexus_components_lookup', 'repository', 'group', 'name'),
    )

    product = relationship("Product")
    assets = relationship("NexusAsset", back_populates="component", cascade="all, delete-orphan")
    raw_data = Column(JSON)

    def __repr__(self) -> str:
        return f"<NexusComponent(name='{self.name}', version='{self.version}')>"


class NexusAsset(Base, TimestampMixin, SCDMixin):
    """Nexus 资产（文件）模型 (nexus_assets)。

    Attributes:
        id (str): Nexus 资产唯一 ID。
        component_id (str): 关联的组件 ID。
        path (str): 文件路径。
        download_url (str): 下载链接。
        size_bytes (int): 文件大小 (字节)。
        checksum_sha256 (str): SHA256 校验码。
        component (NexusComponent): 关联的组件对象。
    """

    __tablename__ = "nexus_assets"
    id = Column(String(100), primary_key=True)
    component_id = Column(String(100), ForeignKey("nexus_components.id"))
    path = Column(String(500), nullable=False)
    download_url = Column(String(1000))
    size_bytes = Column(BigInteger)
    checksum_sha1 = Column(String(40))
    checksum_sha256 = Column(String(64))
    checksum_md5 = Column(String(32))

    last_modified = Column(DateTime)
    last_downloaded = Column(DateTime)

    component = relationship("NexusComponent", back_populates="assets")
    raw_data = Column(JSON)

    def __repr__(self) -> str:
        return f"<NexusAsset(path='{self.path}')>"
