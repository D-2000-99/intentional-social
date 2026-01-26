"""Merge reactions and post_stats migrations

Revision ID: merge_reactions_post_stats
Revises: add_reactions_001, add_post_stats_001
Create Date: 2026-01-26 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'merge_reactions_post_stats'
down_revision: Union[str, Sequence[str], None] = ('add_reactions_001', 'add_post_stats_001')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Merge migrations - no schema changes needed."""
    pass


def downgrade() -> None:
    """Merge migrations - no schema changes needed."""
    pass
