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
    requester_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    recipient_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(
        SQLEnum(ConnectionStatus),
        default=ConnectionStatus.PENDING,
        nullable=False
    )
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    requester = relationship("User", foreign_keys=[requester_id], backref="sent_requests")
    recipient = relationship("User", foreign_keys=[recipient_id], backref="received_requests")

    # Constraints
    __table_args__ = (
        UniqueConstraint('requester_id', 'recipient_id', name='unique_connection'),
        Index('idx_requester', 'requester_id'),
        Index('idx_recipient', 'recipient_id'),
        Index('idx_status', 'status'),
    )
