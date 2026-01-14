from pydantic import BaseModel
from datetime import datetime


class ConnectionBase(BaseModel):
    pass


class ConnectionRequest(BaseModel):
    recipient_id: int


class ConnectionOut(BaseModel):
    id: int
    user_a_id: int
    user_b_id: int
    status: str
    created_at: datetime
    updated_at: datetime
    
    # Include user details for easier frontend display
    user_a_username: str | None = None
    user_b_username: str | None = None

    class Config:
        from_attributes = True


class ConnectionWithUser(BaseModel):
    """Connection with other user details (email removed for privacy)."""
    id: int
    status: str
    created_at: datetime
    other_user_id: int
    other_user_username: str

    class Config:
        from_attributes = True
