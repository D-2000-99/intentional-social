from datetime import datetime
from pydantic import BaseModel
from typing import List, Optional
from app.schemas.post import AuthorOut


class ReplyCreate(BaseModel):
    comment_id: int
    content: str


class ReplyOut(BaseModel):
    id: int
    comment_id: int
    author_id: int
    content: str
    created_at: datetime
    author: AuthorOut

    class Config:
        from_attributes = True
