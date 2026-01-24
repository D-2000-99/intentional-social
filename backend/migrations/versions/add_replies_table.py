"""Add replies table

Revision ID: add_replies_001
Revises: 65f0331fea3f_add_performance_indexes
Create Date: 2026-01-24 11:22:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'add_replies_001'
down_revision: Union[str, Sequence[str], None] = '65f0331fea3f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'replies',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('comment_id', sa.Integer(), nullable=False),
        sa.Column('author_id', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['comment_id'], ['comments.id'], ),
        sa.ForeignKeyConstraint(['author_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_replies_id'), 'replies', ['id'], unique=False)
    op.create_index('idx_replies_comment_id', 'replies', ['comment_id'], unique=False)
    op.create_index('idx_replies_author_id', 'replies', ['author_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('idx_replies_author_id', table_name='replies')
    op.drop_index('idx_replies_comment_id', table_name='replies')
    op.drop_index(op.f('ix_replies_id'), table_name='replies')
    op.drop_table('replies')
