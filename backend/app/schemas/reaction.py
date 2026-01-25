from datetime import datetime
from pydantic import BaseModel
from typing import Optional, List
from app.schemas.post import AuthorOut


class ReactionCreate(BaseModel):
    emoji: str  # Emoji string (e.g., "👍", "❤️", "😊")


class ReactionOut(BaseModel):
    id: int
    post_id: int
    user_id: int
    emoji: str
    created_at: datetime
    user: Optional[AuthorOut] = None  # Include user details when needed
    
    class Config:
        from_attributes = True


class ReactionSummary(BaseModel):
    """Summary of reactions for a post, grouped by emoji"""
    emoji: str
    count: int
    user_reacted: bool  # Whether current user has reacted with this emoji


class PostReactionsOut(BaseModel):
    """Reactions summary for a post"""
    reactions: List[ReactionSummary]  # Grouped by emoji
    total_count: int


class ReactorOut(BaseModel):
    """User who reacted (for showing who reacted)"""
    id: int
    username: str
    display_name: Optional[str] = None
    full_name: Optional[str] = None
    
    class Config:
        from_attributes = True


class EmojiReactorsOut(BaseModel):
    """List of users who reacted with a specific emoji"""
    emoji: str
    reactors: List[ReactorOut]
