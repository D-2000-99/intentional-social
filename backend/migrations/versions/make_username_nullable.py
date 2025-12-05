"""Make username nullable for new user registration

Revision ID: make_username_nullable
Revises: migrate_to_google_oauth
Create Date: 2025-12-07

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'make_username_nullable'
down_revision: Union[str, Sequence[str], None] = 'migrate_to_google_oauth'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Make username nullable to allow users to be created without username."""
    # Drop the unique constraint on username temporarily
    op.drop_index(op.f('ix_users_username'), table_name='users')
    
    # Make username nullable
    op.alter_column('users', 'username',
                    existing_type=sa.String(length=50),
                    nullable=True,
                    existing_nullable=False)
    
    # Recreate the unique index (allows NULL values)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)


def downgrade() -> None:
    """Revert username to non-nullable."""
    # First, set any NULL usernames to a default value (using email prefix)
    op.execute("""
        UPDATE users 
        SET username = LOWER(SPLIT_PART(email, '@', 1)) || '_' || id::text
        WHERE username IS NULL
    """)
    
    # Drop the unique index
    op.drop_index(op.f('ix_users_username'), table_name='users')
    
    # Make username non-nullable again
    op.alter_column('users', 'username',
                    existing_type=sa.String(length=50),
                    nullable=False,
                    existing_nullable=True)
    
    # Recreate the unique index
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)
