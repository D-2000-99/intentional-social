"""add_performance_indexes

Revision ID: 65f0331fea3f
Revises: refactor_connections_tags
Create Date: 2026-01-17 12:39:56.810795

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '65f0331fea3f'
down_revision: Union[str, Sequence[str], None] = 'refactor_connections_tags'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add performance indexes for optimized queries."""
    # Composite index for connection lookups
    op.create_index(
        'idx_connection_lookup',
        'connections',
        ['user_a_id', 'user_b_id', 'status']
    )
    
    # Index for chronological post queries
    op.create_index(
        'idx_post_created_at',
        'posts',
        [sa.text('created_at DESC')]
    )
    
    # Index for post author queries
    op.create_index(
        'idx_post_author',
        'posts',
        ['author_id']
    )
    
    # Composite index for post audience tags
    op.create_index(
        'idx_post_audience_tag_lookup',
        'post_audience_tags',
        ['post_id', 'tag_id']
    )
    
    # Composite index for user tags
    op.create_index(
        'idx_user_tag_lookup',
        'user_tags',
        ['owner_user_id', 'target_user_id', 'tag_id']
    )
    
    # Index for comment post lookups
    op.create_index(
        'idx_comment_post',
        'comments',
        ['post_id']
    )
    
    # Index for comment author lookups
    op.create_index(
        'idx_comment_author',
        'comments',
        ['author_id']
    )


def downgrade() -> None:
    """Remove performance indexes."""
    op.drop_index('idx_connection_lookup', 'connections')
    op.drop_index('idx_post_created_at', 'posts')
    op.drop_index('idx_post_author', 'posts')
    op.drop_index('idx_post_audience_tag_lookup', 'post_audience_tags')
    op.drop_index('idx_user_tag_lookup', 'user_tags')
    op.drop_index('idx_comment_post', 'comments')
    op.drop_index('idx_comment_author', 'comments')
