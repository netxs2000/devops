"""rename mdm_product to mdm_products and add SCD composite indexes

Revision ID: a1b2c3d4e5f6
Revises: c7cdb0fad960
Create Date: 2026-03-16 14:12:00.000000

"""

from collections.abc import Sequence

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "c7cdb0fad960"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Rename mdm_product -> mdm_products and add composite indexes for SCD lookups."""
    # 1. 表重命名
    op.rename_table("mdm_product", "mdm_products")

    # 2. 添加 SCD 复合索引 (business_id, is_current)
    op.create_index("idx_mdm_org_active_lookup", "mdm_organizations", ["org_id", "is_current"])
    op.create_index("idx_mdm_user_active_lookup", "mdm_identities", ["employee_id", "is_current"])
    op.create_index("idx_mdm_user_email_lookup", "mdm_identities", ["primary_email", "is_current"])
    op.create_index("idx_mdm_team_active_lookup", "sys_teams", ["team_code", "is_current"])
    op.create_index("idx_mdm_product_active_lookup", "mdm_products", ["product_id", "is_current"])
    op.create_index("idx_mdm_project_active_lookup", "mdm_projects", ["project_id", "is_current"])


def downgrade() -> None:
    """Revert: drop composite indexes and rename table back."""
    # 1. 移除复合索引
    op.drop_index("idx_mdm_project_active_lookup", table_name="mdm_projects")
    op.drop_index("idx_mdm_product_active_lookup", table_name="mdm_products")
    op.drop_index("idx_mdm_team_active_lookup", table_name="sys_teams")
    op.drop_index("idx_mdm_user_email_lookup", table_name="mdm_identities")
    op.drop_index("idx_mdm_user_active_lookup", table_name="mdm_identities")
    op.drop_index("idx_mdm_org_active_lookup", table_name="mdm_organizations")

    # 2. 表重命名回退
    op.rename_table("mdm_products", "mdm_product")
