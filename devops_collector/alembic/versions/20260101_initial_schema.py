"""Initial schema with surrogate PK and SCD Type2 fields

Revision ID: 20260101_initial_schema
Revises: 
Create Date: 2026-01-01 17:30:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
revision = '20260101_initial_schema'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    """Create all tables required by the current model.
    This includes Organization and User (mdm_identities) with
    surrogate primary keys, SCD Type2 columns and removal of the
    original unique constraints.
    """
    op.create_table('mdm_organizations', sa.Column('id', sa.Integer, primary_key=True, autoincrement=True), sa.Column('org_id', sa.String(length=100), nullable=False), sa.Column('org_name', sa.String(length=200), nullable=False), sa.Column('parent_org_id', sa.String(length=100), sa.ForeignKey('mdm_organizations.org_id'), nullable=True), sa.Column('org_level', sa.Integer, nullable=True), sa.Column('manager_user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('mdm_identities.global_user_id'), nullable=True), sa.Column('cost_center', sa.String(length=100), nullable=True), sa.Column('sync_version', sa.BigInteger, nullable=False, server_default='1'), sa.Column('is_deleted', sa.Boolean, nullable=False, server_default=sa.text('false')), sa.Column('effective_from', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')), sa.Column('effective_to', sa.DateTime(timezone=True), nullable=True), sa.Column('is_current', sa.Boolean, nullable=False, server_default=sa.text('true')), sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')), sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True, onupdate=sa.text('NOW()')))
    op.create_table('mdm_identities', sa.Column('id', sa.Integer, primary_key=True, autoincrement=True), sa.Column('global_user_id', postgresql.UUID(as_uuid=True), nullable=False), sa.Column('employee_id', sa.String(length=50), nullable=True, unique=True), sa.Column('full_name', sa.String(length=200), nullable=False), sa.Column('primary_email', sa.String(length=200), nullable=True, unique=True), sa.Column('identity_map', postgresql.JSONB, nullable=True), sa.Column('match_confidence', sa.Float, nullable=True), sa.Column('is_survivor', sa.Boolean, nullable=False, server_default=sa.text('true')), sa.Column('is_active', sa.Boolean, nullable=False, server_default=sa.text('true')), sa.Column('sync_version', sa.BigInteger, nullable=False, server_default='1'), sa.Column('is_deleted', sa.Boolean, nullable=False, server_default=sa.text('false')), sa.Column('effective_from', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')), sa.Column('effective_to', sa.DateTime(timezone=True), nullable=True), sa.Column('is_current', sa.Boolean, nullable=False, server_default=sa.text('true')), sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')), sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True, onupdate=sa.text('NOW()')), sa.Column('source_system', sa.String(length=50), nullable=True), sa.Column('department_id', sa.String(length=100), sa.ForeignKey('mdm_organizations.org_id'), nullable=True), sa.Column('location_id', sa.String(length=6), sa.ForeignKey('mdm_location.location_id'), nullable=True))

def downgrade() -> None:
    """Drop the tables created in upgrade()."""
    op.drop_table('mdm_identities')
    op.drop_table('mdm_organizations')