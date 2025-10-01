"""Add subtype and isSpecialReading to utility_readings

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
    # Add subtype column to utility_readings table
    op.add_column('utility_readings', sa.Column('subtype', sa.String(), nullable=True))
    
    # Add isSpecialReading column to utility_readings table
    op.add_column('utility_readings', sa.Column('isSpecialReading', sa.Boolean(), nullable=True, default=False))


def downgrade() -> None:
    # Remove isSpecialReading column
    op.drop_column('utility_readings', 'isSpecialReading')
    
    # Remove subtype column
    op.drop_column('utility_readings', 'subtype')
