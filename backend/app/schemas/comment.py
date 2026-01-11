from datetime import datetime
from pydantic import BaseModel
from typing import Optional
from app.schemas.post import AuthorOut


class CommentCreate(BaseModel):
    post_id: int
    content: str


class CommentOut(BaseModel):
    id: int
    post_id: int
    author_id: int
    content: str
    created_at: datetime
    author: AuthorOut

    class Config:
        from_attributes = True
