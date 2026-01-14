"""
Digest Router

Handles the weekly digest feature - a chronological, reflective view of posts
from the current week (Sunday to Saturday).
"""
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_

from app.core.deps import get_db, get_current_user
from app.core.s3 import generate_presigned_urls
from app.core.llm import generate_weekly_summary
from app.models.user import User
from app.models.post import Post
from app.models.connection import Connection, ConnectionStatus
from app.models.connection_tag import ConnectionTag
from app.models.post_audience_tag import PostAudienceTag
from app.models.tag import Tag
from app.schemas.post import PostOut

router = APIRouter(prefix="/digest", tags=["Digest"])


def get_week_bounds(date: Optional[datetime] = None) -> tuple[datetime, datetime]:
    """
    Get the start (Sunday 00:00) and end (Saturday 23:59:59) of the week containing the given date.
    If no date is provided, uses current date.
    
    Week definition: Sunday → Saturday
    """
    if date is None:
        date = datetime.now(timezone.utc)
    
    # Get the date (without time) in UTC
    date_only = date.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Find Sunday (weekday 6 in Python: Monday=0, Sunday=6)
    days_since_sunday = (date_only.weekday() + 1) % 7
    week_start = date_only - timedelta(days=days_since_sunday)
    
    # Week ends on Saturday 23:59:59
    week_end = week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)
    
    return week_start, week_end


def filter_digest_posts(posts: list[Post], max_pages: int = 12) -> list[Post]:
    """
    Apply Digest filtering rules to posts to differentiate from Feed:
    
    Rule A: Weekly page cap (max 10-12 pages)
    Rule B: Per-day compression (1-2 highest importance per person per day)
    Rule C: Low-priority removal (exclude routine posts if high-importance events exist)
    
    Args:
        posts: List of posts with importance_score and digest_summary
        max_pages: Maximum number of posts to include (default: 12)
    
    Returns:
        Filtered list of posts
    """
    from collections import defaultdict
    from datetime import date
    
    if not posts:
        return []
    
    # Rule C: Check if week has high-importance events
    # High-importance events: weddings, family gatherings, meaningful social events
    # Low-priority: coffee, desk shots, routine selfies
    high_importance_threshold = 7.0  # Posts with importance >= 7 are considered high-importance events
    low_priority_threshold = 4.0  # Posts with importance <= 4 are considered routine
    
    has_high_importance_events = any(
        post.importance_score is not None and post.importance_score >= high_importance_threshold
        for post in posts
    )
    
    # Rule B: Group posts by author and date
    posts_by_author_date = defaultdict(list)
    for post in posts:
        if post.importance_score is None:
            # Skip posts without importance scores (not processed yet)
            continue
        
        post_date = post.created_at.date() if post.created_at else date.today()
        author_id = post.author_id
        key = (author_id, post_date)
        posts_by_author_date[key].append(post)
    
    # Apply Rule B: Keep 1-2 highest importance posts per person per day
    filtered_by_day = []
    for (author_id, post_date), day_posts in posts_by_author_date.items():
        # Sort by importance (descending)
        sorted_posts = sorted(
            day_posts,
            key=lambda p: p.importance_score if p.importance_score is not None else 0.0,
            reverse=True
        )
        
        # Keep top 2 posts per person per day
        filtered_by_day.extend(sorted_posts[:2])
    
    # Apply Rule C: Remove low-priority posts if high-importance events exist
    if has_high_importance_events:
        filtered_by_priority = [
            post for post in filtered_by_day
            if post.importance_score is None or post.importance_score > low_priority_threshold
        ]
    else:
        filtered_by_priority = filtered_by_day
    
    # Sort by date and importance for final selection
    filtered_by_priority.sort(
        key=lambda p: (
            p.created_at if p.created_at else datetime.min.replace(tzinfo=timezone.utc),
            -(p.importance_score if p.importance_score is not None else 0.0)
        )
    )
    
    # Rule A: Apply weekly page cap
    final_posts = filtered_by_priority[:max_pages]
    
    return final_posts


@router.get("/", response_model=dict)
def get_digest(
    tag_filter: str = Query("all", description="Filter by tag: 'all', 'friends', 'family', or tag ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get the weekly digest - posts from the current week (Sunday to Saturday).
    
    Returns:
        {
            "posts": [PostOut],  # Chronologically ordered (oldest first)
            "weekly_summary": str | None,  # LLM-generated weekly reflection
            "week_start": str,  # ISO format
            "week_end": str  # ISO format
        }
    """
    # Get week bounds (Sunday to Saturday)
    week_start, week_end = get_week_bounds()
    
    # Get all accepted connections
    my_connections = (
        db.query(Connection)
        .filter(
            or_(
                Connection.requester_id == current_user.id,
                Connection.recipient_id == current_user.id,
            ),
            Connection.status == ConnectionStatus.ACCEPTED,
        )
        .all()
    )
    
    # Extract connected user IDs
    connected_user_ids = []
    for conn in my_connections:
        if conn.requester_id == current_user.id:
            connected_user_ids.append(conn.recipient_id)
        else:
            connected_user_ids.append(conn.requester_id)
    
    # Add own user ID to see own posts
    connected_user_ids.append(current_user.id)
    
    # Filter by tag if requested
    if tag_filter and tag_filter not in ["all", "friends", "family"]:
        # Specific tag ID provided
        try:
            tag_id = int(tag_filter)
            tagged_connections = (
                db.query(ConnectionTag.connection_id)
                .filter(ConnectionTag.tag_id == tag_id)
                .distinct()
                .all()
            )
            tagged_connection_ids = [tc[0] for tc in tagged_connections]
            
            filtered_user_ids = []
            for conn in my_connections:
                if conn.id in tagged_connection_ids:
                    if conn.requester_id == current_user.id:
                        filtered_user_ids.append(conn.recipient_id)
                    else:
                        filtered_user_ids.append(conn.requester_id)
            
            connected_user_ids = filtered_user_ids
        except ValueError:
            # Invalid tag ID, ignore filter
            pass
    elif tag_filter in ["friends", "family"]:
        # Filter by tag color_scheme
        tag_scheme = tag_filter  # "friends" or "family"
        tagged_connections = (
            db.query(ConnectionTag.connection_id)
            .join(Tag, ConnectionTag.tag_id == Tag.id)
            .filter(Tag.user_id == current_user.id)
            .filter(Tag.color_scheme == tag_scheme)
            .distinct()
            .all()
        )
        tagged_connection_ids = [tc[0] for tc in tagged_connections]
        
        filtered_user_ids = []
        for conn in my_connections:
            if conn.id in tagged_connection_ids:
                if conn.requester_id == current_user.id:
                    filtered_user_ids.append(conn.recipient_id)
                else:
                    filtered_user_ids.append(conn.requester_id)
        
        connected_user_ids = filtered_user_ids
    
    # Get posts from this week (Sunday to Saturday)
    if not connected_user_ids:
        return {
            "posts": [],
            "weekly_summary": None,
            "week_start": week_start.isoformat(),
            "week_end": week_end.isoformat()
        }
    
    posts = (
        db.query(Post)
        .options(joinedload(Post.author))
        .filter(
            Post.author_id.in_(connected_user_ids),
            Post.created_at >= week_start,
            Post.created_at <= week_end
        )
        .order_by(Post.created_at.asc())  # Oldest first for chronological digest
        .all()
    )
    
    # Filter posts based on audience settings (same logic as feed)
    filtered_posts = []
    for post in posts:
        # Always show own posts
        if post.author_id == current_user.id:
            filtered_posts.append(post)
            continue
            
        # Show posts with audience_type = 'all'
        if post.audience_type == 'all':
            filtered_posts.append(post)
            continue
        
        # Skip private posts from others
        if post.audience_type == 'private':
            continue
        
        # For tag-based audience, check if current user has the required tags
        if post.audience_type == 'tags':
            post_audience_tags = (
                db.query(PostAudienceTag.tag_id)
                .filter(PostAudienceTag.post_id == post.id)
                .all()
            )
            post_tag_ids = [t[0] for t in post_audience_tags]
            
            if not post_tag_ids:
                filtered_posts.append(post)
                continue
            
            connection = next(
                (c for c in my_connections 
                 if (c.requester_id == post.author_id and c.recipient_id == current_user.id) or
                    (c.recipient_id == post.author_id and c.requester_id == current_user.id)),
                None
            )
            
            if connection:
                connection_tags = (
                    db.query(ConnectionTag.tag_id)
                    .filter(
                        ConnectionTag.connection_id == connection.id,
                        ConnectionTag.tag_id.in_(post_tag_ids)
                    )
                    .first()
                )
                
                if connection_tags:
                    filtered_posts.append(post)
    
    # Apply Digest filtering rules (different from feed)
    # This is where we differentiate Digest from Feed
    digest_filtered_posts = filter_digest_posts(filtered_posts, max_pages=12)
    
    # Convert to PostOut with pre-signed URLs
    result_posts = []
    posts_with_scores = []  # For weekly summary generation
    
    for post in digest_filtered_posts:
        # Generate pre-signed URLs for photos
        photo_urls_presigned = []
        if post.photo_urls:
            try:
                photo_urls_presigned = generate_presigned_urls(post.photo_urls)
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to generate pre-signed URLs for post {post.id}: {str(e)}")
                photo_urls_presigned = []
        
        # Get audience tags
        audience_tags = []
        if post.audience_type == "tags":
            post_audience_tags = (
                db.query(PostAudienceTag)
                .filter(PostAudienceTag.post_id == post.id)
                .all()
            )
            tag_ids = [pat.tag_id for pat in post_audience_tags]
            if tag_ids:
                tags = db.query(Tag).filter(Tag.id.in_(tag_ids)).all()
                audience_tags = tags
        
        # Create PostOut
        post_dict = {
            "id": post.id,
            "author_id": post.author_id,
            "content": post.content,
            "audience_type": post.audience_type,
            "photo_urls": post.photo_urls or [],
            "photo_urls_presigned": photo_urls_presigned,
            "created_at": post.created_at,
            "author": post.author,
            "audience_tags": audience_tags,
            "digest_summary": post.digest_summary  # Include digest summary if available
        }
        result_posts.append(PostOut(**post_dict))
        
        # Collect for weekly summary
        if post.importance_score is not None:
            posts_with_scores.append({
                "importance_score": post.importance_score,
                "summary": post.digest_summary
            })
    
    # Generate weekly summary
    weekly_summary = None
    if posts_with_scores:
        weekly_summary = generate_weekly_summary(posts_with_scores)
    
    return {
        "posts": result_posts,
        "weekly_summary": weekly_summary,
        "week_start": week_start.isoformat(),
        "week_end": week_end.isoformat()
    }

