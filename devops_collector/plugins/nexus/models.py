"""TODO: Add module description."""
from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey, BigInteger
from sqlalchemy.orm import relationship
from datetime import datetime
from devops_collector.models.base_models import Base, Product

class NexusComponent(Base):
    """Nexus 组件模型 (nexus_components)。
    
    Attributes:
        id (str): Nexus 内部组件 ID。
        repository (str): 仓库名称。
        format (str): 格式 (maven2, npm, docker 等)。
        group (str): 组织/分组。
        name (str): 组件名称。
        version (str): 版本号。
        product_id (int): 关联的产品 ID。
        product (Product): 关联的产品对象。
        assets (List[NexusAsset]): 该组件包含的资产列表。
    """
    __tablename__ = 'nexus_components'
    id = Column(String(100), primary_key=True)
    repository = Column(String(100), nullable=False)
    format = Column(String(50))
    group = Column(String(255))
    name = Column(String(255), nullable=False)
    version = Column(String(100))
    product_id = Column(Integer, ForeignKey('products.id'))
    product = relationship('Product')
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    assets = relationship('NexusAsset', back_populates='component', cascade='all, delete-orphan')
    raw_data = Column(JSON)

    def __repr__(self) -> str:
        '''"""TODO: Add description.

Args:
    self: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        return f"<NexusComponent(name='{self.name}', version='{self.version}')>"

class NexusAsset(Base):
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
    __tablename__ = 'nexus_assets'
    id = Column(String(100), primary_key=True)
    component_id = Column(String(100), ForeignKey('nexus_components.id'))
    path = Column(String(500), nullable=False)
    download_url = Column(String(1000))
    size_bytes = Column(BigInteger)
    checksum_sha1 = Column(String(40))
    checksum_sha256 = Column(String(64))
    checksum_md5 = Column(String(32))
    created_at = Column(DateTime)
    last_modified = Column(DateTime)
    last_downloaded = Column(DateTime)
    component = relationship('NexusComponent', back_populates='assets')
    raw_data = Column(JSON)

    def __repr__(self) -> str:
        '''"""TODO: Add description.

Args:
    self: TODO

Returns:
    TODO

Raises:
    TODO
"""'''
        return f"<NexusAsset(path='{self.path}')>"