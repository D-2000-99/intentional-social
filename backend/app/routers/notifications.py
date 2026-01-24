from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Dict
from pydantic import BaseModel

from app.core.deps import get_db, get_current_user
from app.models.user import User
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["Notifications"])


class PostSummaryRequest(BaseModel):
    post_ids: List[int]


class PostSummaryResponse(BaseModel):
    summary: Dict[int, Dict[str, bool]]  # {post_id: {'has_unread_comments': bool, 'has_unread_replies': bool}}


@router.get("/recent")
def get_recent_notifications(
    limit_posts: int = Query(50, ge=1, le=100, description="Maximum number of recent posts to check"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get recent feed post IDs and unread notification post IDs.
    Returns ordered list of recent post IDs and unread post IDs (for bell dot and jump queue).
    """
    # Get recent feed post IDs (using same connection filtering as feed)
    recent_post_ids = NotificationService.get_recent_feed_post_ids(
        db, current_user, limit=limit_posts
    )
    
    # Get unread post IDs from recent posts
    unread_post_ids = NotificationService.get_recent_unread_post_ids(
        db, current_user.id, recent_post_ids
    )
    
    return {
        "recent_post_ids": recent_post_ids,
        "unread_post_ids": unread_post_ids,
    }


@router.post("/post-summary", response_model=PostSummaryResponse)
def get_post_notification_summary(
    request: PostSummaryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get notification summary for multiple posts.
    Returns which posts have unread comments or replies.
    """
    summary = NotificationService.get_post_notification_summary(
        db, current_user.id, request.post_ids
    )
    
    return PostSummaryResponse(summary=summary)


@router.post("/posts/{post_id}/read")
def mark_post_notifications_read(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Mark all unread notifications for a post as read.
    Called when user opens comments section or scrolls to it.
    """
    count = NotificationService.mark_post_notifications_read(
        db, current_user.id, post_id
    )
    
    return {"message": "Notifications marked as read", "count": count}


@router.post("/comments/{comment_id}/read")
def mark_comment_notifications_read(
    comment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Mark all unread reply notifications for a comment as read.
    Called when user opens reply section or scrolls to it.
    """
    count = NotificationService.mark_comment_notifications_read(
        db, current_user.id, comment_id
    )
    
    return {"message": "Notifications marked as read", "count": count}


@router.post("/recent/clear")
def clear_recent_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Clear all unread notifications for the most recent 50 feed posts.
    Called on bell long-press.
    """
    # Get recent feed post IDs
    recent_post_ids = NotificationService.get_recent_feed_post_ids(
        db, current_user, limit=50
    )
    
    # Clear notifications for these posts
    count = NotificationService.clear_recent_notifications(
        db, current_user.id, recent_post_ids
    )
    
    return {"message": "Recent notifications cleared", "count": count}
