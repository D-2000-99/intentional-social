"""
Post processing logic for digest generation.

Handles post data preparation, OpenAI API calls, and database updates.
"""
import logging
from typing import Optional, Dict, List
from sqlalchemy.orm import Session, joinedload
from app.database import get_db_session
from app.models import Post, User
from app.openai_client import generate_digest_summary
from app.s3_helper import is_s3_key, generate_presigned_url

logger = logging.getLogger(__name__)


def prepare_post_data(post: Post, db: Session) -> Optional[Dict]:
    """
    Prepare post data for processing (author name, photo URLs).
    
    Args:
        post: Post model instance
        db: Database session
    
    Returns:
        Dictionary with post data or None if preparation fails
    """
    # Get author name
    if post.author:
        author_name = post.author.get_display_name()
    else:
        author = db.query(User).filter(User.id == post.author_id).first()
        if not author:
            logger.warning(f"Author {post.author_id} not found for post {post.id}")
            return None
        author_name = author.get_display_name()
    
    # Get photo URLs and convert S3 keys to presigned URLs if needed
    photo_urls_raw = post.photo_urls or []
    photo_urls = []
    for url_or_key in photo_urls_raw:
        if is_s3_key(url_or_key):
            presigned = generate_presigned_url(url_or_key)
            if presigned:
                photo_urls.append(presigned)
            else:
                logger.warning(f"Could not generate presigned URL for S3 key: {url_or_key}")
        else:
            # Already a URL, use as-is
            photo_urls.append(url_or_key)
    
    return {
        "post": post,
        "author_name": author_name,
        "photo_urls": photo_urls
    }


def process_single_post(post_id: int) -> bool:
    """
    Process a single post to generate its digest summary.
    
    Args:
        post_id: The ID of the post to process
    
    Returns:
        True if successful, False otherwise
    """
    try:
        with get_db_session() as db:
            # Load post with author
            post = (
                db.query(Post)
                .options(joinedload(Post.author))
                .filter(Post.id == post_id)
                .first()
            )
            
            if not post:
                logger.warning(f"Post {post_id} not found")
                return False
            
            # Check if already processed
            if post.digest_summary is not None:
                logger.info(f"Post {post_id} already has a digest summary, skipping")
                return True
            
            # Prepare post data
            post_data = prepare_post_data(post, db)
            if not post_data:
                return False
            
            # Generate summary
            logger.info(f"Processing post {post_id} by {post_data['author_name']}")
            try:
                summary, importance = generate_digest_summary(
                    post_content=post.content,
                    author_name=post_data["author_name"],
                    image_urls=post_data["photo_urls"],
                    timestamp=post.created_at.isoformat() if post.created_at else None
                )
                
                # Validate that we got valid results (not None or empty)
                if not summary or not isinstance(summary, str) or len(summary.strip()) == 0:
                    raise ValueError("Generated summary is empty or invalid")
                if not isinstance(importance, (int, float)) or importance < 0 or importance > 10:
                    raise ValueError(f"Generated importance score is invalid: {importance}")
                
                # Only update post if LLM call succeeded and we have valid results
                post.digest_summary = summary
                post.importance_score = importance
                db.commit()
                
                logger.info(
                    f"Successfully processed post {post_id}: "
                    f"importance={importance:.1f}, summary_length={len(summary)}"
                )
                
                return True
            except Exception as e:
                # LLM call failed - don't update the post, don't set any default values
                logger.error(f"LLM call failed for post {post_id}: {str(e)}")
                # Explicitly rollback to ensure no partial updates
                db.rollback()
                # Ensure post fields are not modified
                db.refresh(post)
                return False
    
    except Exception as e:
        logger.error(f"Error processing post {post_id}: {str(e)}", exc_info=True)
        return False


def process_post_batch(posts_data: List[Dict], db: Session) -> Dict[str, int]:
    """
    Process a batch of prepared posts.
    
    Args:
        posts_data: List of prepared post data dictionaries
        db: Database session
    
    Returns:
        Dictionary with processing statistics
    """
    stats = {
        "processed": 0,
        "failed": 0
    }
    
    for item in posts_data:
        post = item["post"]
        author_name = item["author_name"]
        photo_urls = item["photo_urls"]
        
        try:
            logger.info(f"Processing post {post.id} by {author_name}")
            
            # Generate summary - if this fails, post won't be updated
            try:
                summary, importance = generate_digest_summary(
                    post_content=post.content,
                    author_name=author_name,
                    image_urls=photo_urls,
                    timestamp=post.created_at.isoformat() if post.created_at else None
                )
                
                # Validate that we got valid results (not None or empty)
                if not summary or not isinstance(summary, str) or len(summary.strip()) == 0:
                    raise ValueError("Generated summary is empty or invalid")
                if not isinstance(importance, (int, float)) or importance < 0 or importance > 10:
                    raise ValueError(f"Generated importance score is invalid: {importance}")
                
                # Only update post if LLM call succeeded and we have valid results
                post.digest_summary = summary
                post.importance_score = importance
                db.commit()
                
                logger.info(
                    f"Successfully processed post {post.id}: "
                    f"importance={importance:.1f}, summary_length={len(summary)}"
                )
                stats["processed"] += 1
                
            except Exception as llm_error:
                # LLM call failed - don't update the post, don't set any default values
                logger.error(f"LLM call failed for post {post.id}: {str(llm_error)}")
                # Explicitly rollback to ensure no partial updates
                db.rollback()
                # Ensure post fields are not modified
                db.refresh(post)
                stats["failed"] += 1
            
        except Exception as e:
            logger.error(f"Error processing post {post.id}: {str(e)}", exc_info=True)
            db.rollback()
            stats["failed"] += 1
    
    return stats

