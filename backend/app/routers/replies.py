from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_
from typing import List

from app.core.deps import get_db, get_current_user
from app.models.reply import Reply
from app.models.comment import Comment
from app.models.post import Post
from app.models.user import User
from app.models.connection import Connection, ConnectionStatus
from app.schemas.reply import ReplyCreate, ReplyOut

router = APIRouter(prefix="/replies", tags=["Replies"])


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


@router.post("/", response_model=ReplyOut, status_code=status.HTTP_201_CREATED)
def create_reply(
    reply_data: ReplyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a reply to a comment.
    Only users who can see the comment can reply to it.
    (Must be connected to both the post author AND the comment author, or be the post/comment author)
    """
    # Verify comment exists and load its post
    comment = (
        db.query(Comment)
        .options(joinedload(Comment.post))
        .filter(Comment.id == reply_data.comment_id)
        .first()
    )
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found"
        )
    
    post = comment.post
    
    # Check if current user can see the comment (same rules as viewing comments)
    # Post author can always reply
    is_post_author = (post.author_id == current_user.id)
    # Comment author can always reply to their own comment
    is_comment_author = (comment.author_id == current_user.id)
    
    if not is_post_author and not is_comment_author:
        # Check if connected to post author
        if not are_connected(db, current_user.id, post.author_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only reply to comments on posts from your connections"
            )
        # Check if connected to comment author (mutual friend requirement)
        if not are_connected(db, current_user.id, comment.author_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only reply to comments from mutual connections"
            )
    
    # Validate content is not empty
    if not reply_data.content or not reply_data.content.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reply content cannot be empty"
        )
    
    # Create reply
    new_reply = Reply(
        comment_id=reply_data.comment_id,
        author_id=current_user.id,
        content=reply_data.content.strip()
    )
    db.add(new_reply)
    db.commit()
    db.refresh(new_reply)
    
    # Load author relationship
    new_reply = (
        db.query(Reply)
        .options(joinedload(Reply.author))
        .filter(Reply.id == new_reply.id)
        .first()
    )
    
    return ReplyOut(
        id=new_reply.id,
        comment_id=new_reply.comment_id,
        author_id=new_reply.author_id,
        content=new_reply.content,
        created_at=new_reply.created_at,
        author=new_reply.author
    )


@router.get("/comment/{comment_id}", response_model=List[ReplyOut])
def get_comment_replies(
    comment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get all replies for a comment with mutual connection filtering.
    
    Visibility rules (same as comments):
    - Post author can see all replies
    - Comment author can see all replies to their comment
    - Other users can only see replies from users they are mutually connected with
    """
    # Verify comment exists and load its post
    comment = (
        db.query(Comment)
        .options(joinedload(Comment.post))
        .filter(Comment.id == comment_id)
        .first()
    )
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found"
        )
    
    post = comment.post
    
    # Check if current user can see the comment
    is_post_author = (post.author_id == current_user.id)
    is_comment_author = (comment.author_id == current_user.id)
    
    if not is_post_author and not is_comment_author:
        # Check if connected to post author
        if not are_connected(db, current_user.id, post.author_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view replies on posts from your connections"
            )
    
    # Get all replies for this comment with author loaded
    all_replies = (
        db.query(Reply)
        .options(joinedload(Reply.author))
        .filter(Reply.comment_id == comment_id)
        .order_by(Reply.created_at.asc())
        .all()
    )
    
    # Filter replies based on mutual connection rules
    visible_replies = []
    
    for reply in all_replies:
        # Post author can see all replies
        if is_post_author:
            visible_replies.append(reply)
        # Comment author can see all replies to their comment
        elif is_comment_author:
            visible_replies.append(reply)
        # Reply author can always see their own reply
        elif reply.author_id == current_user.id:
            visible_replies.append(reply)
        else:
            # For other users: can only see reply if they are connected to the reply author
            is_connected_to_reply_author = are_connected(db, current_user.id, reply.author_id)
            
            if is_connected_to_reply_author:
                visible_replies.append(reply)
    
    # Convert to ReplyOut
    result = []
    for reply in visible_replies:
        result.append(ReplyOut(
            id=reply.id,
            comment_id=reply.comment_id,
            author_id=reply.author_id,
            content=reply.content,
            created_at=reply.created_at,
            author=reply.author
        ))
    
    return result
