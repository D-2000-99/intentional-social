import logging
from fastapi import APIRouter, Depends, status, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime, timezone

from app.core.deps import get_db, get_current_user
from app.core.s3 import validate_image, upload_photo_to_s3, generate_presigned_urls, generate_presigned_url, delete_photo_from_s3
from app.models.post import Post
from app.models.post_audience_tag import PostAudienceTag
from app.models.reported_post import ReportedPost
from app.models.tag import Tag
from app.schemas.post import PostCreate, PostOut, ReportPostRequest
from app.models.user import User
from app.services.post_service import PostService
from app.services.storage_service import StorageService

router = APIRouter(prefix="/posts", tags=["Posts"])

logger = logging.getLogger(__name__)


@router.post("/", response_model=PostOut, status_code=status.HTTP_201_CREATED)
async def create_post(
    content: str = Form(...),
    audience_type: str = Form("all"),
    audience_tag_ids: Optional[str] = Form(None),  # Comma-separated string
    photos: Optional[List[UploadFile]] = File(None),
    client_timestamp: Optional[str] = Form(None),  # ISO format timestamp from client
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new post with optional photo attachments.
    
    Accepts multipart/form-data with:
    - content: Post text content
    - audience_type: 'all', 'tags', 'connections', or 'private'
    - audience_tag_ids: Comma-separated tag IDs (optional, used when audience_type is 'tags')
    - photos: One or more image files (optional)
    - client_timestamp: ISO format timestamp from client system (optional, falls back to server time)
    """
    # Parse client timestamp or use server time as fallback
    if client_timestamp:
        try:
            # Parse ISO format timestamp (client sends local time without timezone)
            # Handle both with and without timezone info
            if client_timestamp.endswith('Z'):
                # UTC format - convert to naive (shouldn't happen with our frontend, but handle it)
                post_timestamp = datetime.fromisoformat(client_timestamp.replace('Z', '+00:00'))
                # Convert to naive by removing timezone info (preserve the time value)
                if post_timestamp.tzinfo:
                    post_timestamp = post_timestamp.replace(tzinfo=None)
            elif '+' in client_timestamp or client_timestamp.count('-') > 2:
                # Has timezone offset - parse and convert to naive
                post_timestamp = datetime.fromisoformat(client_timestamp)
                if post_timestamp.tzinfo:
                    post_timestamp = post_timestamp.replace(tzinfo=None)
            else:
                # Naive datetime (local time from client) - parse as-is
                post_timestamp = datetime.fromisoformat(client_timestamp)
        except (ValueError, AttributeError) as e:
            # If parsing fails, fall back to server time
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to parse client_timestamp '{client_timestamp}': {e}. Using server time.")
            post_timestamp = datetime.now()
    else:
        # No client timestamp provided, use server time
        post_timestamp = datetime.now()
    
    # Check daily post limit (3 posts per day) using client time
    # Use the client's local date (their current day)
    # Ensure post_timestamp is naive (no timezone) to preserve client's local time
    if post_timestamp.tzinfo is not None:
        post_timestamp = post_timestamp.replace(tzinfo=None)
    
    # Extract date part for comparison (works with both naive and timezone-aware stored timestamps)
    client_date = post_timestamp.date()
    
    # Query posts from today using date comparison
    # This works regardless of whether stored timestamps are timezone-aware or naive
    posts_today_count = (
        db.query(func.count(Post.id))
        .filter(Post.author_id == current_user.id)
        .filter(func.date(Post.created_at) == client_date)
        .scalar()
    )
    
    if posts_today_count >= 3:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="You have reached the daily limit of 3 posts. Please try again tomorrow."
        )
    
    # Parse audience_tag_ids
    tag_ids = []
    if audience_tag_ids:
        try:
            tag_ids = [int(tid.strip()) for tid in audience_tag_ids.split(",") if tid.strip()]
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid audience_tag_ids format"
            )
    
    # Validate and upload photos
    photo_s3_keys = []
    if photos:
        # Limit number of photos per post (e.g., max 5)
        max_photos = 5
        if len(photos) > max_photos:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Maximum {max_photos} photos allowed per post"
            )
        
        # Create post first to get post_id for S3 path
        # Ensure timestamp is naive (no timezone) to preserve client's local time
        post_created_at = post_timestamp
        if post_created_at.tzinfo is not None:
            post_created_at = post_created_at.replace(tzinfo=None)
        
        new_post = Post(
            author_id=current_user.id,
            content=content,
            audience_type=audience_type,
            photo_urls=[],  # Will be updated after uploads
            created_at=post_created_at
        )
        db.add(new_post)
        db.commit()
        db.refresh(new_post)
        
        # Process each photo
        for photo in photos:
            try:
                # Read file content
                file_content = await photo.read()
                
                # Validate image
                is_valid, error_msg, image_info = validate_image(file_content, max_size_mb=0.2)
                if not is_valid:
                    # Rollback post creation if validation fails
                    db.delete(new_post)
                    db.commit()
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Photo validation failed: {error_msg}"
                    )
                
                # Determine file extension from content type or filename
                file_extension = "jpg"  # default
                if photo.filename:
                    if photo.filename.lower().endswith(('.png',)):
                        file_extension = "png"
                    elif photo.filename.lower().endswith(('.webp',)):
                        file_extension = "webp"
                    elif photo.filename.lower().endswith(('.jpg', '.jpeg')):
                        file_extension = "jpg"
                elif image_info and image_info.get('format'):
                    format_map = {'JPEG': 'jpg', 'PNG': 'png', 'WEBP': 'webp'}
                    file_extension = format_map.get(image_info['format'], 'jpg')
                
                # Upload to S3
                s3_key = upload_photo_to_s3(
                    file_content=file_content,
                    post_id=new_post.id,
                    user_id=current_user.id,
                    file_extension=file_extension
                )
                photo_s3_keys.append(s3_key)
                
            except HTTPException:
                # Re-raise HTTP exceptions
                raise
            except Exception as e:
                # Rollback post creation on any error
                db.delete(new_post)
                db.commit()
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to upload photo: {str(e)}"
                )
        
        # Update post with photo URLs
        new_post.photo_urls = photo_s3_keys
        db.commit()
        db.refresh(new_post)
    else:
        # No photos, create post normally
        # Ensure timestamp is naive (no timezone) to preserve client's local time
        post_created_at = post_timestamp
        if post_created_at.tzinfo is not None:
            post_created_at = post_created_at.replace(tzinfo=None)
        
        new_post = Post(
            author_id=current_user.id,
            content=content,
            audience_type=audience_type,
            photo_urls=[],
            created_at=post_created_at
        )
        db.add(new_post)
        db.commit()
        db.refresh(new_post)
    
    # If audience is tags, create post_audience_tags
    if audience_type == "tags" and tag_ids:
        for tag_id in tag_ids:
            audience_tag = PostAudienceTag(
                post_id=new_post.id,
                tag_id=tag_id,
            )
            db.add(audience_tag)
        db.commit()
        db.refresh(new_post)

    # Use StorageService for presigned URLs
    storage_service = StorageService(redis_client=None)
    photo_urls_presigned = []
    if new_post.photo_urls:
        try:
            photo_urls_presigned = storage_service.batch_get_presigned_urls(new_post.photo_urls)
        except Exception:
            photo_urls_presigned = []
    
    # Use PostService to batch load audience tags
    audience_tags_map = PostService.batch_load_audience_tags([new_post], db)
    
    # Return PostOut with pre-signed URLs
    return PostOut(
        id=new_post.id,
        author_id=new_post.author_id,
        content=new_post.content,
        audience_type=new_post.audience_type,
        photo_urls=new_post.photo_urls or [],
        photo_urls_presigned=photo_urls_presigned,
        created_at=new_post.created_at,
        author=new_post.author,
        audience_tags=audience_tags_map.get(new_post.id, [])
    )


@router.get("/me", response_model=list[PostOut])
def get_my_posts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all posts by the current user"""
    posts = (
        db.query(Post)
        .options(joinedload(Post.author))
        .filter(Post.author_id == current_user.id)
        .order_by(Post.created_at.desc())
        .all()
    )
    
    # Use PostService to batch load audience tags (fixes N+1 query problem)
    audience_tags_map = PostService.batch_load_audience_tags(posts, db)
    
    # Use StorageService for presigned URLs
    storage_service = StorageService(redis_client=None)
    
    # Convert to PostOut with pre-signed URLs
    result = []
    for post in posts:
        photo_urls_presigned = []
        if post.photo_urls:
            try:
                photo_urls_presigned = storage_service.batch_get_presigned_urls(post.photo_urls)
            except Exception as e:
                logger.error(f"Failed to generate pre-signed URLs for post {post.id}: {str(e)}")
                logger.error(f"Photo URLs: {post.photo_urls}")
                photo_urls_presigned = []
        
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


@router.get("/user/{user_id}", response_model=list[PostOut])
def get_user_posts(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all posts by a specific user"""
    # Verify user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    posts = (
        db.query(Post)
        .options(joinedload(Post.author))
        .filter(Post.author_id == user_id)
        .order_by(Post.created_at.desc())
        .all()
    )
    
    # Use PostService to batch load audience tags (fixes N+1 query problem)
    audience_tags_map = PostService.batch_load_audience_tags(posts, db)
    
    # Use StorageService for presigned URLs
    storage_service = StorageService(redis_client=None)
    
    # Convert to PostOut with pre-signed URLs
    result = []
    for post in posts:
        photo_urls_presigned = []
        if post.photo_urls:
            try:
                photo_urls_presigned = storage_service.batch_get_presigned_urls(post.photo_urls)
            except Exception as e:
                logger.error(f"Failed to generate pre-signed URLs for post {post.id}: {str(e)}")
                logger.error(f"Photo URLs: {post.photo_urls}")
                photo_urls_presigned = []
        
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


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a post by its ID. Only the post author can delete their own post.
    
    Deletion order:
    1. Delete PostAudienceTag entries (foreign key constraint)
    2. Delete photos from S3 (if any)
    3. Delete the post itself
    """
    # Get the post and verify ownership
    post = db.query(Post).filter(Post.id == post_id).first()
    
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )
    
    if post.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own posts"
        )
    
    try:
        # Step 1: Delete PostAudienceTag entries (foreign key constraint)
        db.query(PostAudienceTag).filter(PostAudienceTag.post_id == post_id).delete()
        db.commit()
        
        # Step 2: Delete photos from S3 (if any)
        if post.photo_urls:
            for s3_key in post.photo_urls:
                try:
                    delete_photo_from_s3(s3_key)
                except Exception as e:
                    # Log error but continue deletion (don't fail if S3 delete fails)
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Failed to delete photo from S3 ({s3_key}): {str(e)}")
        
        # Step 3: Delete the post itself
        db.delete(post)
        db.commit()
        
        return None  # 204 No Content
        
    except Exception as e:
        db.rollback()
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error deleting post {post_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete post: {str(e)}"
        )


@router.post("/{post_id}/report", status_code=status.HTTP_201_CREATED)
def report_post(
    post_id: int,
    report_data: ReportPostRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Report a post for moderation.
    """
    # Verify post exists
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )
    
    # Check if user has already reported this post
    existing_report = db.query(ReportedPost).filter(
        ReportedPost.post_id == post_id,
        ReportedPost.reported_by_id == current_user.id
    ).first()
    
    if existing_report:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already reported this post"
        )
    
    # Create report
    report = ReportedPost(
        post_id=post_id,
        reported_by_id=current_user.id,
        reason=report_data.reason
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    
    return {"message": "Post reported successfully", "report_id": report.id}


@router.get("/test-presigned/{s3_key:path}")
def test_presigned_url(
    s3_key: str,
    current_user: User = Depends(get_current_user),
):
    """
    Test endpoint to generate and return a pre-signed URL for debugging.
    Usage: /posts/test-presigned/posts/photos/175/166/20251203_7c8ece7c-876d-4781-829c-22c452d9351c.jpg
    """
    try:
        url = generate_presigned_url(s3_key)
        return {
            "s3_key": s3_key,
            "presigned_url": url,
            "status": "success"
        }
    except Exception as e:
        return {
            "s3_key": s3_key,
            "error": str(e),
            "status": "error"
        }
