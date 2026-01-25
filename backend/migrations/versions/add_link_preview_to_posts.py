"""add_link_preview_to_posts

Revision ID: add_link_preview
Revises: add_digest_fields_to_posts
Create Date: 2026-01-26

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'add_link_preview'
down_revision: Union[str, Sequence[str], None] = 'add_reactions_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add link_preview JSON column to posts table."""
    op.add_column('posts', sa.Column('link_preview', postgresql.JSON(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    """Remove link_preview column from posts table."""
    op.drop_column('posts', 'link_preview')
