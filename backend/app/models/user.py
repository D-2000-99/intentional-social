from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.orm import relationship

from app.db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(50), unique=True, nullable=True, index=True)
    google_id = Column(String(255), unique=True, nullable=False, index=True)
    auth_provider = Column(String(20), default="google", nullable=False)
    full_name = Column(String(255), nullable=True)  # From Google, user can override
    picture_url = Column(String(500), nullable=True)  # From Google, user can override
    display_name = Column(String(255), nullable=True)  # User-customizable override for full_name
    avatar_url = Column(String(500), nullable=True)  # User-customizable override for picture_url
    bio = Column(String(500), nullable=True)  # User bio/note
    is_banned = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    posts = relationship("Post", back_populates="author", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="author", cascade="all, delete-orphan")
    replies = relationship("Reply", back_populates="author", cascade="all, delete-orphan")
    reactions = relationship("Reaction", back_populates="user", cascade="all, delete-orphan")
    
    def get_display_name(self) -> str:
        """Get display name, preferring user override over Google full_name."""
        return self.display_name or self.full_name or self.username
    
    def get_avatar_url(self) -> str | None:
        """Get avatar URL, preferring user override over Google picture_url."""
        return self.avatar_url or self.picture_url