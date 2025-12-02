from datetime import datetime
from pydantic import BaseModel

class PostCreate(BaseModel):
    content: str
    audience_type: str = "all"  # 'all', 'tags', 'connections', 'private'
    audience_tag_ids: list[int] = []  # Used when audience_type is 'tags'

class AuthorOut(BaseModel):
    id: int
    username: str
    
    class Config:
        from_attributes = True

class PostOut(BaseModel):
    id: int
    author_id: int
    content: str
    audience_type: str
    created_at: datetime
    author: AuthorOut  # Include author details

    class Config:
        from_attributes = True
