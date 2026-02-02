"""remove_product_code_column

Revision ID: c7cdb0fad960
Revises: 15670218bb0d
Create Date: 2026-02-02 18:27:18.363050

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c7cdb0fad960'
down_revision: Union[str, None] = '15670218bb0d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 删除 product_code 列
    op.drop_column('mdm_product', 'product_code')


def downgrade() -> None:
    """Downgrade schema."""
    # 回滚：重新添加 product_code 列（数据会丢失）
    op.add_column('mdm_product', 
        sa.Column('product_code', sa.String(25), nullable=True)
    )
    # 注意：原有的 NOT NULL 约束和索引不会自动恢复
