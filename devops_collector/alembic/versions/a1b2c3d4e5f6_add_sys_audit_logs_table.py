"""add sys_audit_logs table

Revision ID: a1b2c3d4e5f6
Revises: 68009a76ff76
Create Date: 2026-04-03 10:50:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "68009a76ff76"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sys_audit_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="审计记录ID"),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=True, comment="物理操作发生时间"),
        sa.Column("actor_id", sa.UUID(as_uuid=True), nullable=True, comment="操作者全局唯一标识"),
        sa.Column("actor_name", sa.String(length=200), nullable=True, comment="操作者姓名快照"),
        sa.Column("client_ip", sa.String(length=50), nullable=True, comment="来源IP地址"),
        sa.Column("action", sa.String(length=50), nullable=False, comment="动作类型"),
        sa.Column("resource_type", sa.String(length=50), nullable=True, comment="操作对象类型"),
        sa.Column("resource_id", sa.String(length=100), nullable=True, comment="操作对象实例ID"),
        sa.Column("changes", sa.JSON(), nullable=True, comment="字段级变更增量Diff"),
        sa.Column("request_id", sa.String(length=100), nullable=True, comment="关联请求追踪ID"),
        sa.Column("correlation_id", sa.String(length=100), nullable=True, comment="业务关联ID"),
        sa.Column("status", sa.String(length=20), nullable=True, comment="操作执行状态"),
        sa.Column("remark", sa.Text(), nullable=True, comment="详细备注或报错信息"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sys_audit_logs_timestamp", "sys_audit_logs", ["timestamp"])
    op.create_index("ix_sys_audit_logs_actor_id", "sys_audit_logs", ["actor_id"])
    op.create_index("ix_sys_audit_logs_action", "sys_audit_logs", ["action"])
    op.create_index("ix_sys_audit_logs_resource_type", "sys_audit_logs", ["resource_type"])
    op.create_index("ix_sys_audit_logs_resource_id", "sys_audit_logs", ["resource_id"])
    op.create_index("ix_sys_audit_logs_request_id", "sys_audit_logs", ["request_id"])
    op.create_index("ix_sys_audit_logs_correlation_id", "sys_audit_logs", ["correlation_id"])
    op.create_index("ix_sys_audit_logs_status", "sys_audit_logs", ["status"])


def downgrade() -> None:
    op.drop_index("ix_sys_audit_logs_status", table_name="sys_audit_logs")
    op.drop_index("ix_sys_audit_logs_correlation_id", table_name="sys_audit_logs")
    op.drop_index("ix_sys_audit_logs_request_id", table_name="sys_audit_logs")
    op.drop_index("ix_sys_audit_logs_resource_id", table_name="sys_audit_logs")
    op.drop_index("ix_sys_audit_logs_resource_type", table_name="sys_audit_logs")
    op.drop_index("ix_sys_audit_logs_action", table_name="sys_audit_logs")
    op.drop_index("ix_sys_audit_logs_actor_id", table_name="sys_audit_logs")
    op.drop_index("ix_sys_audit_logs_timestamp", table_name="sys_audit_logs")
    op.drop_table("sys_audit_logs")
