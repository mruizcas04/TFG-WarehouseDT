"""add last_login to users and completed_at to tasks

Revision ID: l7a8b9c0d1e2
Revises: k6f7a8b9c0d1
Create Date: 2026-05-24 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'l7a8b9c0d1e2'
down_revision: Union[str, Sequence[str], None] = 'k6f7a8b9c0d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('last_login', sa.DateTime(), nullable=True))
    op.add_column('tasks', sa.Column('completed_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('tasks', 'completed_at')
    op.drop_column('users', 'last_login')
