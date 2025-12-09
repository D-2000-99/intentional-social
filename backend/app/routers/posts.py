from fastapi import APIRouter, Depends, status, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime, timezone

from app.core.deps import get_db, get_current_user
from app.core.s3 import validate_image, upload_photo_to_s3, generate_presigned_urls, generate_presigned_url, delete_photo_from_s3
from app.models.post import Post
from app.models.post_audience_tag import PostAudienceTag
from app.models.tag import Tag
from app.schemas.post import PostCreate, PostOut
from app.models.user import User

router = APIRouter(prefix="/posts", tags=["Posts"])


@router.post("/", response_model=PostOut, status_code=status.HTTP_201_CREATED)
async def create_post(
    content: str = Form(...),
    audience_type: str = Form("all"),
    audience_tag_ids: Optional[str] = Form(None),  # Comma-separated string
    photos: Optional[List[UploadFile]] = File(None),
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
    """
    # Check daily post limit (3 posts per day)
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    posts_today_count = (
        db.query(func.count(Post.id))
        .filter(Post.author_id == current_user.id)
        .filter(Post.created_at >= today_start)
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
        new_post = Post(
            author_id=current_user.id,
            content=content,
            audience_type=audience_type,
            photo_urls=[]  # Will be updated after uploads
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
        new_post = Post(
            author_id=current_user.id,
            content=content,
            audience_type=audience_type,
            photo_urls=[]
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

    # Generate pre-signed URLs for the response
    photo_urls_presigned = []
    if new_post.photo_urls:
        try:
            photo_urls_presigned = generate_presigned_urls(new_post.photo_urls)
        except Exception:
            photo_urls_presigned = []
    
    # Get audience tags
    audience_tags = []
    if new_post.audience_type == "tags":
        post_audience_tags = (
            db.query(PostAudienceTag)
            .filter(PostAudienceTag.post_id == new_post.id)
            .all()
        )
        tag_ids = [pat.tag_id for pat in post_audience_tags]
        if tag_ids:
            tags = db.query(Tag).filter(Tag.id.in_(tag_ids)).all()
            audience_tags = tags
    
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
        audience_tags=audience_tags
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
    
    # Convert to PostOut with pre-signed URLs
    result = []
    for post in posts:
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
    
    # Convert to PostOut with pre-signed URLs
    result = []
    for post in posts:
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
