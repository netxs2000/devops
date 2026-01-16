import pytest
from sqlalchemy.exc import IntegrityError
from devops_collector.models.base_models import (
    BusinessSystem, Service, SystemRegistry, EntityTopology, User
)
import uuid

def test_create_business_system(db_session):
    """Test creating a BusinessSystem."""
    system = BusinessSystem(
        code="trade-core",
        name="Trading System",
        description="The core trading platform",
        domain="E-Commerce"
    )
    db_session.add(system)
    db_session.commit()
    db_session.refresh(system)
    
    assert system.id is not None
    assert system.code == "trade-core"
    assert system.name == "Trading System"

def test_create_system_registry(db_session):
    """Test creating a SystemRegistry entry."""
    registry = SystemRegistry(
        system_code="GITLAB_CORP",
        system_name="Corporate GitLab",
        system_type="VCS",
        base_url="https://gitlab.example.com",
        api_version="v4",
        auth_type="Token",
        is_active=True
    )
    db_session.add(registry)
    db_session.commit()
    db_session.refresh(registry)
    
    assert registry.system_code == "GITLAB_CORP"
    assert registry.base_url == "https://gitlab.example.com"

def test_link_service_to_business_system(db_session):
    """Test linking a Service to a BusinessSystem."""
    # 1. Create System
    biz_system = BusinessSystem(code="fin-core", name="Financial System")
    db_session.add(biz_system)
    db_session.commit()
    
    # 2. Create Service linked to System
    service = Service(
        name="payment-service",
        system_id=biz_system.id,
        component_type="service",
        lifecycle="production",
        tags=["java", "critical"]
    )
    db_session.add(service)
    db_session.commit()
    db_session.refresh(service)
    
    # 3. Verify association
    assert service.system_id == biz_system.id
    assert service.system.code == "fin-core"
    # Verify reverse relationship
    assert len(biz_system.services) == 1
    assert biz_system.services[0].name == "payment-service"

def test_entity_topology_integration(db_session):
    """Test the full chain: Service -> EntityTopology -> SystemRegistry."""
    # 1. Create Business Service
    service = Service(name="order-service")
    db_session.add(service)
    
    # 2. Create System Registry (Tool)
    tool = SystemRegistry(system_code="SONAR_01", system_name="SonarQube Main")
    db_session.add(tool)
    db_session.commit()
    
    # 3. Create Topology Mapping
    topo = EntityTopology(
        service_id=service.id,
        system_code=tool.system_code,
        external_resource_id="project-key-abc",
        element_type="quality-gate",
        meta_info={"branch": "main"}
    )
    db_session.add(topo)
    db_session.commit()
    db_session.refresh(topo)
    
    # 4. Verify Linkages
    assert topo.service.name == "order-service"
    assert topo.target_system.system_name == "SonarQube Main"
    
    # 5. Verify Service can access its resources
    db_session.refresh(service)
    assert len(service.resources) == 1
    assert service.resources[0].external_resource_id == "project-key-abc"

def test_cascade_delete_service(db_session):
    """Test that deleting a Service also deletes its Topology links."""
    # 1. Setup Data
    service = Service(name="temp-service")
    tool = SystemRegistry(system_code="TEMP_TOOL", system_name="Temp Tool")
    db_session.add(service)
    db_session.add(tool)
    db_session.commit()
    
    topo = EntityTopology(
        service_id=service.id,
        system_code="TEMP_TOOL",
        external_resource_id="temp-1",
    )
    db_session.add(topo)
    db_session.commit()
    
    assert db_session.query(EntityTopology).count() == 1
    
    # 2. Delete Service
    db_session.delete(service)
    db_session.commit()
    
    # 3. Verify Topology is gone
    assert db_session.query(EntityTopology).count() == 0
    # Logic: Service.resources relationship has cascade='all, delete-orphan'

def test_topology_integrity_constraint(db_session):
    """Test that creating Topology with invalid system_code fails."""
    service = Service(name="test-service")
    db_session.add(service)
    db_session.commit()
    
    # Try to link to non-existent system
    topo = EntityTopology(
        service_id=service.id,
        system_code="INVALID_SYSTEM_CODE", # Does not exist in SystemRegistry
        external_resource_id="123"
    )
    db_session.add(topo)
    
    # Expect IntegrityError due to FK constraint
    with pytest.raises(IntegrityError):
        db_session.commit()
