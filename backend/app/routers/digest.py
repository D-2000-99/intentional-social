"""
Digest Router

Handles the weekly digest feature - a chronological, reflective view of posts
from the current week (Sunday to Saturday).
"""
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_

from app.core.deps import get_db, get_current_user
from app.core.s3 import generate_presigned_urls
from app.core.llm import generate_weekly_summary
from app.core.metrics import digest_requests_total, digest_latency_seconds
from app.config import settings
from app.models.user import User
from app.models.post import Post
from app.models.connection import Connection, ConnectionStatus
from app.models.user_tag import UserTag
from app.models.post_audience_tag import PostAudienceTag
from app.models.tag import Tag
from app.schemas.post import PostOut
from app.services.connection_service import ConnectionService
from app.services.post_service import PostService
from app.services.storage_service import StorageService

router = APIRouter(prefix="/digest", tags=["Digest"])

logger = logging.getLogger(__name__)


def get_week_bounds(date: Optional[datetime] = None) -> tuple[datetime, datetime]:
    """
    Get the start (Sunday 00:00) and end (Saturday 23:59:59) of the week containing the given date.
    If no date is provided, uses current date.
    
    Week definition: Sunday → Saturday
    
    Args:
        date: Optional datetime (timezone-aware or naive). If None, uses current time.
              If timezone-aware, converts to naive to match client time storage.
    
    Returns:
        Tuple of (week_start, week_end) as naive datetimes (no timezone)
    """
    if date is None:
        # Use current time (naive, no timezone) to match client time storage
        date = datetime.now()
    else:
        # If timezone-aware, convert to naive to preserve the time value
        if date.tzinfo is not None:
            date = date.replace(tzinfo=None)
    
    # Get the date (without time)
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
    Rule D: Exclude memes/low-quality posts (importance <= threshold)
    
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
    
    # Get configurable thresholds
    min_importance_threshold = settings.DIGEST_MIN_IMPORTANCE_THRESHOLD
    posts_per_connection_per_day = settings.DIGEST_POSTS_PER_CONNECTION_PER_DAY
    # Ensure posts_per_connection_per_day is between 1 and 2
    posts_per_connection_per_day = max(1, min(2, posts_per_connection_per_day))
    
    # Rule D: Filter out memes and low-quality posts FIRST (before any other filtering)
    # Posts with importance_score <= threshold are excluded
    filtered_by_quality = [
        post for post in posts
        if post.importance_score is not None and post.importance_score > min_importance_threshold
    ]
    
    # Rule C: Check if week has high-importance events
    # High-importance events: weddings, family gatherings, meaningful social events
    # Low-priority: coffee, desk shots, routine selfies
    high_importance_threshold = 7.0  # Posts with importance >= 7 are considered high-importance events
    low_priority_threshold = 4.0  # Posts with importance <= 4 are considered routine
    
    has_high_importance_events = any(
        post.importance_score is not None and post.importance_score >= high_importance_threshold
        for post in filtered_by_quality
    )
    
    # Rule B: Group posts by author and date
    posts_by_author_date = defaultdict(list)
    for post in filtered_by_quality:
        if post.importance_score is None:
            # Skip posts without importance scores (not processed yet)
            continue
        
        post_date = post.created_at.date() if post.created_at else date.today()
        author_id = post.author_id
        key = (author_id, post_date)
        posts_by_author_date[key].append(post)
    
    # Apply Rule B: Keep top 1-2 highest importance posts per person per day (configurable)
    filtered_by_day = []
    for (author_id, post_date), day_posts in posts_by_author_date.items():
        # Sort by importance (descending), then by post ID (ascending) for deterministic ordering
        sorted_posts = sorted(
            day_posts,
            key=lambda p: (
                -(p.importance_score if p.importance_score is not None else 0.0),
                p.id  # Use post ID as tiebreaker for deterministic sorting
            )
        )
        
        # Keep top N posts per person per day (configurable, 1-2)
        filtered_by_day.extend(sorted_posts[:posts_per_connection_per_day])
    
    # Apply Rule C: Remove low-priority posts if high-importance events exist
    if has_high_importance_events:
        filtered_by_priority = [
            post for post in filtered_by_day
            if post.importance_score is None or post.importance_score > low_priority_threshold
        ]
    else:
        filtered_by_priority = filtered_by_day
    
    # Sort by date, importance, and post ID for deterministic final selection
    # This ensures the digest stays consistent during the week
    # Use datetime.min (naive) for fallback since posts are stored as naive datetimes
    filtered_by_priority.sort(
        key=lambda p: (
            p.created_at if p.created_at else datetime.min,
            -(p.importance_score if p.importance_score is not None else 0.0),
            p.id  # Post ID as final tiebreaker for consistency
        )
    )
    
    # Rule A: Apply weekly page cap
    final_posts = filtered_by_priority[:max_pages]
    
    return final_posts


@router.get("/", response_model=dict)
def get_digest(
    tag_filter: str = Query("all", description="Filter by tag: 'all', 'friends', 'family', or tag ID"),
    client_timestamp: Optional[str] = Query(None, description="ISO format timestamp from client system (optional)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get the weekly digest - posts from the current week (Sunday to Saturday).
    
    Uses client timestamp to determine the week, so the digest reflects the user's local time.
    
    Returns:
        {
            "posts": [PostOut],  # Chronologically ordered (oldest first)
            "weekly_summary": str | None,  # LLM-generated weekly reflection
            "week_start": str,  # ISO format
            "week_end": str  # ISO format
        }
    """
    # Track metrics
    digest_requests_total.inc()
    start_time = time.time()
    
    try:
        # Parse client timestamp or use server time as fallback
        if client_timestamp:
            try:
                # Parse ISO format timestamp (client sends local time without timezone)
                if client_timestamp.endswith('Z'):
                    # UTC format - convert to naive (shouldn't happen with our frontend, but handle it)
                    client_date = datetime.fromisoformat(client_timestamp.replace('Z', '+00:00'))
                    if client_date.tzinfo:
                        client_date = client_date.replace(tzinfo=None)
                elif '+' in client_timestamp or (client_timestamp.count('-') > 2 and 'T' in client_timestamp):
                    # Has timezone offset - parse and convert to naive
                    client_date = datetime.fromisoformat(client_timestamp)
                    if client_date.tzinfo:
                        client_date = client_date.replace(tzinfo=None)
                else:
                    # Naive datetime (local time from client) - parse as-is
                    client_date = datetime.fromisoformat(client_timestamp)
            except (ValueError, AttributeError) as e:
                # If parsing fails, fall back to server time
                logger.warning(f"Failed to parse client_timestamp '{client_timestamp}': {e}. Using server time.")
                client_date = datetime.now()
        else:
            # No client timestamp provided, use server time
            client_date = datetime.now()
        
        # Get week bounds (Sunday to Saturday) using client time
        week_start, week_end = get_week_bounds(client_date)
        
        # Use ConnectionService to get connected user IDs (optimized with SQL CASE)
        connected_user_ids = ConnectionService.get_connected_user_ids(
            current_user, db, include_self=True
        )
        
        # Filter by tag if requested
        if tag_filter and tag_filter not in ["all", "friends", "family"]:
            # Specific tag ID provided
            try:
                tag_id = int(tag_filter)
                # Get users that have this tag (where current user is the owner)
                tagged_user_ids = (
                    db.query(UserTag.target_user_id)
                    .filter(
                        UserTag.owner_user_id == current_user.id,
                        UserTag.tag_id == tag_id
                    )
                    .distinct()
                    .all()
                )
                tagged_user_id_set = {tu[0] for tu in tagged_user_ids}
                
                # Filter connected_user_ids to only those with the selected tag
                filtered_user_ids = [
                    user_id for user_id in connected_user_ids
                    if user_id in tagged_user_id_set
                ]
                
                connected_user_ids = filtered_user_ids
            except ValueError:
                # Invalid tag ID, ignore filter
                pass
        elif tag_filter in ["friends", "family"]:
            # Filter by tag color_scheme
            tag_scheme = tag_filter  # "friends" or "family"
            # Get users that have tags with this color_scheme (where current user is the owner)
            tagged_user_ids = (
                db.query(UserTag.target_user_id)
                .join(Tag, UserTag.tag_id == Tag.id)
                .filter(
                    UserTag.owner_user_id == current_user.id,
                    Tag.owner_user_id == current_user.id,
                    Tag.color_scheme == tag_scheme
                )
                .distinct()
                .all()
            )
            tagged_user_id_set = {tu[0] for tu in tagged_user_ids}
            
            # Filter connected_user_ids to only those with tags of this color_scheme
            filtered_user_ids = [
                user_id for user_id in connected_user_ids
                if user_id in tagged_user_id_set
            ]
            
            connected_user_ids = filtered_user_ids
        
        # Get posts from this week (Sunday to Saturday)
        if not connected_user_ids:
            return {
                "posts": [],
                "weekly_summary": None,
                "week_start": week_start.isoformat(),
                "week_end": week_end.isoformat()
            }
        
        # Query posts from this week
        # Since posts are stored as naive datetimes (client time) and week bounds are also naive,
        # the comparison should work correctly
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
        
        # Use PostService to filter posts by audience (eliminates code duplication)
        filtered_posts = PostService.filter_posts_by_audience(posts, current_user, db)
        
        # Apply Digest filtering rules (different from feed)
        # This is where we differentiate Digest from Feed
        digest_filtered_posts = filter_digest_posts(filtered_posts, max_pages=12)
        
        # Use PostService to batch load audience tags (fixes N+1 query problem)
        audience_tags_map = PostService.batch_load_audience_tags(digest_filtered_posts, db)
        
        # Initialize StorageService (without Redis for now)
        storage_service = StorageService(redis_client=None)
        
        # Convert to PostOut with pre-signed URLs
        result_posts = []
        posts_with_scores = []  # For weekly summary generation
        
        for post in digest_filtered_posts:
            # Generate pre-signed URLs for photos
            photo_urls_presigned = []
            if post.photo_urls:
                try:
                    photo_urls_presigned = storage_service.batch_get_presigned_urls(post.photo_urls)
                except Exception as e:
                    logger.error(f"Failed to generate pre-signed URLs for post {post.id}: {str(e)}")
                    photo_urls_presigned = []
            
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
                "audience_tags": audience_tags_map.get(post.id, []),
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
    finally:
        # Record latency
        duration = time.time() - start_time
        digest_latency_seconds.observe(duration)
