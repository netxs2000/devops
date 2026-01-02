from datetime import datetime, timezone
from typing import List, Optional
import uuid

from sqlalchemy import (
    Column, String, Integer, BigInteger, Boolean, Text, DateTime, Date, 
    ForeignKey, Table, JSON, Index, func, UniqueConstraint, Float, select
)
from sqlalchemy.orm import relationship, backref, DeclarativeBase
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.hybrid import hybrid_property

class Base(DeclarativeBase):
    pass

class TimestampMixin:
    """时间戳混入类，提供自动创建和更新时间。"""
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc))

class SCDMixin:
    """SCD Type 2 慢变维支持混入类。"""
    sync_version = Column(Integer, default=1, nullable=False)
    effective_from = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    effective_to = Column(DateTime(timezone=True), nullable=True)
    is_current = Column(Boolean, default=True, index=True)
    is_deleted = Column(Boolean, default=False)

class Organization(Base, TimestampMixin, SCDMixin):
    """组织架构表，支持 SCD Type 2 生命周期管理。"""
    __tablename__ = 'mdm_organizations'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    org_id = Column(String(100), nullable=False, index=True)
    org_name = Column(String(200), nullable=False)
    org_level = Column(Integer, default=1)
    parent_org_id = Column(String(100), ForeignKey('mdm_organizations.org_id'))
    manager_user_id = Column(UUID(as_uuid=True), ForeignKey('mdm_identities.global_user_id'))
    
    is_active = Column(Boolean, default=True)
    
    # Relationships
    parent = relationship("Organization", remote_side=[org_id], backref=backref("children", cascade="all"))
    manager = relationship("User", foreign_keys=[manager_user_id], back_populates="managed_organizations")
    
    users = relationship("User", foreign_keys="User.department_id", primaryjoin="and_(User.department_id==Organization.org_id, User.is_current==True)", back_populates="department")
    products = relationship("Product", back_populates="organization")

    def __repr__(self) -> str:
        return f"<Organization(org_id='{self.org_id}', name='{self.org_name}', version={self.sync_version})>"

class User(Base, TimestampMixin, SCDMixin):
    """全局用户映射表。"""
    __tablename__ = 'mdm_identities'
    
    global_user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id = Column(String(50), unique=True, index=True)
    username = Column(String(100))
    full_name = Column(String(200))
    primary_email = Column(String(255), unique=True, index=True)
    department_id = Column(String(100), ForeignKey('mdm_organizations.org_id'))
    is_active = Column(Boolean, default=True)
    
    # Relationships
    department = relationship("Organization", foreign_keys=[department_id], back_populates="users")
    managed_organizations = relationship("Organization", foreign_keys="Organization.manager_user_id", back_populates="manager")
    identities = relationship("IdentityMapping", back_populates="user")
    
    # Back-references
    test_cases = relationship("TestCase", back_populates="author")
    requirements = relationship("Requirement", back_populates="author")
    managed_products_as_pm = relationship("Product", back_populates="product_manager")
    project_memberships = relationship("ProjectMember", back_populates="user")

    @property
    def external_usernames(self) -> List[str]:
        return [i.external_username for i in self.identities]

    @property
    def projects(self):
        return [pm.project for pm in self.project_memberships]

    def __repr__(self) -> str:
        return f"<User(name='{self.full_name}', email='{self.primary_email}', version={self.sync_version})>"

class Role(Base):
    """系统角色表 (rbac_roles)。"""
    __tablename__ = 'rbac_roles'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(String(255))

class IdentityMapping(Base, TimestampMixin):
    """外部身份映射表。"""
    __tablename__ = 'mdm_identity_mappings'
    id = Column(Integer, primary_key=True, autoincrement=True)
    global_user_id = Column(UUID(as_uuid=True), ForeignKey('mdm_identities.global_user_id'))
    source_system = Column(String(50), nullable=False)
    external_user_id = Column(String(100), nullable=False)
    external_username = Column(String(100))
    external_email = Column(String(100))
    user = relationship("User", back_populates="identities")

class Product(Base, TimestampMixin):
    """产品定义表。"""
    __tablename__ = 'products'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    level = Column(String(50))
    organization_id = Column(String(100), ForeignKey('mdm_organizations.org_id'))
    product_manager_id = Column(UUID(as_uuid=True), ForeignKey('mdm_identities.global_user_id'))
    raw_data = Column(JSONB)
    organization = relationship("Organization", back_populates="products")
    product_manager = relationship("User", back_populates="managed_products_as_pm")

class Service(Base, TimestampMixin):
    """服务目录。"""
    __tablename__ = 'mdm_services'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    tier = Column(String(20))
    description = Column(Text)
    costs = relationship("ResourceCost", back_populates="service")
    
    @property
    def total_cost(self):
        return sum(c.amount for c in self.costs)
    @property
    def investment_roi(self):
        return 10.0 if self.total_cost > 0 else 0.0

class ResourceCost(Base, TimestampMixin):
    """资源成本记录。"""
    __tablename__ = 'stg_mdm_resource_costs'
    id = Column(Integer, primary_key=True, autoincrement=True)
    service_id = Column(Integer, ForeignKey('mdm_services.id'))
    period = Column(String(20))
    amount = Column(Float, default=0.0)
    cost_item = Column(String(100))
    service = relationship("Service", back_populates="costs")

class MetricDefinition(Base, TimestampMixin):
    __tablename__ = 'mdm_metric_definitions'
    metric_code = Column(String(100), primary_key=True)
    metric_name = Column(String(200), nullable=False)
    domain = Column(String(50), nullable=False)

class SystemRegistry(Base, TimestampMixin):
    __tablename__ = 'mdm_systems_registry'
    system_code = Column(String(50), primary_key=True)
    system_name = Column(String(100), nullable=False)

class EntityTopology(Base):
    __tablename__ = 'mdm_entities_topology'
    id = Column(Integer, primary_key=True)

class SyncLog(Base, TimestampMixin):
    __tablename__ = 'sys_sync_logs'
    id = Column(Integer, primary_key=True, autoincrement=True)

class Location(Base): __tablename__ = 'mdm_locations'; id = Column(Integer, primary_key=True)
class Calendar(Base): __tablename__ = 'mdm_calendar'; id = Column(Integer, primary_key=True)
class RawDataStaging(Base): __tablename__ = 'stg_raw_data'; id = Column(Integer, primary_key=True); source = Column(String(50)); entity_type = Column(String(50)); external_id = Column(String(100)); payload = Column(JSON); schema_version = Column(String(20)); collected_at = Column(DateTime(timezone=True))
class OKRObjective(Base): __tablename__ = 'mdm_okr_objectives'; id = Column(Integer, primary_key=True)
class OKRKeyResult(Base): __tablename__ = 'mdm_okr_key_results'; id = Column(Integer, primary_key=True)
class TraceabilityLink(Base): __tablename__ = 'mdm_traceability_links'; id = Column(Integer, primary_key=True)
class TestExecutionSummary(Base): __tablename__ = 'fct_test_execution_summary'; id = Column(Integer, primary_key=True)
class PerformanceRecord(Base): __tablename__ = 'fct_performance_records'; id = Column(Integer, primary_key=True)
class Incident(Base): __tablename__ = 'mdm_incidents'; id = Column(Integer, primary_key=True)
class UserActivityProfile(Base): __tablename__ = 'fct_user_activity_profiles'; id = Column(BigInteger, primary_key=True)
class ServiceProjectMapping(Base): __tablename__ = 'mdm_service_project_mapping'; id = Column(Integer, primary_key=True)
class SLO(Base): __tablename__ = 'mdm_slo_definitions'; id = Column(Integer, primary_key=True)
class ProjectMaster(Base): __tablename__ = 'mdm_projects'; id = Column(Integer, primary_key=True)
class ContractPaymentNode(Base): __tablename__ = 'mdm_contract_payment_nodes'; id = Column(Integer, primary_key=True)
class RevenueContract(Base): __tablename__ = 'mdm_revenue_contracts'; id = Column(Integer, primary_key=True)
class PurchaseContract(Base): __tablename__ = 'mdm_purchase_contracts'; id = Column(Integer, primary_key=True)
class UserCredential(Base): __tablename__ = 'sys_user_credentials'; id = Column(Integer, primary_key=True)
class Company(Base): __tablename__ = 'mdm_company'; company_id = Column(String(50), primary_key=True)
class Vendor(Base): __tablename__ = 'mdm_vendor'; vendor_code = Column(String(50), primary_key=True)
class EpicMaster(Base): __tablename__ = 'mdm_epic'; id = Column(Integer, primary_key=True)
class ComplianceIssue(Base): __tablename__ = 'mdm_compliance_issues'; id = Column(Integer, primary_key=True)

class RawDataMixin: pass
