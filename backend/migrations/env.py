import sys
import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# Make sure Alembic can import app modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load Base and settings
from app.db import Base
from app.config import settings

# Import ALL models so metadata picks them up
from app.models.user import User  # noqa
from app.models.connection import Connection  # noqa
from app.models.post import Post  # noqa
from app.models.tag import Tag  # noqa
from app.models.user_tag import UserTag  # noqa
from app.models.post_audience_tag import PostAudienceTag  # noqa
from app.models.comment import Comment  # noqa
from app.models.reply import Reply  # noqa
from app.models.reaction import Reaction  # noqa
from app.models.post_stats import PostStats  # noqa

# Alembic Config object
config = context.config

# Override DB URL dynamically
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Logging config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# This is what autogenerate uses
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
