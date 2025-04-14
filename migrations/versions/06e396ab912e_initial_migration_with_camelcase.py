"""Initial migration with camelCase

Revision ID: 06e396ab912e
Revises: 
Create Date: 2024-03-21 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from datetime import datetime


# revision identifiers, used by Alembic.
revision: str = '06e396ab912e'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('hashedPassword', sa.String(), nullable=False),
        sa.Column('firstName', sa.String(), nullable=False),
        sa.Column('lastName', sa.String(), nullable=False),
        sa.Column('role', sa.String(), nullable=False),
        sa.Column('isActive', sa.Boolean(), nullable=False, default=True),
        sa.Column('lastLogin', sa.DateTime(), nullable=True),
        sa.Column('createdAt', sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.Column('updatedAt', sa.DateTime(), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('username'),
        sa.UniqueConstraint('email')
    )
    
    # Create refresh_tokens table
    op.create_table(
        'refresh_tokens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('token', sa.String(), nullable=False),
        sa.Column('username', sa.String(), nullable=False),
        sa.Column('expires', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('is_revoked', sa.Boolean(), nullable=False, default=False),
        sa.Column('revoked_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token'),
        sa.ForeignKeyConstraint(['username'], ['users.username'])
    )


def downgrade() -> None:
    op.drop_table('refresh_tokens')
    op.drop_table('users')
