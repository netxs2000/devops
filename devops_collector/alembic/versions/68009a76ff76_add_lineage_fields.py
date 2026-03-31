"""Add lineage fields

Revision ID: 68009a76ff76
Revises: b1cf984c9cd9
Create Date: 2026-03-31 06:25:59.045168

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '68009a76ff76'
down_revision: Union[str, None] = 'b1cf984c9cd9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # mdm_organizations
    op.add_column('mdm_organizations', sa.Column('source_system', sa.String(length=50), nullable=True))
    op.add_column('mdm_organizations', sa.Column('correlation_id', sa.String(length=100), nullable=True))
    op.create_index(op.f('ix_mdm_organizations_correlation_id'), 'mdm_organizations', ['correlation_id'], unique=False)

    # mdm_identities (User)
    op.add_column('mdm_identities', sa.Column('source_system', sa.String(length=50), nullable=True))
    op.add_column('mdm_identities', sa.Column('correlation_id', sa.String(length=100), nullable=True))
    op.create_index(op.f('ix_mdm_identities_correlation_id'), 'mdm_identities', ['correlation_id'], unique=False)



def downgrade() -> None:
    """Downgrade schema."""
    # mdm_identities
    op.drop_index(op.f('ix_mdm_identities_correlation_id'), table_name='mdm_identities')
    op.drop_column('mdm_identities', 'correlation_id')
    op.drop_column('mdm_identities', 'source_system')

    # mdm_organizations
    op.drop_index(op.f('ix_mdm_organizations_correlation_id'), table_name='mdm_organizations')
    op.drop_column('mdm_organizations', 'correlation_id')
    op.drop_column('mdm_organizations', 'source_system')

