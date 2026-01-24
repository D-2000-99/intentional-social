#!/usr/bin/env python3
"""
Run the notifications table migration.
This script can be executed directly or imported.
"""
import os
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from app.config import settings

def run_migration():
    """Run the notifications table migration."""
    # Read SQL file
    sql_file = Path(__file__).parent / "create_notifications_table.sql"
    with open(sql_file, 'r') as f:
        sql_content = f.read()
    
    # Create database engine
    engine = create_engine(settings.DATABASE_URL)
    
    # Execute the entire SQL file as one transaction
    # The SQL file is now idempotent (checks if table/index exists before creating)
    with engine.begin() as conn:
        try:
            conn.execute(text(sql_content))
        except Exception as e:
            error_str = str(e).lower()
            # If table/index already exists, that's okay - the SQL should handle this now
            # but just in case, we'll catch and ignore
            if "already exists" in error_str or "duplicate" in error_str:
                pass  # Table/index already exists, skip (shouldn't happen with new SQL)
            else:
                raise
    
    print("Migration completed successfully!")

if __name__ == "__main__":
    try:
        run_migration()
    except Exception as e:
        print(f"Migration failed: {e}", file=sys.stderr)
        sys.exit(1)
