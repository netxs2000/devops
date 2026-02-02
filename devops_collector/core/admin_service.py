"""系统管理核心业务服务层。

该模块封装了“系统管理模块”的核心业务逻辑，包括：
1. 用户全景画像聚合
2. 虚拟团队与成员管理
3. 业务主项目 (MDM) 与仓库关联管理
"""
import logging
import uuid
import csv
import io
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session, joinedload
from devops_collector.models.base_models import Organization, User, ProjectMaster, IdentityMapping, Team, TeamMember, UserRole, Product, ProjectProductRelation
from devops_collector.plugins.gitlab.models import GitLabProject
from devops_portal import schemas

logger = logging.getLogger(__name__)

class AdminService:
    """系统管理业务逻辑服务。"""

    def __init__(self, session: Session):
        """初始化管理服务。

        Args:
            session (Session): 数据库会话。
        """
        self.session = session

    def get_user_full_profile(self, user_id: uuid.UUID) -> schemas.UserFullProfile:
        """获取用户全景画像。"""
        user = self.session.query(User).filter(User.global_user_id == user_id).first()
        if not user:
            return None
        
        identities = []
        for m in user.identities:
            view = schemas.IdentityMappingView.model_validate(m)
            view.user_name = user.full_name
            view.hr_relationship = user.hr_relationship
            identities.append(view)
            
        teams = []
        for tm in user.team_memberships:
            teams.append({
                "team_id": tm.team.id,
                "team_name": tm.team.name,
                "role": tm.role_code,
                "allocation": tm.allocation_ratio
            })
            
        return schemas.UserFullProfile(
            global_user_id=user.global_user_id,
            full_name=user.full_name,
            username=user.username,
            primary_email=user.primary_email,
            employee_id=user.employee_id,
            department_name=user.department.org_name if user.department else None,
            is_active=user.is_active,
            hr_relationship=user.hr_relationship,
            identities=identities,
            teams=teams
        )

    def create_team(self, data: schemas.TeamCreate) -> Team:
        """创建虚拟团队。"""
        new_team = Team(
            name=data.name,
            team_code=data.team_code,
            description=data.description,
            parent_id=data.parent_id,
            org_id=data.org_id,
            leader_id=data.leader_id
        )
        self.session.add(new_team)
        self.session.commit()
        self.session.refresh(new_team)
        return new_team

    def add_team_member(self, team_id: int, data: schemas.TeamMemberCreate) -> bool:
        """添加团队成员。"""
        existing = self.session.query(TeamMember).filter(
            TeamMember.team_id == team_id, 
            TeamMember.user_id == data.user_id
        ).first()
        if existing:
            existing.role_code = data.role_code
            existing.allocation_ratio = data.allocation_ratio
        else:
            new_member = TeamMember(
                team_id=team_id,
                user_id=data.user_id,
                role_code=data.role_code,
                allocation_ratio=data.allocation_ratio
            )
            self.session.add(new_member)
        
        self.session.commit()
        return True

    def link_repo_to_mdm_project(self, mdm_project_id: str, gitlab_project_id: int, is_lead: bool = False) -> bool:
        """关联 GitLab 仓库到 MDM 项目。"""
        repo = self.session.query(GitLabProject).filter(GitLabProject.id == gitlab_project_id).first()
        mdm_p = self.session.query(ProjectMaster).filter(ProjectMaster.project_id == mdm_project_id).first()
        if not repo or not mdm_p:
            return False
        
        repo.mdm_project_id = mdm_p.project_id
        repo.organization_id = mdm_p.org_id
        if is_lead:
            mdm_p.lead_repo_id = repo.id
        self.session.commit()
        return True

    def list_products(self) -> List[Product]:
        """列出所有产品。"""
        return self.session.query(Product).all()

    def create_product(self, data: schemas.ProductCreate) -> Product:
        """创建新产品。"""
        new_product = Product(
            product_id=data.product_id,
            product_name=data.product_name,
            product_description=data.product_description,
            category=data.category,
            version_schema=data.version_schema,
            owner_team_id=data.owner_team_id,
            product_manager_id=data.product_manager_id
        )
        self.session.add(new_product)
        self.session.commit()
        self.session.refresh(new_product)
        return new_product

    def link_product_to_project(self, data: schemas.ProjectProductRelationCreate) -> ProjectProductRelation:
        """建立产品与项目的关联。"""
        project = self.session.query(ProjectMaster).filter(ProjectMaster.project_id == data.project_id).first()
        if not project:
            raise ValueError(f"Project {data.project_id} not found")
        
        org_id = project.org_id
        if not org_id:
            raise ValueError(f"Project {data.project_id} does not belong to any organization")

        relation = self.session.query(ProjectProductRelation).filter(
            ProjectProductRelation.project_id == data.project_id,
            ProjectProductRelation.product_id == data.product_id
        ).first()
        
        if relation:
            relation.relation_type = data.relation_type
            relation.allocation_ratio = data.allocation_ratio
            relation.org_id = org_id
        else:
            relation = ProjectProductRelation(
                project_id=data.project_id,
                product_id=data.product_id,
                relation_type=data.relation_type,
                allocation_ratio=data.allocation_ratio,
                org_id=org_id
            )
            self.session.add(relation)
        
        self.session.commit()
        self.session.refresh(relation)
        return relation

    def list_all_organizations(self) -> List[schemas.OrganizationView]:
        """列出所有组织架构（包含负责人和父级名称），按层级排序。"""
        orgs = self.session.query(Organization).options(
            joinedload(Organization.manager),
            joinedload(Organization.parent)
        ).filter(Organization.is_current == True).order_by(Organization.org_level.asc()).all()
        
        results = []
        for o in orgs:
            view = schemas.OrganizationView.model_validate(o)
            view.manager_name = o.manager.full_name if o.manager else None
            view.parent_name = o.parent.org_name if o.parent else None
            results.append(view)
        return results

    def create_organization(self, data: schemas.OrganizationCreate) -> Organization:
        """创建新的组织实体。"""
        new_org = Organization(
            org_id=data.org_id,
            org_name=data.org_name,
            org_level=data.org_level,
            parent_org_id=data.parent_org_id,
            manager_user_id=data.manager_user_id,
            cost_center=data.cost_center,
            is_active=data.is_active,
            is_current=True,
            sync_version=1
        )
        self.session.add(new_org)
        self.session.commit()
        self.session.refresh(new_org)
        return new_org

    def import_users(self, csv_content: str) -> schemas.ImportSummary:
        """从 CSV 字符串导入用户。"""
        f = io.StringIO(csv_content)
        reader = csv.DictReader(f)
        summary = schemas.ImportSummary(total_processed=0, success_count=0, failure_count=0)
        
        for row in reader:
            emp_id = row.get('工号') or row.get('employee_id')
            name = row.get('姓名') or row.get('full_name')
            email = row.get('邮箱') or row.get('email')
            
            # 跳过空行或缺少核心信息的记录
            if not any(row.values()) or (not emp_id and not name):
                continue
                
            summary.total_processed += 1
            try:
                dept_id = row.get('部门ID') or row.get('department_id')
                hr_rel = row.get('人事关系') or row.get('hr_relationship')
                
                if not emp_id or not name or not email:
                    raise ValueError("Missing mandatory fields: employee_id, full_name, or email")

                user = self.session.query(User).filter(User.employee_id == emp_id).first()
                if user:
                    user.full_name = name
                    user.primary_email = email
                    user.department_id = dept_id
                    user.hr_relationship = hr_rel
                    user.updated_at = datetime.now(timezone.utc)
                else:
                    user = User(
                        global_user_id=uuid.uuid4(),
                        employee_id=emp_id,
                        full_name=name,
                        primary_email=email,
                        department_id=dept_id,
                        hr_relationship=hr_rel,
                        is_active=True,
                        is_current=True,
                        sync_version=1
                    )
                    self.session.add(user)
                summary.success_count += 1
            except Exception as e:
                summary.failure_count += 1
                summary.errors.append({"row": summary.total_processed, "error": str(e)})

        self.session.commit()
        return summary

    def import_organizations(self, csv_content: str) -> schemas.ImportSummary:
        """从 CSV 字符串导入组织架构。"""
        f = io.StringIO(csv_content)
        reader = csv.DictReader(f)
        summary = schemas.ImportSummary(total_processed=0, success_count=0, failure_count=0)
        
        for row in reader:
            org_id = row.get('组织ID') or row.get('org_id')
            name = row.get('组织名称') or row.get('org_name')
            
            # 跳过空行
            if not any(row.values()) or (not org_id and not name):
                continue

            summary.total_processed += 1
            try:
                level = int(row.get('层级') or row.get('org_level') or 2)
                parent_id = row.get('上级ID') or row.get('parent_org_id')
                mgr_name = row.get('负责人') or row.get('manager_name')
                
                if not org_id or not name:
                    raise ValueError("Missing mandatory fields: org_id or org_name")

                # Lookup manager user ID by name with ambiguity check
                mgr_uid = None
                if mgr_name:
                    mgr_users = self.session.query(User).filter(User.full_name == mgr_name).all()
                    if not mgr_users:
                        # Optional: logger.warning(f"No user found with name {mgr_name}")
                        pass
                    elif len(mgr_users) > 1:
                        # Ambiguous match
                        summary.errors.append({
                            "row": summary.total_processed, 
                            "error": f"负责人 '{mgr_name}' 不唯一 (存在多名同名员工)，已跳过自动关联"
                        })
                    else:
                        mgr_uid = mgr_users[0].global_user_id

                org = self.session.query(Organization).filter(Organization.org_id == org_id).first()
                if org:
                    org.org_name = name
                    org.org_level = level
                    org.parent_org_id = parent_id
                    org.manager_user_id = mgr_uid
                    org.updated_at = datetime.now(timezone.utc)
                else:
                    org = Organization(
                        org_id=org_id,
                        org_name=name,
                        org_level=level,
                        parent_org_id=parent_id,
                        manager_user_id=mgr_uid,
                        is_active=True,
                        is_current=True,
                        sync_version=1
                    )
                    self.session.add(org)
                summary.success_count += 1
            except Exception as e:
                summary.failure_count += 1
                summary.errors.append({"row": summary.total_processed, "error": str(e)})

        self.session.commit()
        return summary

    def export_products(self) -> str:
        """导出所有产品数据为 CSV（包含层级与负责人映射）。"""
        products = self.session.query(Product).options(
            joinedload(Product.product_manager),
            joinedload(Product.parent)
        ).all()
        
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['product_id', 'product_name', 'node_type', 'parent_product_id', 
                         'category', 'version_schema', 'owner_team_id', 'pm_email'])
        
        for p in products:
            pm_email = p.product_manager.primary_email if p.product_manager else ''
            writer.writerow([
                p.product_id, p.product_name, p.node_type, p.parent_product_id,
                p.category, p.version_schema, p.owner_team_id, pm_email
            ])
        return output.getvalue()

    def import_products(self, csv_content: str) -> schemas.ImportSummary:
        """从 CSV 导入产品树。支持两阶段提交以解决层级依赖。"""
        f = io.StringIO(csv_content)
        reader = list(csv.DictReader(f))
        summary = schemas.ImportSummary(total_processed=0, success_count=0, failure_count=0)
        
        # 阶段1：先创建所有节点（暂不设 parent_id），确保 ID 存在
        # 阶段2：更新 parent_id 关系
        
        # 预加载所有用户邮箱映射以减少查询
        user_map = {u.primary_email: u for u in self.session.query(User).filter(User.is_current == True).all()}
        
        for phase in [1, 2]:
            for row in reader:
                if phase == 1:
                    summary.total_processed += 1
                    
                pid = row.get('product_id')
                name = row.get('product_name')
                
                if not pid or not name:
                    if phase == 1:
                        summary.failure_count += 1
                        summary.errors.append({"row": summary.total_processed, "error": "Missing product_id or product_name"})
                    continue

                try:
                    product = self.session.query(Product).filter(Product.product_id == pid).first()
                    
                    if phase == 1:
                        # 基础信息 Upsert
                        pm_email = row.get('pm_email')
                        pm_uid = user_map.get(pm_email).global_user_id if pm_email and pm_email in user_map else None
                        
                        if not product:
                            product = Product(product_id=pid)
                            self.session.add(product)
                        
                        product.product_name = name
                        product.node_type = row.get('node_type', 'APP')
                        product.category = row.get('category')
                        product.version_schema = row.get('version_schema', 'SemVer')
                        product.owner_team_id = row.get('owner_team_id')
                        product.product_manager_id = pm_uid
                        product.updated_at = datetime.now(timezone.utc)
                        
                    elif phase == 2 and product:
                        # 关系链接
                        parent_id = row.get('parent_product_id')
                        if parent_id:
                            # 校验父节点是否存在
                            if self.session.query(Product).filter(Product.product_id == parent_id).count() > 0:
                                product.parent_product_id = parent_id
                
                except Exception as e:
                    if phase == 1:
                        summary.failure_count += 1
                        summary.errors.append({"row": summary.total_processed, "error": str(e)})

            # 阶段提交
            self.session.flush()
        
        self.session.commit()
        # 修正计数逻辑：phase 2 不累计
        summary.success_count = summary.total_processed - summary.failure_count
        return summary

    def export_product_mappings(self) -> str:
        """导出产品-项目关联矩阵。"""
        relations = self.session.query(ProjectProductRelation).options(
            joinedload(ProjectProductRelation.project),
            joinedload(ProjectProductRelation.product)
        ).all()
        
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['project_id', 'project_name', 'product_id', 'product_name', 'relation_type', 'allocation_ratio'])
        
        for r in relations:
            writer.writerow([
                r.project_id, 
                r.project.project_name if r.project else 'Unknown',
                r.product_id, 
                r.product.product_name if r.product else 'Unknown',
                r.relation_type, 
                r.allocation_ratio
            ])
        return output.getvalue()

    def import_product_mappings(self, csv_content: str) -> schemas.ImportSummary:
        """从 CSV 导入项目-产品关联。"""
        f = io.StringIO(csv_content)
        reader = csv.DictReader(f)
        summary = schemas.ImportSummary(total_processed=0, success_count=0, failure_count=0)
        
        for row in reader:
            summary.total_processed += 1
            proj_id = row.get('project_id')
            prod_id = row.get('product_id')
            
            if not proj_id or not prod_id:
                summary.failure_count += 1
                continue
                
            try:
                # 校验实体存在性
                project = self.session.query(ProjectMaster).filter(ProjectMaster.project_id == proj_id).first()
                if not project:
                    raise ValueError(f"Project {proj_id} not found")
                    
                # 查找或创建关联
                rel = self.session.query(ProjectProductRelation).filter(
                    ProjectProductRelation.project_id == proj_id,
                    ProjectProductRelation.product_id == prod_id
                ).first()
                
                if not rel:
                    rel = ProjectProductRelation(project_id=proj_id, product_id=prod_id)
                    self.session.add(rel)
                
                rel.relation_type = row.get('relation_type', 'PRIMARY')
                rel.allocation_ratio = float(row.get('allocation_ratio', 1.0))
                rel.org_id = project.org_id  # 继承项目组织
                
                summary.success_count += 1
            except Exception as e:
                summary.failure_count += 1
                summary.errors.append({"row": summary.total_processed, "error": str(e)})

        self.session.commit()
        return summary
