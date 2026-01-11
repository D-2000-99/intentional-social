import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_

from app.config import settings
from app.core.deps import get_db, get_moderator_user
from app.core.s3 import delete_photo_from_s3, generate_presigned_urls
from app.models.user import User
from app.models.post import Post
from app.models.comment import Comment
from app.models.connection import Connection
from app.models.tag import Tag
from app.models.connection_tag import ConnectionTag
from app.models.post_audience_tag import PostAudienceTag
from app.models.email_verification import EmailVerification
from app.models.reported_post import ReportedPost
from app.schemas.moderation import UserOut, ReportedPostOut

router = APIRouter(prefix="/moderation", tags=["Moderation"])
logger = logging.getLogger(__name__)


@router.get("/reported-posts", response_model=List[ReportedPostOut])
def get_reported_posts(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    unresolved_only: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_moderator_user),
):
    """Get all reported posts, optionally filtered to unresolved only."""
    query = (
        db.query(ReportedPost)
        .options(
            joinedload(ReportedPost.post).joinedload(Post.author),
            joinedload(ReportedPost.reported_by)
        )
    )
    
    if unresolved_only:
        query = query.filter(ReportedPost.resolved_at.is_(None))
    
    # Order by unresolved first, then by creation date
    reports = (
        query.order_by(
            ReportedPost.resolved_at.is_(None).desc(),  # Unresolved first
            ReportedPost.created_at.desc()
        )
        .offset(skip)
        .limit(limit)
        .all()
    )
    
    result = []
    for report in reports:
        # Build post dict
        post_dict = None
        if report.post:
            # Generate pre-signed URLs for photos
            photo_urls_presigned = []
            if report.post.photo_urls:
                try:
                    photo_urls_presigned = generate_presigned_urls(report.post.photo_urls)
                except Exception as e:
                    logger.error(f"Failed to generate pre-signed URLs for post {report.post.id}: {str(e)}")
                    photo_urls_presigned = []
            
            post_dict = {
                "id": report.post.id,
                "author_id": report.post.author_id,
                "content": report.post.content[:200] + "..." if len(report.post.content) > 200 else report.post.content,
                "created_at": report.post.created_at.isoformat(),
                "photo_urls": report.post.photo_urls or [],
                "photo_urls_presigned": photo_urls_presigned,
                "author": {
                    "id": report.post.author.id,
                    "email": report.post.author.email,
                    "username": report.post.author.username,
                } if report.post.author else None
            }
        
        result.append(ReportedPostOut(
            id=report.id,
            post_id=report.post_id,
            reported_by_id=report.reported_by_id,
            reason=report.reason,
            created_at=report.created_at,
            resolved_at=report.resolved_at,
            resolved_by_id=report.resolved_by_id,
            post=post_dict,
            reported_by=UserOut.model_validate(report.reported_by) if report.reported_by else None,
        ))
    
    return result


@router.post("/reported-posts/{report_id}/resolve", status_code=status.HTTP_200_OK)
def resolve_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_moderator_user),
):
    """Mark a report as resolved."""
    from datetime import datetime, timezone
    
    report = db.query(ReportedPost).filter(ReportedPost.id == report_id).first()
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found"
        )
    
    if report.resolved_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Report is already resolved"
        )
    
    report.resolved_at = datetime.now(timezone.utc)
    report.resolved_by_id = current_user.id
    db.commit()
    
    return {"message": "Report resolved successfully"}


@router.delete("/posts/{post_id}", status_code=status.HTTP_200_OK)
def delete_post(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_moderator_user),
):
    """
    Delete a post by its ID. Moderators can delete any post.
    
    Deletion order:
    1. Delete PostAudienceTag entries (foreign key constraint)
    2. Delete ReportedPost entries for this post
    3. Delete photos from S3 (if any)
    4. Delete the post itself (comments cascade delete automatically)
    """
    # Get the post
    post = db.query(Post).filter(Post.id == post_id).first()
    
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )
    
    try:
        # Step 1: Delete PostAudienceTag entries (foreign key constraint)
        db.query(PostAudienceTag).filter(PostAudienceTag.post_id == post_id).delete()
        
        # Step 2: Delete ReportedPost entries for this post
        db.query(ReportedPost).filter(ReportedPost.post_id == post_id).delete()
        
        # Step 3: Delete photos from S3 (if any)
        if post.photo_urls:
            for s3_key in post.photo_urls:
                try:
                    delete_photo_from_s3(s3_key)
                except Exception as e:
                    logger.error(f"Failed to delete photo from S3 ({s3_key}): {str(e)}")
                    # Continue even if S3 deletion fails
        
        # Step 4: Delete the post itself (comments will cascade delete)
        db.delete(post)
        db.commit()
        
        logger.info(f"Post {post_id} deleted by moderator {current_user.id}")
        return {"message": "Post deleted successfully"}
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting post {post_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete post: {str(e)}"
        )


@router.get("/users", response_model=List[UserOut])
def get_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_moderator_user),
):
    """Get all users with pagination and optional search."""
    query = db.query(User)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                User.email.ilike(search_term),
                User.username.ilike(search_term),
                User.full_name.ilike(search_term),
            )
        )
    
    users = query.order_by(User.created_at.desc()).offset(skip).limit(limit).all()
    return [UserOut.model_validate(user) for user in users]


@router.post("/users/{user_id}/ban", status_code=status.HTTP_200_OK)
def ban_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_moderator_user),
):
    """Ban a user."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot ban yourself"
        )
    
    user.is_banned = True
    db.commit()
    db.refresh(user)
    
    logger.info(f"User {user_id} banned by moderator {current_user.id}")
    return {"message": f"User {user.email} has been banned"}


@router.post("/users/{user_id}/unban", status_code=status.HTTP_200_OK)
def unban_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_moderator_user),
):
    """Unban a user."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.is_banned = False
    db.commit()
    db.refresh(user)
    
    logger.info(f"User {user_id} unbanned by moderator {current_user.id}")
    return {"message": f"User {user.email} has been unbanned"}


@router.delete("/users/{user_id}", status_code=status.HTTP_200_OK)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_moderator_user),
):
    """
    Delete a user and all associated data.
    Deletes in proper order to respect foreign key constraints and cleans up S3 images.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete yourself"
        )
    
    try:
        # Step 1: Delete S3 images
        # Delete post photos
        for post in user.posts:
            if post.photo_urls:
                for s3_key in post.photo_urls:
                    try:
                        delete_photo_from_s3(s3_key)
                    except Exception as e:
                        logger.error(f"Failed to delete photo from S3 ({s3_key}): {str(e)}")
                        # Continue even if S3 deletion fails
        
        # Delete user avatar if it's an S3 key
        if user.avatar_url and user.avatar_url.startswith(settings.S3_AVATAR_PREFIX):
            try:
                delete_photo_from_s3(user.avatar_url)
            except Exception as e:
                logger.error(f"Failed to delete avatar from S3 ({user.avatar_url}): {str(e)}")
        
        # Step 2: Delete PostAudienceTag records (via post.audience_tags)
        # We need to do this before deleting posts
        for post in user.posts:
            db.query(PostAudienceTag).filter(PostAudienceTag.post_id == post.id).delete()
        
        # Step 3: Comments will be deleted via cascade when posts are deleted
        # But we also have direct user.comments relationship, so we'll delete them explicitly
        db.query(Comment).filter(Comment.author_id == user_id).delete()
        
        # Step 4: Delete Post records (cascade will handle comments via post.comments)
        db.query(Post).filter(Post.author_id == user_id).delete()
        
        # Step 5: Delete ConnectionTag records where user is requester or recipient
        # First get all connections involving this user
        connections = db.query(Connection).filter(
            or_(Connection.requester_id == user_id, Connection.recipient_id == user_id)
        ).all()
        connection_ids = [conn.id for conn in connections]
        if connection_ids:
            db.query(ConnectionTag).filter(ConnectionTag.connection_id.in_(connection_ids)).delete()
        
        # Step 6: Delete Connection records
        db.query(Connection).filter(
            or_(Connection.requester_id == user_id, Connection.recipient_id == user_id)
        ).delete()
        
        # Step 7: Delete Tag records
        db.query(Tag).filter(Tag.user_id == user_id).delete()
        
        # Step 8: Delete EmailVerification records
        db.query(EmailVerification).filter(EmailVerification.user_id == user_id).delete()
        
        # Step 9: Delete ReportedPost records where user is reporter
        db.query(ReportedPost).filter(ReportedPost.reported_by_id == user_id).delete()
        
        # Step 10: Finally delete User record
        db.delete(user)
        db.commit()
        
        logger.info(f"User {user_id} deleted by moderator {current_user.id}")
        return {"message": f"User {user.email} has been deleted"}
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete user: {str(e)}"
        )

