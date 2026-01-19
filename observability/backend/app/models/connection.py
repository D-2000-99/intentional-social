from sqlalchemy import Column, Integer, DateTime, ForeignKey, UniqueConstraint, Index, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from enum import Enum

from app.db import Base


class ConnectionStatus(str, Enum):
    """Valid connection status values."""
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class Connection(Base):
    __tablename__ = "connections"

    id = Column(Integer, primary_key=True, index=True)
    user_a_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user_b_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(
        SQLEnum(ConnectionStatus, native_enum=True, values_callable=lambda x: [e.value for e in x]),
        default=ConnectionStatus.PENDING,
        nullable=False
    )
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    user_a = relationship("User", foreign_keys=[user_a_id], backref="connections_as_a")
    user_b = relationship("User", foreign_keys=[user_b_id], backref="connections_as_b")

    # Constraints
    __table_args__ = (
        UniqueConstraint('user_a_id', 'user_b_id', name='unique_connection'),
        Index('idx_user_a', 'user_a_id'),
        Index('idx_user_b', 'user_b_id'),
        Index('idx_status', 'status'),
    )

