"""Migrate to Google OAuth - remove password system

Revision ID: migrate_to_google_oauth
Revises: merge_heads_001
Create Date: 2025-12-06

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'migrate_to_google_oauth'
down_revision: Union[str, Sequence[str], None] = 'merge_heads_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Migrate to Google OAuth - remove password system and clear all data."""
    
    # Clear all existing data (fresh start)
    # Delete in order to respect foreign key constraints
    op.execute("DELETE FROM connection_tags")
    op.execute("DELETE FROM post_audience_tags")
    op.execute("DELETE FROM tags")
    op.execute("DELETE FROM connections")
    op.execute("DELETE FROM posts")
    
    # Delete email_verifications first (before users due to foreign key)
    op.execute("DELETE FROM email_verifications")
    
    # Now safe to delete users
    op.execute("DELETE FROM users")
    
    # Drop email_verifications table (no longer needed)
    op.drop_table('email_verifications')
    
    # Remove password-related columns
    op.drop_column('users', 'hashed_password')
    op.drop_column('users', 'email_verified')
    
    # Add Google OAuth columns
    op.add_column('users', sa.Column('google_id', sa.String(255), nullable=False))
    op.add_column('users', sa.Column('auth_provider', sa.String(20), nullable=False, server_default='google'))
    op.add_column('users', sa.Column('full_name', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('picture_url', sa.String(500), nullable=True))
    op.add_column('users', sa.Column('display_name', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('avatar_url', sa.String(500), nullable=True))
    
    # Create unique index on google_id
    op.create_index(op.f('ix_users_google_id'), 'users', ['google_id'], unique=True)


def downgrade() -> None:
    """Revert to password system (not recommended, but provided for completeness)."""
    
    # Remove Google OAuth columns
    op.drop_index(op.f('ix_users_google_id'), table_name='users')
    op.drop_column('users', 'avatar_url')
    op.drop_column('users', 'display_name')
    op.drop_column('users', 'picture_url')
    op.drop_column('users', 'full_name')
    op.drop_column('users', 'auth_provider')
    op.drop_column('users', 'google_id')
    
    # Restore password-related columns
    op.add_column('users', sa.Column('hashed_password', sa.String(255), nullable=False, server_default=''))
    op.add_column('users', sa.Column('email_verified', sa.String(10), nullable=False, server_default='false'))
    
    # Recreate email_verifications table
    op.create_table(
        'email_verifications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('otp_code', sa.String(6), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('verified_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_email_verifications_id'), 'email_verifications', ['id'], unique=False)
    op.create_index(op.f('ix_email_verifications_user_id'), 'email_verifications', ['user_id'], unique=False)
