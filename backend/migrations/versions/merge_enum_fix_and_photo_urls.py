"""Merge enum fix and photo urls branches

Revision ID: merge_heads_001
Revises: f8a9b2c3d4e5, a1b2c3d4e5f6
Create Date: 2025-12-05 10:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'merge_heads_001'
down_revision: Union[str, Sequence[str], None] = ['f8a9b2c3d4e5', 'a1b2c3d4e5f6']
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Merge the two migration branches."""
    # This is a merge migration - no schema changes needed
    # Both branches have already been applied
    pass


def downgrade() -> None:
    """Downgrade merge."""
    # Merge migrations typically don't need downgrade logic
    pass
