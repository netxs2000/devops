from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey, BigInteger
from sqlalchemy.orm import relationship
from datetime import datetime
from devops_collector.models.base_models import Base, Product

class NexusComponent(Base):
    """Nexus 组件模型。"""
    __tablename__ = 'nexus_components'
    
    id = Column(String(100), primary_key=True) # Nexus Component ID (Internal)
    repository = Column(String(100), nullable=False)
    format = Column(String(50)) # maven2, npm, docker, etc.
    group = Column(String(255))
    name = Column(String(255), nullable=False)
    version = Column(String(100))
    
    # 关联
    product_id = Column(Integer, ForeignKey('products.id'))
    product = relationship("Product")
    
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    
    assets = relationship("NexusAsset", back_populates="component", cascade="all, delete-orphan")
    raw_data = Column(JSON)


class NexusAsset(Base):
    """Nexus 资产（文件）模型。"""
    __tablename__ = 'nexus_assets'
    
    id = Column(String(100), primary_key=True) # Nexus Asset ID
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
    
    component = relationship("NexusComponent", back_populates="assets")
    raw_data = Column(JSON)
