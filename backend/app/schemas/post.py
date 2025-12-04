from datetime import datetime
from pydantic import BaseModel

class PostCreate(BaseModel):
    content: str
    audience_type: str = "all"  # 'all', 'tags', 'connections', 'private'
    audience_tag_ids: list[int] = []  # Used when audience_type is 'tags'
    photo_urls: list[str] = []  # List of S3 keys for photos (set by server after upload)

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
    photo_urls: list[str] = []  # List of S3 keys
    photo_urls_presigned: list[str] = []  # Pre-signed URLs for client access (generated on demand)
    created_at: datetime
    author: AuthorOut  # Include author details

    class Config:
        from_attributes = True
