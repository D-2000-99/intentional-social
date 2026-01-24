from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship

from app.db import Base


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    recipient_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False, index=True)
    comment_id = Column(Integer, ForeignKey("comments.id"), nullable=True, index=True)
    type = Column(String(20), nullable=False)  # 'comment' or 'reply'
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    read_at = Column(DateTime, nullable=True)

    # Relationships
    recipient = relationship("User", foreign_keys=[recipient_id])
    actor = relationship("User", foreign_keys=[actor_id])
    post = relationship("Post")
    comment = relationship("Comment")

    # Indexes for efficient queries
    __table_args__ = (
        Index('idx_notification_recipient_read', 'recipient_id', 'read_at'),
        Index('idx_notification_recipient_post', 'recipient_id', 'post_id'),
        Index('idx_notification_recipient_comment', 'recipient_id', 'comment_id'),
    )
