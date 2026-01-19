"""
Registration Request Model - MVP TEMPORARY FEATURE
==================================================
This model is used to manage user registration requests during the MVP phase.
Users can register, but their accounts are created only after admin approval.

TODO: Remove this entire file and related code when moving beyond MVP phase.
See backend/app/routers/auth.py and observability/backend/app/routers/moderation.py
for related code that should also be removed.
"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
import enum

from app.db import Base


class RegistrationStatus(enum.Enum):
    """Status of a registration request."""
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"


class RegistrationRequest(Base):
    """
    Registration Request Model - MVP TEMPORARY FEATURE
    
    Stores registration requests from users who sign up via Google OAuth.
    Admins can approve or deny these requests from the observability dashboard.
    
    TODO: Remove this model and create a migration to drop the table when moving beyond MVP.
    """
    __tablename__ = "registration_requests"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), nullable=False, index=True)
    google_id = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=True)
    picture_url = Column(String(500), nullable=True)
    
    # Status tracking
    status = Column(SQLEnum(RegistrationStatus), default=RegistrationStatus.PENDING, nullable=False, index=True)
    
    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    reviewed_at = Column(DateTime, nullable=True)
    reviewed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Relationships
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_id], backref="registration_requests_reviewed")
