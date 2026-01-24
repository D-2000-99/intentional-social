"""Add initiator to connections

Revision ID: add_connection_initiator
Revises: merge_replies_and_registration
Create Date: 2026-01-24 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_connection_initiator'
down_revision: Union[str, Sequence[str], None] = 'merge_replies_and_registration'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add initiator tracking to connections."""
    op.add_column('connections', sa.Column('initiated_by_user_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_connections_initiated_by_user_id',
        'connections',
        'users',
        ['initiated_by_user_id'],
        ['id'],
    )
    op.execute("""
        UPDATE connections
        SET initiated_by_user_id = user_a_id
        WHERE initiated_by_user_id IS NULL
    """)
    op.alter_column('connections', 'initiated_by_user_id', nullable=False)
    op.create_index('idx_initiated_by_user', 'connections', ['initiated_by_user_id'], unique=False)


def downgrade() -> None:
    """Remove initiator tracking from connections."""
    op.drop_index('idx_initiated_by_user', table_name='connections')
    op.drop_constraint('fk_connections_initiated_by_user_id', 'connections', type_='foreignkey')
    op.drop_column('connections', 'initiated_by_user_id')
