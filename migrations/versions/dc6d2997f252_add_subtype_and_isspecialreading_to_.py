"""Add multi-tenancy, soft delete, and ID reuse system

Revision ID: dc6d2997f252
Revises: 82b4088122eb
Create Date: 2025-10-01 21:25:52.146131

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dc6d2997f252'
down_revision: Union[str, None] = '82b4088122eb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create free_ids table for ID reuse
    op.create_table('free_ids',
        sa.Column('table_name', sa.String(), nullable=False),
        sa.Column('freed_id', sa.Integer(), nullable=False),
        sa.Column('freed_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('table_name', 'freed_id')
    )

    # Add subtype column to utility_readings table (from previous migration)
    op.add_column('utility_readings', sa.Column('subtype', sa.String(), nullable=True))

    # Add isSpecialReading column to utility_readings table (from previous migration)
    op.add_column('utility_readings', sa.Column('isSpecialReading', sa.Boolean(), nullable=True, default=False))

    # Add user_id and deleted_at to users table
    op.add_column('users', sa.Column('deletedAt', sa.DateTime(), nullable=True))

    # Add user_id and deleted_at to apartments table
    op.add_column('apartments', sa.Column('userId', sa.Integer(), nullable=False))
    op.add_column('apartments', sa.Column('deletedAt', sa.DateTime(), nullable=True))
    op.create_foreign_key(None, 'apartments', 'users', ['userId'], ['id'])

    # Add user_id and deleted_at to maintenance_records table
    op.add_column('maintenance_records', sa.Column('userId', sa.Integer(), nullable=False))
    op.add_column('maintenance_records', sa.Column('deletedAt', sa.DateTime(), nullable=True))
    op.create_foreign_key(None, 'maintenance_records', 'users', ['userId'], ['id'])

    # Add user_id and deleted_at to tenants table
    op.add_column('tenants', sa.Column('userId', sa.Integer(), nullable=False))
    op.add_column('tenants', sa.Column('deletedAt', sa.DateTime(), nullable=True))
    op.create_foreign_key(None, 'tenants', 'users', ['userId'], ['id'])

    # Add user_id and deleted_at to leases table
    op.add_column('leases', sa.Column('userId', sa.Integer(), nullable=False))
    op.add_column('leases', sa.Column('deletedAt', sa.DateTime(), nullable=True))
    op.create_foreign_key(None, 'leases', 'users', ['userId'], ['id'])

    # Add user_id and deleted_at to invoices table
    op.add_column('invoices', sa.Column('userId', sa.Integer(), nullable=False))
    op.add_column('invoices', sa.Column('deletedAt', sa.DateTime(), nullable=True))
    op.create_foreign_key(None, 'invoices', 'users', ['userId'], ['id'])

    # Add user_id and deleted_at to utility_readings table
    op.add_column('utility_readings', sa.Column('userId', sa.Integer(), nullable=False))
    op.add_column('utility_readings', sa.Column('deletedAt', sa.DateTime(), nullable=True))
    op.create_foreign_key(None, 'utility_readings', 'users', ['userId'], ['id'])

    # Add user_id and deleted_at to lease_documents table
    op.add_column('lease_documents', sa.Column('userId', sa.Integer(), nullable=False))
    op.add_column('lease_documents', sa.Column('deletedAt', sa.DateTime(), nullable=True))
    op.create_foreign_key(None, 'lease_documents', 'users', ['userId'], ['id'])

    # Add user_id and deleted_at to lease_payments table
    op.add_column('lease_payments', sa.Column('userId', sa.Integer(), nullable=False))
    op.add_column('lease_payments', sa.Column('deletedAt', sa.DateTime(), nullable=True))
    op.create_foreign_key(None, 'lease_payments', 'users', ['userId'], ['id'])

    # Add user_id and deleted_at to invoice_items table
    op.add_column('invoice_items', sa.Column('userId', sa.Integer(), nullable=False))
    op.add_column('invoice_items', sa.Column('deletedAt', sa.DateTime(), nullable=True))
    op.create_foreign_key(None, 'invoice_items', 'users', ['userId'], ['id'])

    # Add user_id and deleted_at to payment_records table
    op.add_column('payment_records', sa.Column('userId', sa.Integer(), nullable=False))
    op.add_column('payment_records', sa.Column('deletedAt', sa.DateTime(), nullable=True))
    op.create_foreign_key(None, 'payment_records', 'users', ['userId'], ['id'])

    # Add user_id and deleted_at to billing_defaults table
    op.add_column('billing_defaults', sa.Column('userId', sa.Integer(), nullable=False))
    op.add_column('billing_defaults', sa.Column('deletedAt', sa.DateTime(), nullable=True))
    op.create_foreign_key(None, 'billing_defaults', 'users', ['userId'], ['id'])


def downgrade() -> None:
    # Remove foreign keys and columns in reverse order

    # Remove isSpecialReading and subtype columns (from previous migration)
    op.drop_column('utility_readings', 'isSpecialReading')
    op.drop_column('utility_readings', 'subtype')

    op.drop_constraint(None, 'billing_defaults', type_='foreignkey')
    op.drop_column('billing_defaults', 'deletedAt')
    op.drop_column('billing_defaults', 'userId')

    op.drop_constraint(None, 'payment_records', type_='foreignkey')
    op.drop_column('payment_records', 'deletedAt')
    op.drop_column('payment_records', 'userId')

    op.drop_constraint(None, 'invoice_items', type_='foreignkey')
    op.drop_column('invoice_items', 'deletedAt')
    op.drop_column('invoice_items', 'userId')

    op.drop_constraint(None, 'lease_payments', type_='foreignkey')
    op.drop_column('lease_payments', 'deletedAt')
    op.drop_column('lease_payments', 'userId')

    op.drop_constraint(None, 'lease_documents', type_='foreignkey')
    op.drop_column('lease_documents', 'deletedAt')
    op.drop_column('lease_documents', 'userId')

    op.drop_constraint(None, 'utility_readings', type_='foreignkey')
    op.drop_column('utility_readings', 'deletedAt')
    op.drop_column('utility_readings', 'userId')

    op.drop_constraint(None, 'invoices', type_='foreignkey')
    op.drop_column('invoices', 'deletedAt')
    op.drop_column('invoices', 'userId')

    op.drop_constraint(None, 'leases', type_='foreignkey')
    op.drop_column('leases', 'deletedAt')
    op.drop_column('leases', 'userId')

    op.drop_constraint(None, 'tenants', type_='foreignkey')
    op.drop_column('tenants', 'deletedAt')
    op.drop_column('tenants', 'userId')

    op.drop_constraint(None, 'maintenance_records', type_='foreignkey')
    op.drop_column('maintenance_records', 'deletedAt')
    op.drop_column('maintenance_records', 'userId')

    op.drop_constraint(None, 'apartments', type_='foreignkey')
    op.drop_column('apartments', 'deletedAt')
    op.drop_column('apartments', 'userId')

    op.drop_column('users', 'deletedAt')

    # Drop free_ids table
    op.drop_table('free_ids')
