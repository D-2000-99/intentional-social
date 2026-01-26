"""Add post_stats table

Revision ID: add_post_stats_001
Revises: add_connection_initiator
Create Date: 2026-01-26 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'add_post_stats_001'
down_revision: Union[str, Sequence[str], None] = 'add_connection_initiator'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'post_stats',
        sa.Column('post_id', sa.Integer(), nullable=False),
        sa.Column('comment_count', sa.Integer(), nullable=False, server_default='0'),
        sa.ForeignKeyConstraint(['post_id'], ['posts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('post_id')
    )
    op.create_index('idx_post_stats_post_id', 'post_stats', ['post_id'], unique=False)
    
    # Initialize PostStats for all existing posts with their actual comment counts
    op.execute("""
        INSERT INTO post_stats (post_id, comment_count)
        SELECT p.id, COALESCE(COUNT(c.id), 0)
        FROM posts p
        LEFT JOIN comments c ON c.post_id = p.id
        GROUP BY p.id
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('idx_post_stats_post_id', table_name='post_stats')
    op.drop_table('post_stats')
