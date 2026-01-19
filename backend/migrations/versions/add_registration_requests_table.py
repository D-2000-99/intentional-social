"""add_registration_requests_table - MVP TEMPORARY FEATURE

Revision ID: add_registration_requests
Revises: 65f0331fea3f
Create Date: 2025-01-XX XX:XX:XX.XXXXXX

MVP TEMPORARY MIGRATION - Remove when moving beyond MVP phase.
This migration creates the registration_requests table for managing user registration
during the MVP phase. See backend/app/models/registration_request.py for the model.

TODO: Create a migration to drop this table when removing MVP registration restrictions.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_registration_requests'
down_revision: Union[str, Sequence[str], None] = '65f0331fea3f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create registration_requests table for MVP registration management."""
    # Create registration_requests table
    op.create_table(
        'registration_requests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('google_id', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=True),
        sa.Column('picture_url', sa.String(length=500), nullable=True),
        sa.Column('status', sa.Enum('PENDING', 'APPROVED', 'DENIED', name='registrationstatus'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('reviewed_by_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['reviewed_by_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('google_id')
    )
    op.create_index(op.f('ix_registration_requests_id'), 'registration_requests', ['id'], unique=False)
    op.create_index('ix_registration_requests_email', 'registration_requests', ['email'], unique=False)
    op.create_index('ix_registration_requests_google_id', 'registration_requests', ['google_id'], unique=False)
    op.create_index('ix_registration_requests_status', 'registration_requests', ['status'], unique=False)
    op.create_index('ix_registration_requests_created_at', 'registration_requests', ['created_at'], unique=False)


def downgrade() -> None:
    """Drop registration_requests table - MVP TEMPORARY FEATURE."""
    op.drop_index('ix_registration_requests_created_at', table_name='registration_requests')
    op.drop_index('ix_registration_requests_status', table_name='registration_requests')
    op.drop_index('ix_registration_requests_google_id', table_name='registration_requests')
    op.drop_index('ix_registration_requests_email', table_name='registration_requests')
    op.drop_index(op.f('ix_registration_requests_id'), table_name='registration_requests')
    op.drop_table('registration_requests')
    # Drop the enum type
    sa.Enum(name='registrationstatus').drop(op.get_bind(), checkfirst=True)
