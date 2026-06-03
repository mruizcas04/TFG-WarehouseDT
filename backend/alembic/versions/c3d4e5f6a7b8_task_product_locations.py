"""task product and location fields

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-05-13 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('tasks', sa.Column('product_id', UUID(as_uuid=True), sa.ForeignKey('products.id'), nullable=True))
    op.add_column('tasks', sa.Column('origin_location_id', UUID(as_uuid=True), sa.ForeignKey('locations.id'), nullable=True))
    op.add_column('tasks', sa.Column('destination_location_id', UUID(as_uuid=True), sa.ForeignKey('locations.id'), nullable=True))


def downgrade() -> None:
    op.drop_column('tasks', 'destination_location_id')
    op.drop_column('tasks', 'origin_location_id')
    op.drop_column('tasks', 'product_id')
