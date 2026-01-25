from datetime import datetime
from pydantic import BaseModel
from typing import Optional, List
from app.schemas.tag import TagOut

class PostCreate(BaseModel):
    content: str
    audience_type: str = "all"  # 'all', 'tags', 'connections', 'private'
    audience_tag_ids: list[int] = []  # Used when audience_type is 'tags'
    photo_urls: list[str] = []  # List of S3 keys for photos (set by server after upload)

class AuthorOut(BaseModel):
    id: int
    username: str
    display_name: Optional[str] = None
    full_name: Optional[str] = None
    
    class Config:
        from_attributes = True

class PostOut(BaseModel):
    id: int
    author_id: int
    content: str
    audience_type: str
    photo_urls: list[str] = []  # List of S3 keys
    photo_urls_presigned: list[str] = []  # Stable image URLs (backend redirect)
    link_preview: Optional[dict] = None  # Link preview metadata
    created_at: datetime
    author: AuthorOut  # Include author details
    audience_tags: List[TagOut] = []  # Tags used for audience filtering
    digest_summary: Optional[str] = None  # LLM-generated summary for digest view
    # Note: importance_score is intentionally NOT included - it's internal only

    class Config:
        from_attributes = True


class ReportPostRequest(BaseModel):
    reason: Optional[str] = None  # Optional reason for reporting


class ReportedPostOut(BaseModel):
    id: int
    post_id: int
    reported_by_id: Optional[int] = None
    reason: Optional[str] = None
    created_at: datetime
    resolved_at: Optional[datetime] = None
    resolved_by_id: Optional[int] = None
    
    class Config:
        from_attributes = True
