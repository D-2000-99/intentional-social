from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey, event
from sqlalchemy.orm import relationship
from sqlalchemy.sql import text

from app.db import Base


class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False, index=True)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    post = relationship("Post", back_populates="comments")
    author = relationship("User", back_populates="comments")
    replies = relationship("Reply", back_populates="comment", cascade="all, delete-orphan")


@event.listens_for(Comment, "after_delete")
def decrement_comment_count(mapper, connection, target):
    """Decrement comment_count in PostStats when a comment is deleted."""
    # Use raw SQL via connection to update PostStats
    # This works for both individual and cascade deletes
    connection.execute(
        text("""
            UPDATE post_stats 
            SET comment_count = GREATEST(0, comment_count - 1)
            WHERE post_id = :post_id
        """),
        {"post_id": target.post_id}
    )

