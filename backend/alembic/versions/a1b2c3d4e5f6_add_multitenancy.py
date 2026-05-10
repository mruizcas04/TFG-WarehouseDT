"""add multitenancy

Revision ID: a1b2c3d4e5f6
Revises: 6b2a69ef9e2d
Create Date: 2026-05-09 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '6b2a69ef9e2d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Tabla companies
    op.create_table(
        'companies',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # company_id en users
    op.add_column('users', sa.Column('company_id', sa.UUID(), nullable=True))
    op.create_foreign_key(
        'fk_users_company_id', 'users', 'companies', ['company_id'], ['id']
    )

    # company_id en warehouses
    op.add_column('warehouses', sa.Column('company_id', sa.UUID(), nullable=True))
    op.create_foreign_key(
        'fk_warehouses_company_id', 'warehouses', 'companies', ['company_id'], ['id']
    )

    # company_id en products + reemplazar unique(barcode) por unique(company_id, barcode)
    op.add_column('products', sa.Column('company_id', sa.UUID(), nullable=True))
    op.create_foreign_key(
        'fk_products_company_id', 'products', 'companies', ['company_id'], ['id']
    )
    op.drop_constraint('products_barcode_key', 'products', type_='unique')
    op.create_unique_constraint(
        'uq_product_company_barcode', 'products', ['company_id', 'barcode']
    )

    # company_id en boxes
    op.add_column('boxes', sa.Column('company_id', sa.UUID(), nullable=True))
    op.create_foreign_key(
        'fk_boxes_company_id', 'boxes', 'companies', ['company_id'], ['id']
    )

    # company_id en tasks
    op.add_column('tasks', sa.Column('company_id', sa.UUID(), nullable=True))
    op.create_foreign_key(
        'fk_tasks_company_id', 'tasks', 'companies', ['company_id'], ['id']
    )

    # company_id en movements
    op.add_column('movements', sa.Column('company_id', sa.UUID(), nullable=True))
    op.create_foreign_key(
        'fk_movements_company_id', 'movements', 'companies', ['company_id'], ['id']
    )


def downgrade() -> None:
    op.drop_constraint('fk_movements_company_id', 'movements', type_='foreignkey')
    op.drop_column('movements', 'company_id')

    op.drop_constraint('fk_tasks_company_id', 'tasks', type_='foreignkey')
    op.drop_column('tasks', 'company_id')

    op.drop_constraint('fk_boxes_company_id', 'boxes', type_='foreignkey')
    op.drop_column('boxes', 'company_id')

    op.drop_constraint('uq_product_company_barcode', 'products', type_='unique')
    op.create_unique_constraint('products_barcode_key', 'products', ['barcode'])
    op.drop_constraint('fk_products_company_id', 'products', type_='foreignkey')
    op.drop_column('products', 'company_id')

    op.drop_constraint('fk_warehouses_company_id', 'warehouses', type_='foreignkey')
    op.drop_column('warehouses', 'company_id')

    op.drop_constraint('fk_users_company_id', 'users', type_='foreignkey')
    op.drop_column('users', 'company_id')

    op.drop_table('companies')
