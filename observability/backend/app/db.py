from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import QueuePool

from app.config import settings

SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL

# Configure connection pooling for production
# pool_size: number of connections to maintain
# max_overflow: additional connections beyond pool_size
# pool_pre_ping: verify connections before using (prevents stale connections)
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    poolclass=QueuePool,
    pool_size=5,  # Sufficient for 10-20 users
    max_overflow=10,  # Allow up to 15 total connections
    pool_pre_ping=True,  # Verify connections before using
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()

