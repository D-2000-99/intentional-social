"""Refactor connections and tags schema

Revision ID: refactor_connections_tags
Revises: add_digest_fields_to_posts
Create Date: 2025-01-XX

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'refactor_connections_tags'
down_revision: Union[str, Sequence[str], None] = 'add_digest_fields_to_posts'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Refactor connections and tags schema:
    1. Change connections.requester_id/recipient_id to user_a_id/user_b_id
    2. Change tags.user_id to owner_user_id
    3. Create user_tags table to replace connection_tags
    4. Migrate data from connection_tags to user_tags
    5. Drop connection_tags table
    """
    
    # Step 1: Rename columns in connections table and normalize (ensure user_a_id < user_b_id)
    # First, add new columns
    op.add_column('connections', sa.Column('user_a_id', sa.Integer(), nullable=True))
    op.add_column('connections', sa.Column('user_b_id', sa.Integer(), nullable=True))
    
    # Normalize: ensure user_a_id < user_b_id for consistency
    op.execute("""
        UPDATE connections
        SET 
            user_a_id = LEAST(requester_id, recipient_id),
            user_b_id = GREATEST(requester_id, recipient_id)
    """)
    
    # Make columns NOT NULL
    op.alter_column('connections', 'user_a_id', nullable=False)
    op.alter_column('connections', 'user_b_id', nullable=False)
    
    # Drop old columns (this will automatically drop indexes and constraints on those columns)
    op.drop_column('connections', 'requester_id')
    op.drop_column('connections', 'recipient_id')
    
    # Create new indexes
    op.create_index('idx_user_a', 'connections', ['user_a_id'], unique=False)
    op.create_index('idx_user_b', 'connections', ['user_b_id'], unique=False)
    
    # Recreate unique constraint with new column names
    # First drop the old constraint if it exists (it should have been auto-dropped with columns)
    op.execute("ALTER TABLE connections DROP CONSTRAINT IF EXISTS unique_connection")
    op.create_unique_constraint('unique_connection', 'connections', ['user_a_id', 'user_b_id'])
    
    # Step 2: Rename column in tags table
    op.alter_column('tags', 'user_id', new_column_name='owner_user_id')
    
    # Step 3: Create user_tags table
    op.create_table('user_tags',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('owner_user_id', sa.Integer(), nullable=False),  # who is tagging
        sa.Column('target_user_id', sa.Integer(), nullable=False),  # who is being tagged
        sa.Column('tag_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['owner_user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['target_user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['tag_id'], ['tags.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('owner_user_id', 'target_user_id', 'tag_id', name='unique_user_tag_assignment')
    )
    op.create_index('idx_owner_user', 'user_tags', ['owner_user_id'], unique=False)
    op.create_index('idx_target_user', 'user_tags', ['target_user_id'], unique=False)
    op.create_index('idx_tag', 'user_tags', ['tag_id'], unique=False)
    op.create_index(op.f('ix_user_tags_id'), 'user_tags', ['id'], unique=False)
    
    # Step 4: Migrate data from connection_tags to user_tags
    # For each connection_tag, we need to determine:
    # - owner_user_id: the user who owns the tag
    # - target_user_id: the other user in the connection
    # 
    # We'll use a SQL query to migrate the data
    op.execute("""
        INSERT INTO user_tags (owner_user_id, target_user_id, tag_id, created_at)
        SELECT 
            t.owner_user_id as owner_user_id,
            CASE 
                WHEN c.user_a_id = t.owner_user_id THEN c.user_b_id
                ELSE c.user_a_id
            END as target_user_id,
            ct.tag_id,
            ct.created_at
        FROM connection_tags ct
        JOIN connections c ON ct.connection_id = c.id
        JOIN tags t ON ct.tag_id = t.id
    """)
    
    # Step 5: Drop connection_tags table
    # Drop index if it exists
    op.execute("DROP INDEX IF EXISTS ix_connection_tags_id")
    op.execute("DROP INDEX IF EXISTS connection_tags_ix_connection_tags_id")
    op.drop_table('connection_tags')


def downgrade() -> None:
    """Revert schema changes."""
    
    # Recreate connection_tags table
    op.create_table('connection_tags',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('connection_id', sa.Integer(), nullable=False),
        sa.Column('tag_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['connection_id'], ['connections.id'], ),
        sa.ForeignKeyConstraint(['tag_id'], ['tags.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('connection_id', 'tag_id', name='unique_connection_tag')
    )
    op.create_index(op.f('ix_connection_tags_id'), 'connection_tags', ['id'], unique=False)
    
    # Migrate data back from user_tags to connection_tags
    # This is more complex - we need to find the connection between owner and target
    # Note: This migration might lose data if multiple connections exist between two users
    op.execute("""
        INSERT INTO connection_tags (connection_id, tag_id, created_at)
        SELECT DISTINCT ON (ut.tag_id, c.id)
            c.id as connection_id,
            ut.tag_id,
            ut.created_at
        FROM user_tags ut
        JOIN connections c ON (
            (c.user_a_id = ut.owner_user_id AND c.user_b_id = ut.target_user_id) OR
            (c.user_b_id = ut.owner_user_id AND c.user_a_id = ut.target_user_id)
        )
        ORDER BY ut.tag_id, c.id, ut.created_at
    """)
    
    # Drop user_tags table
    op.execute("DROP INDEX IF EXISTS ix_user_tags_id")
    op.execute("DROP INDEX IF EXISTS user_tags_ix_user_tags_id")
    op.execute("DROP INDEX IF EXISTS idx_tag")
    op.execute("DROP INDEX IF EXISTS user_tags_idx_tag")
    op.execute("DROP INDEX IF EXISTS idx_target_user")
    op.execute("DROP INDEX IF EXISTS user_tags_idx_target_user")
    op.execute("DROP INDEX IF EXISTS idx_owner_user")
    op.execute("DROP INDEX IF EXISTS user_tags_idx_owner_user")
    op.drop_table('user_tags')
    
    # Revert tags table
    op.alter_column('tags', 'owner_user_id', new_column_name='user_id')
    
    # Revert connections table
    # Add back old columns
    op.add_column('connections', sa.Column('requester_id', sa.Integer(), nullable=True))
    op.add_column('connections', sa.Column('recipient_id', sa.Integer(), nullable=True))
    
    # For downgrade, we'll use user_a_id as requester_id and user_b_id as recipient_id
    # (This is a simplification - we can't perfectly restore the original direction)
    op.execute("""
        UPDATE connections
        SET 
            requester_id = user_a_id,
            recipient_id = user_b_id
    """)
    
    op.alter_column('connections', 'requester_id', nullable=False)
    op.alter_column('connections', 'recipient_id', nullable=False)
    
    op.drop_column('connections', 'user_b_id')
    op.drop_column('connections', 'user_a_id')
    
    # Drop new indexes if they exist
    op.execute("DROP INDEX IF EXISTS idx_user_b")
    op.execute("DROP INDEX IF EXISTS connections_idx_user_b")
    op.execute("DROP INDEX IF EXISTS idx_user_a")
    op.execute("DROP INDEX IF EXISTS connections_idx_user_a")
    
    # Create old indexes
    op.create_index('idx_recipient', 'connections', ['recipient_id'], unique=False)
    op.create_index('idx_requester', 'connections', ['requester_id'], unique=False)

