"""系统管理核心业务服务层。

该模块封装了“系统管理模块”的核心业务逻辑，包括：
1. 用户全景画像聚合
2. 虚拟团队与成员管理
3. 业务主项目 (MDM) 与仓库关联管理
"""
import logging
import uuid
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from devops_collector.models.base_models import Organization, User, ProjectMaster, IdentityMapping, Team, TeamMember, UserRole
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
            global_user_id=str(user.global_user_id),
            full_name=user.full_name,
            username=user.username,
            primary_email=user.primary_email,
            employee_id=user.employee_id,
            department_name=user.department.org_name if user.department else None,
            is_active=user.is_active,
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
