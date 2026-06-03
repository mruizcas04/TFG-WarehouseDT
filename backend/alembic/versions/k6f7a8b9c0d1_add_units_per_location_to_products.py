"""add units_per_location to products

Revision ID: k6f7a8b9c0d1
Revises: j5e6f7a8b9c0
Create Date: 2026-05-23 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'k6f7a8b9c0d1'
down_revision: Union[str, Sequence[str], None] = 'j5e6f7a8b9c0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('products', sa.Column('units_per_location', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('products', 'units_per_location')
