from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Float
from sqlalchemy.orm import relationship

from app.db import Base


class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    audience_type = Column(String(20), default="all")  # 'all', 'tags', 'connections', 'private'
    photo_urls = Column(JSON, default=lambda: [])  # List of S3 keys for photos
    created_at = Column(DateTime, nullable=False)  # Set explicitly using client time
    
    # Digest fields
    digest_summary = Column(Text, nullable=True)  # LLM-generated summary for digest view
    importance_score = Column(Float, nullable=True)  # Internal importance score (0-10), never exposed to users

    author = relationship("User", back_populates="posts")
    comments = relationship("Comment", back_populates="post", cascade="all, delete-orphan")
