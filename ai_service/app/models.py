"""
Database models for AI Service.

Minimal models needed for this service.
Matches the main backend schema.
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

Base = declarative_base()


class User(Base):
    """User model for getting author information."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(50), unique=True, nullable=True, index=True)
    full_name = Column(String(255), nullable=True)
    display_name = Column(String(255), nullable=True)
    
    def get_display_name(self) -> str:
        """Get display name, preferring user override over full_name."""
        return self.display_name or self.full_name or self.username or "Unknown"


class Post(Base):
    """Post model matching the main backend schema."""
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    audience_type = Column(String(20), default="all")
    photo_urls = Column(JSON, default=lambda: [])
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    digest_summary = Column(Text, nullable=True)
    importance_score = Column(Float, nullable=True)
    
    # Relationship (for joinedload)
    author = relationship("User", foreign_keys=[author_id])

