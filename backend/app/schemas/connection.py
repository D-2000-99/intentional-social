from pydantic import BaseModel
from datetime import datetime


class ConnectionBase(BaseModel):
    pass


class ConnectionRequest(BaseModel):
    recipient_id: int


class ConnectionOut(BaseModel):
    id: int
    requester_id: int
    recipient_id: int
    status: str
    created_at: datetime
    updated_at: datetime
    
    # Include user details for easier frontend display
    requester_username: str | None = None
    recipient_username: str | None = None

    class Config:
        from_attributes = True


class ConnectionWithUser(BaseModel):
    id: int
    status: str
    created_at: datetime
    other_user_id: int
    other_user_username: str
    other_user_email: str

    class Config:
        from_attributes = True
