"""Add photo_urls to posts

Revision ID: f8a9b2c3d4e5
Revises: add_email_verification
Create Date: 2025-01-15 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'f8a9b2c3d4e5'
down_revision: Union[str, Sequence[str], None] = 'add_email_verification'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add photo_urls column as JSON (or JSONB for PostgreSQL)
    # Using JSON type which works for both PostgreSQL and SQLite
    # Allow nullable - application will default to empty list
    op.add_column('posts', sa.Column('photo_urls', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('posts', 'photo_urls')

