from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, union_all, or_, and_

from app.core.deps import get_db, get_current_user
from app.models.user import User
from app.models.post import Post
from app.models.connection import Connection
from app.schemas.post import PostOut

router = APIRouter(prefix="/feed", tags=["Feed"])


@router.get("/", response_model=list[PostOut])
def get_feed(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get chronological feed of posts from mutual connections only.
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
    
    # If no connections, return empty feed
    if not connected_user_ids:
        return []
    
    # Get posts from connected users, chronologically
    # Use joinedload to eager load the author relationship
    posts = (
        db.query(Post)
        .options(joinedload(Post.author))  # Eager load author
        .filter(Post.author_id.in_(connected_user_ids))
        .order_by(Post.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    return posts
