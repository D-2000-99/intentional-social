from datetime import datetime
from pydantic import BaseModel
from typing import Optional, List, TYPE_CHECKING
from app.schemas.post import AuthorOut

if TYPE_CHECKING:
    from app.schemas.reply import ReplyOut


class CommentCreate(BaseModel):
    post_id: int
    content: str


class ReplyOutBase(BaseModel):
    """Inline reply schema to avoid circular imports."""
    id: int
    comment_id: int
    author_id: int
    content: str
    created_at: datetime
    author: AuthorOut

    class Config:
        from_attributes = True


class CommentOut(BaseModel):
    id: int
    post_id: int
    author_id: int
    content: str
    created_at: datetime
    author: AuthorOut
    has_unread_reply: Optional[bool] = False  # Whether user has unread replies on this comment

    class Config:
        from_attributes = True


class CommentWithRepliesOut(BaseModel):
    """Comment with its replies included."""
    id: int
    post_id: int
    author_id: int
    content: str
    created_at: datetime
    author: AuthorOut
    replies: List[ReplyOutBase] = []

    class Config:
        from_attributes = True

