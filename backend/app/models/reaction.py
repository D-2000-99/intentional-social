from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db import Base


class Reaction(Base):
    __tablename__ = "reactions"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    emoji = Column(String(10), nullable=False)  # Store emoji as string (e.g., "👍", "❤️", "😊")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Ensure one reaction per user per post (user can change their reaction)
    __table_args__ = (
        UniqueConstraint('post_id', 'user_id', name='uq_reaction_post_user'),
    )

    # Relationships
    post = relationship("Post", back_populates="reactions")
    user = relationship("User", back_populates="reactions")
