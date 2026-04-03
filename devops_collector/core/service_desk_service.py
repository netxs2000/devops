"""Service Desk Core Service.

封装服务工单、业务线拉取以及其他需要直接操作主数据的服务台逻辑。
"""

import logging

from sqlalchemy.orm import Session

from devops_collector.models.base_models import (
    IdentityMapping,
    Product,
    ProjectMaster,
    ProjectProductRelation,
    User,
)


logger = logging.getLogger(__name__)


class ServiceDeskCoreService:
    """处理服务台路由底下的核心数据库逻辑。"""

    def __init__(self, session: Session):
        self.session = session

    def list_business_projects(self) -> list[dict]:
        """获取所有已关联受理仓库的产品/业务线。如果无，则兜底返回所有产品。"""
        # 查找所有已建立关联且项目有受理仓库的产品
        products = (
            self.session.query(Product)
            .join(ProjectProductRelation, Product.id == ProjectProductRelation.product_id)
            .join(ProjectMaster, ProjectProductRelation.project_id == ProjectMaster.id)
            .filter(Product.is_current.is_(True), ProjectMaster.is_current.is_(True), ProjectMaster.lead_repo_id.is_not(None))
            .distinct()
            .all()
        )

        if not products:
            products = self.session.query(Product).filter(Product.is_current.is_(True)).all()
            return [{"id": p.product_code, "name": p.product_name, "description": p.product_description, "status": "no_lead"} for p in products]

        return [{"id": p.product_code, "name": p.product_name, "description": p.product_description} for p in products]

    def get_lead_repo_for_project(self, project_code: str) -> int | None:
        """根据原有的直接项目代码获取主仓库。"""
        mdm_p = self.session.query(ProjectMaster).filter(ProjectMaster.project_code == project_code).first()
        if not mdm_p:
            return None
        return mdm_p.lead_repo_id

    def get_lead_repo_for_product(self, product_code: str) -> ProjectMaster | None:
        """根据产品代码获取归属项目及其受理中心仓库。"""
        mdm_p = (
            self.session.query(ProjectMaster)
            .join(ProjectProductRelation, ProjectMaster.id == ProjectProductRelation.project_id)
            .join(Product, ProjectProductRelation.product_id == Product.id)
            .filter(
                Product.product_code == product_code,
                ProjectMaster.lead_repo_id.is_not(None),
                ProjectMaster.is_current.is_(True),
            )
            .first()
        )
        return mdm_p

    def list_all_users_for_admin(self, status: str | None = None) -> dict:
        """[管理后台] 获取所有用户申请记录及统计信息。"""
        query = self.session.query(User).filter(User.is_current)
        if status == "pending":
            query = query.filter(User.is_active.is_(False), User.is_survivor.is_(True))
        elif status == "approved":
            query = query.filter(User.is_active.is_(True))
        elif status == "rejected":
            query = query.filter(User.is_active.is_(False), User.is_survivor.is_(False))

        users = query.all()

        total = self.session.query(User).filter(User.is_current).count()
        pending = self.session.query(User).filter(User.is_current, User.is_active.is_(False), User.is_survivor.is_(True)).count()
        approved = self.session.query(User).filter(User.is_current, User.is_active.is_(True)).count()
        rejected = self.session.query(User).filter(User.is_current, User.is_active.is_(False), User.is_survivor.is_(False)).count()

        results = []
        for u in users:
            u_status = "approved" if u.is_active else ("pending" if u.is_survivor else "rejected")
            gitlab_mapping = (
                self.session.query(IdentityMapping)
                .filter(IdentityMapping.global_user_id == u.global_user_id, IdentityMapping.source_system == "gitlab")
                .first()
            )

            results.append(
                {
                    "name": u.full_name,
                    "email": u.primary_email,
                    "company": u.department.org_name if u.department else "未知",
                    "created_at": u.created_at.isoformat(),
                    "status": u_status,
                    "gitlab_user_id": gitlab_mapping.external_user_id if gitlab_mapping else None,
                }
            )

        return {"stats": {"total": total, "pending": pending, "approved": approved, "rejected": rejected}, "users": results}

    def approve_user_application(self, email: str, approved: bool, gitlab_user_id: str | None = None) -> bool:
        """[管理后台] 审批用户申请并绑定身份标识。"""
        user = self.session.query(User).filter(User.primary_email == email, User.is_current).first()
        if not user:
            return False

        if approved:
            user.is_active = True
            user.is_survivor = True
            if gitlab_user_id:
                mapping = (
                    self.session.query(IdentityMapping)
                    .filter(IdentityMapping.global_user_id == user.global_user_id, IdentityMapping.source_system == "gitlab")
                    .first()
                )
                if mapping:
                    mapping.external_user_id = gitlab_user_id
                    mapping.mapping_status = "VERIFIED"
                else:
                    mapping = IdentityMapping(
                        global_user_id=user.global_user_id,
                        source_system="gitlab",
                        external_user_id=gitlab_user_id,
                        mapping_status="VERIFIED",
                    )
                    self.session.add(mapping)
        else:
            user.is_active = False
            user.is_survivor = False

        self.session.commit()
        return True
