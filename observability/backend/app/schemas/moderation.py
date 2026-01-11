from datetime import datetime
from pydantic import BaseModel
from typing import Optional, List


class UserOut(BaseModel):
    id: int
    email: str
    username: Optional[str] = None
    full_name: Optional[str] = None
    display_name: Optional[str] = None
    is_banned: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class ReportedPostOut(BaseModel):
    id: int
    post_id: int
    reported_by_id: Optional[int] = None
    reason: Optional[str] = None
    created_at: datetime
    resolved_at: Optional[datetime] = None
    resolved_by_id: Optional[int] = None
    post: Optional[dict] = None  # Will contain post details
    reported_by: Optional[UserOut] = None
    
    class Config:
        from_attributes = True

