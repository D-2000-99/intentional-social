import logging
import time
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, union_all, or_, and_

from app.core.deps import get_db, get_current_user
from app.core.image_urls import build_image_path
from app.core.metrics import feed_requests_total, feed_latency_seconds
from app.models.user import User
from app.models.post import Post
from app.models.connection import Connection, ConnectionStatus
from app.models.user_tag import UserTag
from app.models.post_audience_tag import PostAudienceTag
from app.models.tag import Tag
from app.schemas.post import PostOut
from app.services.connection_service import ConnectionService
from app.services.post_service import PostService

router = APIRouter(prefix="/feed", tags=["Feed"])

logger = logging.getLogger(__name__)


@router.get("/", response_model=list[PostOut])
@router.get("", response_model=list[PostOut])  # Accept both /feed and /feed/ to avoid redirects
def get_feed(
    skip: int = 0,
    limit: int = 20,
    tag_ids: str = Query(None, description="Comma-separated tag IDs to filter by"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get chronological feed of posts from mutual connections.
    Optionally filter by tags.
    """
    # Track metrics
    feed_requests_total.inc()
    start_time = time.time()
    
    try:
        print(f"Raw tag_ids param: {tag_ids} ({type(tag_ids)})")

        # Use ConnectionService to get connected user IDs (optimized with SQL CASE)
        connected_user_ids = ConnectionService.get_connected_user_ids(
            current_user, db, include_self=True
        )
        
        # If tag filtering is requested
        if tag_ids:
            tag_id_list = [int(tid) for tid in tag_ids.split(",")]
            
            # Get users that have any of these tags (where current user is the owner)
            tagged_user_ids = (
                db.query(UserTag.target_user_id)
                .filter(
                    UserTag.owner_user_id == current_user.id,
                    UserTag.tag_id.in_(tag_id_list)
                )
                .distinct()
                .all()
            )
            tagged_user_id_set = {tu[0] for tu in tagged_user_ids}
            
            # Filter connected_user_ids to only those with the selected tags
            # Keep own user ID so we can still see own posts when filtering
            filtered_user_ids = [
                user_id for user_id in connected_user_ids
                if user_id in tagged_user_id_set or user_id == current_user.id
            ]
            
            # Update connected_user_ids to filtered list (includes own posts)
            connected_user_ids = filtered_user_ids
        
        # Get posts from connected users + self, chronologically
        # Use joinedload to eager load the author relationship
        # Handle case where list might be empty (though it always has current_user.id)
        if not connected_user_ids:
            return []
        
        posts = (
            db.query(Post)
            .options(joinedload(Post.author))  # Eager load author
            .filter(Post.author_id.in_(connected_user_ids))
            .order_by(Post.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        
        # Use PostService to filter posts by audience (eliminates code duplication)
        filtered_posts = PostService.filter_posts_by_audience(posts, current_user, db)

        # If tag filtering is requested, further filter posts by their audience tags
        # Only show posts that have at least one of the selected tags in their audience
        if tag_ids and filtered_posts:
            tag_id_list = [int(tid) for tid in tag_ids.split(",")]
            
            # Get all post IDs from filtered posts
            post_ids = [post.id for post in filtered_posts]
            
            # Get all PostAudienceTag entries for these posts in one query
            post_audience_tags_map = {}
            if post_ids:
                audience_tags = (
                    db.query(PostAudienceTag.post_id, PostAudienceTag.tag_id)
                    .filter(PostAudienceTag.post_id.in_(post_ids))
                    .all()
                )
                for post_id, tag_id in audience_tags:
                    if post_id not in post_audience_tags_map:
                        post_audience_tags_map[post_id] = []
                    post_audience_tags_map[post_id].append(tag_id)
            
            # Filter posts: only include if they have at least one of the selected tags
            # OR if they have audience_type='all' (show in all filters)
            posts_with_matching_tags = []
            for post in filtered_posts:
                if post.audience_type == 'all':
                    # Posts with 'all' audience appear in all filters
                    posts_with_matching_tags.append(post)
                elif post.audience_type == 'tags':
                    # Check if post has any of the selected tags in its audience
                    post_tag_ids = post_audience_tags_map.get(post.id, [])
                    if any(tag_id in post_tag_ids for tag_id in tag_id_list):
                        posts_with_matching_tags.append(post)
                # 'private' posts are already filtered out above
            
            filtered_posts = posts_with_matching_tags

        # Use PostService to batch load audience tags (fixes N+1 query problem)
        audience_tags_map = PostService.batch_load_audience_tags(filtered_posts, db)
        
        # Convert posts to PostOut with pre-signed URLs for photos
        result = []
        for post in filtered_posts:
            photo_urls_presigned = [build_image_path(key) for key in (post.photo_urls or [])]
            
            # Create PostOut with pre-signed URLs
            post_dict = {
                "id": post.id,
                "author_id": post.author_id,
                "content": post.content,
                "audience_type": post.audience_type,
                "photo_urls": post.photo_urls or [],
                "photo_urls_presigned": photo_urls_presigned,
                "created_at": post.created_at,
                "author": post.author,
                "audience_tags": audience_tags_map.get(post.id, [])
            }
            result.append(PostOut(**post_dict))

        return result
    finally:
        # Record latency
        duration = time.time() - start_time
        feed_latency_seconds.observe(duration)
