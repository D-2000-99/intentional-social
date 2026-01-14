from sqlalchemy import Column, Integer, ForeignKey, DateTime, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from app.db import Base


class UserTag(Base):
    __tablename__ = "user_tags"

    id = Column(Integer, primary_key=True, index=True)
    owner_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # who is tagging
    target_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # who is being tagged
    tag_id = Column(Integer, ForeignKey("tags.id"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    owner = relationship("User", foreign_keys=[owner_user_id], backref="tags_owned")
    target = relationship("User", foreign_keys=[target_user_id], backref="tags_received")
    tag = relationship("Tag", backref="user_tags")

    # Constraints
    __table_args__ = (
        UniqueConstraint('owner_user_id', 'target_user_id', 'tag_id', name='unique_user_tag_assignment'),
        Index('idx_owner_user', 'owner_user_id'),
        Index('idx_target_user', 'target_user_id'),
        Index('idx_tag', 'tag_id'),
    )

