from pydantic import BaseModel, Field
from datetime import datetime


class TagCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=24)
    color_scheme: str = "generic"  # family, friends, inner, work, custom, generic


class TagUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=24)
    color_scheme: str | None = None


class TagOut(BaseModel):
    id: int
    user_id: int
    name: str
    color_scheme: str
    created_at: datetime

    class Config:
        from_attributes = True


class ConnectionTagCreate(BaseModel):
    tag_id: int


class ConnectionTagOut(BaseModel):
    id: int
    connection_id: int
    tag_id: int
    tag: TagOut
    created_at: datetime

    class Config:
        from_attributes = True
