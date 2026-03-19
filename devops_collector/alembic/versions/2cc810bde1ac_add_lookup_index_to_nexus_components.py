"""add lookup index to nexus_components

Revision ID: 2cc810bde1ac
Revises: 6fcea0da41c5
Create Date: 2026-03-14 13:30:53.104225

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "2cc810bde1ac"
down_revision: Union[str, None] = "6fcea0da41c5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index("ix_nexus_components_lookup", "nexus_components", ["repository", "group", "name"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_nexus_components_lookup", table_name="nexus_components")
