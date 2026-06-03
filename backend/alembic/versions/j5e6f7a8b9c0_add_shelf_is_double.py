"""add is_double to shelves

Revision ID: j5e6f7a8b9c0
Revises: i4d5e6f7a8b9
Create Date: 2026-05-22 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'j5e6f7a8b9c0'
down_revision: Union[str, Sequence[str], None] = 'i4d5e6f7a8b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('shelves', sa.Column('is_double', sa.Boolean(), nullable=False, server_default='false'))


def downgrade() -> None:
    op.drop_column('shelves', 'is_double')
