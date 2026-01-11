"""add_is_banned_and_reported_posts

Revision ID: 778705460212
Revises: add_comments_001
Create Date: 2025-12-21 20:43:19.120529

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '778705460212'
down_revision: Union[str, Sequence[str], None] = 'add_comments_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add is_banned column to users table and create reported_posts table."""
    # Add is_banned column to users table
    op.add_column('users', sa.Column('is_banned', sa.Boolean(), nullable=False, server_default='false'))
    
    # Create reported_posts table
    op.create_table(
        'reported_posts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('post_id', sa.Integer(), nullable=False),
        sa.Column('reported_by_id', sa.Integer(), nullable=True),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.Column('resolved_by_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['post_id'], ['posts.id'], ),
        sa.ForeignKeyConstraint(['reported_by_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['resolved_by_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_reported_posts_id'), 'reported_posts', ['id'], unique=False)
    op.create_index('ix_reported_posts_post_id', 'reported_posts', ['post_id'], unique=False)
    op.create_index('ix_reported_posts_reported_by_id', 'reported_posts', ['reported_by_id'], unique=False)


def downgrade() -> None:
    """Remove is_banned column and drop reported_posts table."""
    op.drop_index('ix_reported_posts_reported_by_id', table_name='reported_posts')
    op.drop_index('ix_reported_posts_post_id', table_name='reported_posts')
    op.drop_index(op.f('ix_reported_posts_id'), table_name='reported_posts')
    op.drop_table('reported_posts')
    op.drop_column('users', 'is_banned')
