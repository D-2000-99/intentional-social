from datetime import datetime
from pydantic import BaseModel, EmailStr
from typing import Optional


class UserBase(BaseModel):
    email: EmailStr
    username: Optional[str] = None


class UserCreate(UserBase):
    """User creation schema for Google OAuth users."""
    google_id: str
    full_name: Optional[str] = None
    picture_url: Optional[str] = None


class UserOut(UserBase):
    id: int
    google_id: str
    auth_provider: str
    full_name: Optional[str] = None
    picture_url: Optional[str] = None
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
