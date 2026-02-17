import pytest
import uuid
from sqlalchemy.orm import Session
from devops_collector.core.admin_service import AdminService
from devops_collector.models.base_models import Product, ProjectProductRelation, Team, TeamMember, User
from devops_portal import schemas

@pytest.fixture
def admin_service(db_session: Session):
    return AdminService(db_session)

def test_create_product(admin_service, db_session):
    """单元测试：验证产品主数据创建控制。"""
    payload = schemas.ProductCreate(
        product_id="PD-001",

        product_name="Mobile Application",
        product_description="Test Description",
        category="Software"
    )
    product = admin_service.create_product(payload)
    
    assert product.product_id == "PD-001"
    
    # 验证数据库中存在
    db_product = db_session.query(Product).filter_by(product_id="PD-001").first()
    assert db_product is not None

def test_link_product_to_project(admin_service, db_session):
    """单元测试：验证产品与项目的映射关联逻辑。"""
    # 准备数据
    from devops_collector.models.base_models import ProjectMaster, Organization
    org = Organization(org_id="O1", org_name="Test Org")
    db_session.add(org)
    
    project = ProjectMaster(
        project_id="PROJ-001", 
        project_name="Test Project",
        org_id="O1"
    )
    db_session.add(project)
    
    product = Product(
        product_id="PROD-001", 
        product_name="Test Product", 

        product_description="Desc", # Required
        version_schema="semver" # Required
    )
    db_session.add(product)
    db_session.commit()
    
    payload = schemas.ProjectProductRelationCreate(
        project_id="PROJ-001",
        product_id="PROD-001",
        relation_type="CORE",
        allocation_ratio=0.8
    )
    
    relation = admin_service.link_product_to_project(payload)
    assert relation.project_id == "PROJ-001"
    assert relation.allocation_ratio == 0.8
    
    # 验证数据库
    db_rel = db_session.query(ProjectProductRelation).first()
    assert db_rel is not None
    assert db_rel.relation_type == "CORE"

def test_create_team(admin_service, db_session):
    """单元测试：验证虚拟团队创建。"""
    payload = schemas.TeamCreate(
        name="Backend Team",
        team_code="BE_TEAM"
    )
    team = admin_service.create_team(payload)
    assert team.name == "Backend Team"
    assert team.team_code == "BE_TEAM"

def test_add_team_member(admin_service, db_session):
    """单元测试：验证团队成员绑定逻辑。"""
    team = Team(name="T1", team_code="T1")
    user_id = uuid.uuid4()
    user = User(global_user_id=user_id, primary_email="test@test.com", username="tester")
    db_session.add_all([team, user])
    db_session.commit()
    
    payload = schemas.TeamMemberCreate(
        user_id=user_id,
        role_code="DEVELOPER",
        allocation_ratio=0.5
    )
    
    admin_service.add_team_member(team.id, payload)
    
    # 验证
    member = db_session.query(TeamMember).filter_by(team_id=team.id).first()
    assert member is not None
    assert member.role_code == "DEVELOPER"
    assert member.allocation_ratio == 0.5
