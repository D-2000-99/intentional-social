"""Fix connection status enum case mismatch

Revision ID: a1b2c3d4e5f6
Revises: cd8dc5e61fed
Create Date: 2025-12-05 10:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'cd8dc5e61fed'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Fix enum case to match Python enum (lowercase)."""
    # First, convert any existing uppercase values to lowercase in the table
    op.execute("""
        UPDATE connections 
        SET status = LOWER(status)::text
        WHERE status::text != LOWER(status::text)
    """)
    
    # Drop the existing enum type if it exists (this will fail if there are dependencies, so we handle it)
    # We need to temporarily change the column type
    op.execute("""
        ALTER TABLE connections 
        ALTER COLUMN status TYPE VARCHAR USING status::text
    """)
    
    # Drop the old enum type (handle case where it might not exist)
    op.execute("DROP TYPE IF EXISTS connectionstatus")
    
    # Create the enum type with lowercase values (matching Python enum)
    connection_status = postgresql.ENUM('pending', 'accepted', 'rejected', name='connectionstatus')
    connection_status.create(op.get_bind())
    
    # Convert the column back to the enum type
    op.execute("""
        ALTER TABLE connections 
        ALTER COLUMN status TYPE connectionstatus 
        USING LOWER(status::text)::connectionstatus
    """)


def downgrade() -> None:
    """Revert enum case fix."""
    # Convert back to VARCHAR
    op.execute("""
        ALTER TABLE connections 
        ALTER COLUMN status TYPE VARCHAR USING status::text
    """)
    
    # Drop the enum
    op.execute("DROP TYPE IF EXISTS connectionstatus")
    
    # Recreate with uppercase (if that was the original)
    connection_status = postgresql.ENUM('PENDING', 'ACCEPTED', 'REJECTED', name='connectionstatus')
    connection_status.create(op.get_bind())
    
    # Convert back
    op.execute("""
        ALTER TABLE connections 
        ALTER COLUMN status TYPE connectionstatus 
        USING UPPER(status::text)::connectionstatus
    """)
