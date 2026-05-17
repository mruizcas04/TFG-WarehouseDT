"""box support in tasks and movements

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-05-14 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, Sequence[str], None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('tasks', sa.Column('box_id', UUID(as_uuid=True), sa.ForeignKey('boxes.id'), nullable=True))
    op.add_column('tasks', sa.Column('quantity', sa.Integer(), nullable=True))
    op.add_column('movements', sa.Column('quantity', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('tasks', 'box_id')
    op.drop_column('tasks', 'quantity')
    op.drop_column('movements', 'quantity')
