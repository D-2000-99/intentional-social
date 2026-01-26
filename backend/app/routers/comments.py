from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_, update
from typing import List

from app.core.deps import get_db, get_current_user
from app.models.comment import Comment
from app.models.post import Post
from app.models.post_stats import PostStats
from app.models.user import User
from app.models.connection import Connection, ConnectionStatus
from app.schemas.comment import CommentCreate, CommentOut
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/comments", tags=["Comments"])


def are_connected(db: Session, user1_id: int, user2_id: int) -> bool:
    """Check if two users are connected (accepted connection)."""
    # Normalize: ensure user_a_id < user_b_id
    user_a_id = min(user1_id, user2_id)
    user_b_id = max(user1_id, user2_id)
    
    connection = (
        db.query(Connection)
        .filter(
            Connection.user_a_id == user_a_id,
            Connection.user_b_id == user_b_id,
            Connection.status == ConnectionStatus.ACCEPTED,
        )
        .first()
    )
    return connection is not None


@router.post("/", response_model=CommentOut, status_code=status.HTTP_201_CREATED)
def create_comment(
    comment_data: CommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a comment on a post.
    Only users connected to the post author can comment.
    """
    # Verify post exists
    post = db.query(Post).filter(Post.id == comment_data.post_id).first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )
    
    # Check if current user is connected to post author
    # Users can always comment on their own posts
    if post.author_id != current_user.id:
        if not are_connected(db, current_user.id, post.author_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only comment on posts from your connections"
            )
    
    # Validate content is not empty
    if not comment_data.content or not comment_data.content.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Comment content cannot be empty"
        )
    
    # Create comment
    new_comment = Comment(
        post_id=comment_data.post_id,
        author_id=current_user.id,
        content=comment_data.content.strip()
    )
    db.add(new_comment)
    
    # Update or create PostStats for this post
    post_stats = db.query(PostStats).filter(PostStats.post_id == comment_data.post_id).first()
    if not post_stats:
        post_stats = PostStats(post_id=comment_data.post_id, comment_count=0)
        db.add(post_stats)
    
    # Increment comment count
    post_stats.comment_count = post_stats.comment_count + 1
    
    db.commit()
    db.refresh(new_comment)
    
    # Create notification for post author
    NotificationService.create_comment_notification(
        db, comment_data.post_id, current_user.id
    )
    
    # Load author relationship
    new_comment = (
        db.query(Comment)
        .options(joinedload(Comment.author))
        .filter(Comment.id == new_comment.id)
        .first()
    )
    
    return CommentOut(
        id=new_comment.id,
        post_id=new_comment.post_id,
        author_id=new_comment.author_id,
        content=new_comment.content,
        created_at=new_comment.created_at,
        author=new_comment.author
    )


@router.get("/posts/{post_id}", response_model=List[CommentOut])
def get_post_comments(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get all comments for a post with mutual connection filtering.
    
    Visibility rules:
    - Post author can see all comments
    - Other users can only see comments from users they are mutually connected with
      (i.e., they must be connected to both the post author AND the comment author)
    """
    # Verify post exists
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )
    
    # Check if current user can see the post (must be connected to post author)
    if post.author_id != current_user.id:
        if not are_connected(db, current_user.id, post.author_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view comments on posts from your connections"
            )
    
    # Get all comments for this post with author loaded
    all_comments = (
        db.query(Comment)
        .options(joinedload(Comment.author))
        .filter(Comment.post_id == post_id)
        .order_by(Comment.created_at.asc())
        .all()
    )
    
    # Filter comments based on mutual connection rules
    visible_comments = []
    
    # If user is post author, they can see all comments
    is_post_author = (post.author_id == current_user.id)
    
    # Cache connection status to post author (we already verified user can see the post)
    # So if not post author, they must be connected
    is_connected_to_post_author = is_post_author or are_connected(db, current_user.id, post.author_id)
    
    for comment in all_comments:
        # Post author can always see all comments
        if is_post_author:
            visible_comments.append(comment)
        # Comment author can always see their own comment
        elif comment.author_id == current_user.id:
            visible_comments.append(comment)
        else:
            # For other users: can only see comment if they are connected to both
            # the post author AND the comment author (mutual connection)
            # We already know is_connected_to_post_author is true at this point
            is_connected_to_comment_author = are_connected(db, current_user.id, comment.author_id)
            
            if is_connected_to_comment_author:
                visible_comments.append(comment)
    
    # Get notification summary for comments
    comment_ids = [c.id for c in visible_comments]
    comment_notification_summary = NotificationService.get_comment_notification_summary(
        db, current_user.id, comment_ids
    )
    
    # Convert to CommentOut
    result = []
    for comment in visible_comments:
        result.append(CommentOut(
            id=comment.id,
            post_id=comment.post_id,
            author_id=comment.author_id,
            content=comment.content,
            created_at=comment.created_at,
            author=comment.author,
            has_unread_reply=comment_notification_summary.get(comment.id, False)
        ))
    
    return result


@router.get("/posts/{post_id}/count")
def get_post_comment_count(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get the count of visible comments for a post.
    Uses the same visibility rules as get_post_comments.
    """
    # Verify post exists
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )
    
    # Check if current user can see the post (must be connected to post author)
    if post.author_id != current_user.id:
        if not are_connected(db, current_user.id, post.author_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view comments on posts from your connections"
            )
    
    # Get all comments for this post
    all_comments = (
        db.query(Comment)
        .filter(Comment.post_id == post_id)
        .all()
    )
    
    # Count visible comments based on mutual connection rules
    is_post_author = (post.author_id == current_user.id)
    is_connected_to_post_author = is_post_author or are_connected(db, current_user.id, post.author_id)
    
    count = 0
    for comment in all_comments:
        # Post author can always see all comments
        if is_post_author:
            count += 1
        # Comment author can always see their own comment
        elif comment.author_id == current_user.id:
            count += 1
        else:
            # For other users: can only see comment if they are connected to both
            # the post author AND the comment author (mutual connection)
            if is_connected_to_post_author:
                is_connected_to_comment_author = are_connected(db, current_user.id, comment.author_id)
                if is_connected_to_comment_author:
                    count += 1
    
    return {"count": count}
