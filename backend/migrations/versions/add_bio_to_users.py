"""Add bio to users

Revision ID: add_bio_to_users
Revises: make_username_nullable
Create Date: 2025-01-XX

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'add_bio_to_users'
down_revision: Union[str, Sequence[str], None] = 'make_username_nullable'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add bio column to users table."""
    op.add_column('users', sa.Column('bio', sa.String(length=500), nullable=True))


def downgrade() -> None:
    """Remove bio column from users table."""
    op.drop_column('users', 'bio')

