from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, union_all, or_, and_

from app.core.deps import get_db, get_current_user
from app.models.user import User
from app.models.post import Post
from app.models.connection import Connection
from app.models.connection_tag import ConnectionTag
from app.models.post_audience_tag import PostAudienceTag
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
    
    # Get all accepted connections where I'm either requester or recipient
    my_connections = (
        db.query(Connection)
        .filter(
            or_(
                Connection.requester_id == current_user.id,
                Connection.recipient_id == current_user.id,
            ),
            Connection.status == "accepted",
        )
        .all()
    )
    
    # Extract the IDs of connected users
    connected_user_ids = []
    for conn in my_connections:
        if conn.requester_id == current_user.id:
            connected_user_ids.append(conn.recipient_id)
        else:
            connected_user_ids.append(conn.requester_id)
    
    # Add own user ID to see own posts in feed
    connected_user_ids.append(current_user.id)
    
    # If tag filtering is requested
    if tag_ids:
        tag_id_list = [int(tid) for tid in tag_ids.split(",")]
        
        # Get connections that have any of these tags
        tagged_connections = (
            db.query(ConnectionTag.connection_id)
            .filter(ConnectionTag.tag_id.in_(tag_id_list))
            .distinct()
            .all()
        )
        tagged_connection_ids = [tc[0] for tc in tagged_connections]
        
        # Filter connected_user_ids to only those with the selected tags
        filtered_user_ids = []
        for conn in my_connections:
            if conn.id in tagged_connection_ids:
                if conn.requester_id == current_user.id:
                    filtered_user_ids.append(conn.recipient_id)
                else:
                    filtered_user_ids.append(conn.requester_id)
        
        # Always include own posts
        filtered_user_ids.append(current_user.id)
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
            
            # Get the connection between current_user and post author
            connection = next(
                (c for c in my_connections 
                 if (c.requester_id == post.author_id and c.recipient_id == current_user.id) or
                    (c.recipient_id == post.author_id and c.requester_id == current_user.id)),
                None
            )
            
            if connection:
                # Check if this connection has any of the required tags (from author's perspective)
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

    return filtered_posts
