from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import QueuePool

from app.config import settings

SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL

# Configure connection pooling for production (optimized for 4GB RAM, 1 CPU core)
# pool_size: number of connections to maintain
# max_overflow: additional connections beyond pool_size
# pool_pre_ping: verify connections before using (prevents stale connections)
# pool_recycle: recycle connections after 1 hour to prevent stale connections
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    poolclass=QueuePool,
    pool_size=8,  # Optimized for 30-60 concurrent users (4GB RAM)
    max_overflow=15,  # Allow up to 23 total connections
    pool_pre_ping=True,  # Verify connections before using
    pool_recycle=3600,  # Recycle connections after 1 hour
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()
