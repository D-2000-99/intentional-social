"""Add comments table

Revision ID: add_comments_001
Revises: add_bio_to_users
Create Date: 2025-12-06 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'add_comments_001'
down_revision: Union[str, Sequence[str], None] = 'add_bio_to_users'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'comments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('post_id', sa.Integer(), nullable=False),
        sa.Column('author_id', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['post_id'], ['posts.id'], ),
        sa.ForeignKeyConstraint(['author_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_comments_id'), 'comments', ['id'], unique=False)
    op.create_index('idx_comments_post_id', 'comments', ['post_id'], unique=False)
    op.create_index('idx_comments_author_id', 'comments', ['author_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('idx_comments_author_id', table_name='comments')
    op.drop_index('idx_comments_post_id', table_name='comments')
    op.drop_index(op.f('ix_comments_id'), table_name='comments')
    op.drop_table('comments')
