from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship

from app.db import Base


class PostStats(Base):
    __tablename__ = "post_stats"

    post_id = Column(Integer, ForeignKey("posts.id"), primary_key=True, nullable=False, index=True)
    comment_count = Column(Integer, default=0, nullable=False)

    # Relationship
    post = relationship("Post", back_populates="stats")
