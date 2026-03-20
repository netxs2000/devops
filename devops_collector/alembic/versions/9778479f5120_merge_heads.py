"""merge heads

Revision ID: 9778479f5120
Revises: 2cc810bde1ac, f1e2d3c4b5a6
Create Date: 2026-03-16 06:40:53.454251

"""

from collections.abc import Sequence


# revision identifiers, used by Alembic.
revision: str = "9778479f5120"
down_revision: str | None = ("2cc810bde1ac", "f1e2d3c4b5a6")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
