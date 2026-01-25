#!/usr/bin/env python3
"""
Run Alembic migrations to upgrade database to head.
This script runs automatically on container startup via Dockerfile CMD.
"""
import os
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from alembic.config import Config
from alembic import command
from app.config import settings

def run_migration():
    """Run Alembic migrations to upgrade database to head."""
    # Get the migrations directory path
    migrations_dir = Path(__file__).parent
    alembic_ini_path = migrations_dir.parent / "alembic.ini"
    
    # Create Alembic config
    alembic_cfg = Config(str(alembic_ini_path))
    
    # Override database URL from settings
    alembic_cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
    
    # Run migrations to head
    print("Running database migrations...")
    command.upgrade(alembic_cfg, "head")
    print("Migrations completed successfully!")

if __name__ == "__main__":
    try:
        run_migration()
    except Exception as e:
        print(f"Migration failed: {e}", file=sys.stderr)
        # Exit with error code - Dockerfile uses || true to continue anyway
        # but this ensures we log the error
        sys.exit(1)
