from datetime import datetime
from pydantic import BaseModel

class PostCreate(BaseModel):
    content: str

class AuthorOut(BaseModel):
    id: int
    username: str
    
    class Config:
        from_attributes = True

class PostOut(BaseModel):
    id: int
    author_id: int
    content: str
    created_at: datetime
    author: AuthorOut  # Include author details

    class Config:
        from_attributes = True
