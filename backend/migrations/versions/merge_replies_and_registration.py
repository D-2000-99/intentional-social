"""Merge registration_requests and replies migrations

Revision ID: merge_replies_and_registration
Revises: add_registration_requests, add_replies_001
Create Date: 2026-01-24 11:33:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'merge_replies_and_registration'
down_revision: Union[str, Sequence[str], None] = ('add_registration_requests', 'add_replies_001')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Merge migration - nothing to do."""
    pass


def downgrade() -> None:
    """Merge migration - nothing to do."""
    pass
