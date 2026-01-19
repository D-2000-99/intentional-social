from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from app.db import Base


class Tag(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, index=True)
    owner_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(24), nullable=False)
    color_scheme = Column(String(20), default="generic")  # family, friends, inner, work, custom, generic
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    owner = relationship("User", backref="tags")

    # Constraints
    __table_args__ = (
        UniqueConstraint('owner_user_id', 'name', name='unique_user_tag'),
        Index('idx_user_tags', 'owner_user_id'),
    )

