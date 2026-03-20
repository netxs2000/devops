"""add commit_sha to nexus_components

Revision ID: 6fcea0da41c5
Revises: c7cdb0fad960
Create Date: 2026-03-14 13:17:43.356720

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "6fcea0da41c5"
down_revision: str | None = "c7cdb0fad960"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("nexus_components", sa.Column("commit_sha", sa.String(length=100), nullable=True))
    op.create_index(op.f("ix_nexus_components_commit_sha"), "nexus_components", ["commit_sha"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_nexus_components_commit_sha"), table_name="nexus_components")
    op.drop_column("nexus_components", "commit_sha")
