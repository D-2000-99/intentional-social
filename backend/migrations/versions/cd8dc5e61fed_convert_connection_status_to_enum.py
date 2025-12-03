"""Convert connection status to enum

Revision ID: cd8dc5e61fed
Revises: e734d765d3ad
Create Date: 2025-12-03 21:36:36.235839

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'cd8dc5e61fed'
down_revision: Union[str, Sequence[str], None] = 'e734d765d3ad'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Drop legacy follows table
    op.drop_index(op.f('ix_follows_followee_id'), table_name='follows')
    op.drop_index(op.f('ix_follows_follower_id'), table_name='follows')
    op.drop_index(op.f('ix_follows_id'), table_name='follows')
    op.drop_table('follows')
    
    # Create the enum type for ConnectionStatus (lowercase to match Python enum)
    connection_status = postgresql.ENUM('pending', 'accepted', 'rejected', name='connectionstatus')
    connection_status.create(op.get_bind())
    
    # Convert existing values to enum (already lowercase)
    op.execute("ALTER TABLE connections ALTER COLUMN status TYPE connectionstatus USING status::connectionstatus")



def downgrade() -> None:
    """Downgrade schema."""
    # Convert enum back to VARCHAR
    op.execute("ALTER TABLE connections ALTER COLUMN status TYPE VARCHAR USING status::text")
    
    # Drop the enum type
    connection_status = postgresql.ENUM('pending', 'accepted', 'rejected', name='connectionstatus')
    connection_status.drop(op.get_bind())
    
    # Recreate follows table (legacy)
    op.create_table('follows',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('follower_id', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('followee_id', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['followee_id'], ['users.id'], name=op.f('follows_followee_id_fkey'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['follower_id'], ['users.id'], name=op.f('follows_follower_id_fkey'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('follows_pkey')),
    sa.UniqueConstraint('follower_id', 'followee_id', name=op.f('uq_follower_followee'), postgresql_include=[], postgresql_nulls_not_distinct=False)
    )
    op.create_index(op.f('ix_follows_id'), 'follows', ['id'], unique=False)
    op.create_index(op.f('ix_follows_follower_id'), 'follows', ['follower_id'], unique=False)
    op.create_index(op.f('ix_follows_followee_id'), 'follows', ['followee_id'], unique=False)
