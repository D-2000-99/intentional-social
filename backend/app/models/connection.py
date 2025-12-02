from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from datetime import datetime

from app.db import Base


class Connection(Base):
    __tablename__ = "connections"

    id = Column(Integer, primary_key=True, index=True)
    requester_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    recipient_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String, default="pending", nullable=False)  # 'pending', 'accepted', 'rejected'
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

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
