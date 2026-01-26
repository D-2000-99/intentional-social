import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, func

from app.config import settings
from app.core.deps import get_db, get_moderator_user
from app.core.s3 import delete_photo_from_s3, generate_presigned_urls
from app.models.user import User
from app.models.post import Post
from app.models.comment import Comment
from app.models.post_stats import PostStats
from app.models.connection import Connection
from app.models.tag import Tag
from app.models.user_tag import UserTag
from app.models.post_audience_tag import PostAudienceTag
from app.models.reported_post import ReportedPost
# MVP TEMPORARY: Registration request model - remove when moving beyond MVP
from app.models.registration_request import RegistrationRequest, RegistrationStatus
from app.schemas.moderation import UserOut, ReportedPostOut, RegistrationRequestOut

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
        db.query(PostAudienceTag).filter(PostAudienceTag.post_id == post_id).delete(synchronize_session=False)
        
        # Step 2: Delete ReportedPost entries for this post
        db.query(ReportedPost).filter(ReportedPost.post_id == post_id).delete(synchronize_session=False)
        
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
        # Step 1: Delete S3/R2 images
        # Delete post photos
        for post in user.posts:
            if post.photo_urls:
                for s3_key in post.photo_urls:
                    try:
                        delete_photo_from_s3(s3_key)
                    except Exception as e:
                        logger.error(f"Failed to delete photo from storage ({s3_key}): {str(e)}")
                        # Continue even if storage deletion fails
        
        # Delete user avatar if it's stored in S3/R2
        # Check if avatar_url is an S3 key (starts with prefix) or contains storage indicators
        if user.avatar_url:
            # Check if it's an S3 key (starts with avatar prefix) or is a storage path
            avatar_prefix = settings.S3_AVATAR_PREFIX
            if user.avatar_url.startswith(avatar_prefix) or "/" in user.avatar_url:
                try:
                    # Extract the S3 key if it's a full URL, otherwise use as-is
                    s3_key = user.avatar_url
                    if "amazonaws.com" in user.avatar_url or "r2.cloudflarestorage.com" in user.avatar_url:
                        # Extract key from URL if it's a full URL
                        # Format: https://bucket.endpoint.com/key or https://endpoint.com/bucket/key
                        parts = user.avatar_url.split("/")
                        s3_key = "/".join(parts[-2:]) if len(parts) > 2 else parts[-1]
                    delete_photo_from_s3(s3_key)
                except Exception as e:
                    logger.error(f"Failed to delete avatar from storage ({user.avatar_url}): {str(e)}")
        
        # Step 2: Get all post IDs before deletion for cleanup
        post_ids = [post.id for post in user.posts]
        
        # Step 3: Delete PostAudienceTag records (via post.audience_tags)
        # We need to do this before deleting posts
        if post_ids:
            db.query(PostAudienceTag).filter(PostAudienceTag.post_id.in_(post_ids)).delete(synchronize_session=False)
        
        # Step 4: Delete ReportedPost records for user's posts (before deleting posts)
        if post_ids:
            db.query(ReportedPost).filter(ReportedPost.post_id.in_(post_ids)).delete(synchronize_session=False)
        
        # Step 5: Delete Comments authored by this user (including comments on other users' posts)
        # First, get post_ids and comment counts before deletion to update PostStats
        comments_to_delete = db.query(Comment.post_id, func.count(Comment.id).label('count')).filter(
            Comment.author_id == user_id
        ).group_by(Comment.post_id).all()
        
        # Delete the comments
        db.query(Comment).filter(Comment.author_id == user_id).delete(synchronize_session=False)
        
        # Update PostStats for affected posts
        for post_id, comment_count in comments_to_delete:
            post_stats = db.query(PostStats).filter(PostStats.post_id == post_id).first()
            if post_stats:
                post_stats.comment_count = max(0, post_stats.comment_count - comment_count)
        
        # Step 6: Delete Post records (cascade will handle comments via post.comments)
        db.query(Post).filter(Post.author_id == user_id).delete(synchronize_session=False)
        
        # Step 7: Delete UserTag records where user is owner or target
        # UserTag represents tags assigned to users (owner tags target)
        db.query(UserTag).filter(
            or_(UserTag.owner_user_id == user_id, UserTag.target_user_id == user_id)
        ).delete(synchronize_session=False)
        
        # Step 8: Delete Connection records
        db.query(Connection).filter(
            or_(Connection.user_a_id == user_id, Connection.user_b_id == user_id)
        ).delete(synchronize_session=False)
        
        # Step 9: Delete Tag records (tags owned by this user)
        db.query(Tag).filter(Tag.owner_user_id == user_id).delete(synchronize_session=False)
        
        # Step 10: Delete ReportedPost records where user is reporter
        db.query(ReportedPost).filter(ReportedPost.reported_by_id == user_id).delete(synchronize_session=False)
        
        # Step 11: Delete ReportedPost records where user resolved reports (moderator action)
        db.query(ReportedPost).filter(ReportedPost.resolved_by_id == user_id).delete(synchronize_session=False)
        
        # Step 12: Finally delete User record
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


# ============================================================================
# MVP TEMPORARY: Registration Request Management - Remove when moving beyond MVP
# ============================================================================
# These endpoints allow moderators to approve or deny user registration requests
# during the MVP phase. When moving beyond MVP, remove these endpoints and
# update the OAuth callback in backend/app/routers/auth.py to create users directly.
# ============================================================================

@router.get("/registration-requests", response_model=List[RegistrationRequestOut])
def get_registration_requests(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status_filter: Optional[str] = Query(None, description="Filter by status: pending, approved, denied"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_moderator_user),
):
    """
    Get all registration requests - MVP TEMPORARY FEATURE.
    
    TODO: Remove this endpoint when moving beyond MVP phase.
    """
    query = db.query(RegistrationRequest).options(
        joinedload(RegistrationRequest.reviewed_by)
    )
    
    if status_filter:
        try:
            status_enum = RegistrationStatus[status_filter.upper()]
            query = query.filter(RegistrationRequest.status == status_enum)
        except KeyError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status filter: {status_filter}. Must be one of: pending, approved, denied"
            )
    
    requests = (
        query.order_by(RegistrationRequest.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    
    result = []
    for req in requests:
        result.append(RegistrationRequestOut(
            id=req.id,
            email=req.email,
            google_id=req.google_id,
            full_name=req.full_name,
            picture_url=req.picture_url,
            status=req.status.value,
            created_at=req.created_at,
            reviewed_at=req.reviewed_at,
            reviewed_by_id=req.reviewed_by_id,
            reviewed_by=UserOut.model_validate(req.reviewed_by) if req.reviewed_by else None,
        ))
    
    return result


@router.post("/registration-requests/{request_id}/approve", status_code=status.HTTP_200_OK)
def approve_registration_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_moderator_user),
):
    """
    Approve a registration request and create the user account - MVP TEMPORARY FEATURE.
    
    TODO: Remove this endpoint when moving beyond MVP phase.
    """
    from datetime import datetime, timezone
    
    # Get the registration request
    reg_request = db.query(RegistrationRequest).filter(RegistrationRequest.id == request_id).first()
    if not reg_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registration request not found"
        )
    
    if reg_request.status != RegistrationStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Registration request has already been {reg_request.status.value}"
        )
    
    # Check if user already exists (shouldn't happen, but safety check)
    existing_user = db.query(User).filter(
        (User.email == reg_request.email) | (User.google_id == reg_request.google_id)
    ).first()
    
    if existing_user:
        # User already exists, mark request as approved anyway
        reg_request.status = RegistrationStatus.APPROVED
        reg_request.reviewed_at = datetime.now(timezone.utc)
        reg_request.reviewed_by_id = current_user.id
        db.commit()
        logger.warning(f"Registration request {request_id} approved but user already exists: {reg_request.email}")
        return {"message": "User already exists", "user_id": existing_user.id}
    
    # Create the user account
    new_user = User(
        email=reg_request.email,
        username=None,  # User must set username via username selection endpoint
        google_id=reg_request.google_id,
        auth_provider="google",
        full_name=reg_request.full_name,
        picture_url=reg_request.picture_url,
    )
    db.add(new_user)
    
    # Update registration request status
    reg_request.status = RegistrationStatus.APPROVED
    reg_request.reviewed_at = datetime.now(timezone.utc)
    reg_request.reviewed_by_id = current_user.id
    
    db.commit()
    db.refresh(new_user)
    
    logger.info(f"Registration request {request_id} approved by moderator {current_user.id}, user {new_user.id} created")
    return {"message": "Registration request approved and user created", "user_id": new_user.id}


@router.post("/registration-requests/{request_id}/deny", status_code=status.HTTP_200_OK)
def deny_registration_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_moderator_user),
):
    """
    Deny a registration request - MVP TEMPORARY FEATURE.
    
    TODO: Remove this endpoint when moving beyond MVP phase.
    """
    from datetime import datetime, timezone
    
    reg_request = db.query(RegistrationRequest).filter(RegistrationRequest.id == request_id).first()
    if not reg_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registration request not found"
        )
    
    if reg_request.status != RegistrationStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Registration request has already been {reg_request.status.value}"
        )
    
    reg_request.status = RegistrationStatus.DENIED
    reg_request.reviewed_at = datetime.now(timezone.utc)
    reg_request.reviewed_by_id = current_user.id
    db.commit()
    
    logger.info(f"Registration request {request_id} denied by moderator {current_user.id}")
    return {"message": "Registration request denied"}

