from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, union_all, or_, and_

from app.core.deps import get_db, get_current_user
from app.core.s3 import generate_presigned_urls
from app.models.user import User
from app.models.post import Post
from app.models.connection import Connection, ConnectionStatus
from app.models.user_tag import UserTag
from app.models.post_audience_tag import PostAudienceTag
from app.models.tag import Tag
from app.schemas.post import PostOut

router = APIRouter(prefix="/feed", tags=["Feed"])


@router.get("/", response_model=list[PostOut])
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
    
    # Get all accepted connections where I'm either user_a or user_b
    my_connections = (
        db.query(Connection)
        .filter(
            or_(
                Connection.user_a_id == current_user.id,
                Connection.user_b_id == current_user.id,
            ),
            Connection.status == ConnectionStatus.ACCEPTED,
        )
        .all()
    )
    
    # Extract the IDs of connected users
    connected_user_ids = []
    for conn in my_connections:
        if conn.user_a_id == current_user.id:
            connected_user_ids.append(conn.user_b_id)
        else:
            connected_user_ids.append(conn.user_a_id)
    
    # Add own user ID to see own posts in feed
    connected_user_ids.append(current_user.id)
    
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
        filtered_user_ids = [
            user_id for user_id in connected_user_ids
            if user_id in tagged_user_id_set
        ]
        
        # When tag filtering is active, exclude own posts - only show posts from tagged connections
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
    
    # Filter posts based on audience settings
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
            # Get the post's audience tags
            post_audience_tags = (
                db.query(PostAudienceTag.tag_id)
                .filter(PostAudienceTag.post_id == post.id)
                .all()
            )
            post_tag_ids = [t[0] for t in post_audience_tags]
            
            if not post_tag_ids:
                # No tags specified, treat as 'all'
                filtered_posts.append(post)
                continue
            
            # Check if post author has tagged current_user with any of the required tags
            # The post author is the owner, current_user is the target
            user_tags = (
                db.query(UserTag.tag_id)
                .filter(
                    UserTag.owner_user_id == post.author_id,
                    UserTag.target_user_id == current_user.id,
                    UserTag.tag_id.in_(post_tag_ids)
                )
                .first()
            )
            
            if user_tags:
                filtered_posts.append(post)

    # Convert posts to PostOut with pre-signed URLs for photos
    result = []
    for post in filtered_posts:
        # Generate pre-signed URLs for photos
        photo_urls_presigned = []
        if post.photo_urls:
            try:
                photo_urls_presigned = generate_presigned_urls(post.photo_urls)
            except Exception as e:
                # Log error for debugging
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to generate pre-signed URLs for post {post.id}: {str(e)}")
                logger.error(f"Photo URLs: {post.photo_urls}")
                # Return empty list if pre-signed URL generation fails
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
            "audience_tags": audience_tags
        }
        result.append(PostOut(**post_dict))

    return result
