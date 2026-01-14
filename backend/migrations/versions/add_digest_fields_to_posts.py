"""Add digest fields to posts

Revision ID: add_digest_fields_to_posts
Revises: 778705460212
Create Date: 2025-01-XX

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'add_digest_fields_to_posts'
down_revision: Union[str, Sequence[str], None] = '778705460212'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add digest_summary and importance_score columns to posts table."""
    op.add_column('posts', sa.Column('digest_summary', sa.Text(), nullable=True))
    op.add_column('posts', sa.Column('importance_score', sa.Float(), nullable=True))


def downgrade() -> None:
    """Remove digest_summary and importance_score columns from posts table."""
    op.drop_column('posts', 'importance_score')
    op.drop_column('posts', 'digest_summary')

