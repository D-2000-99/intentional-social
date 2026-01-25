"""
Post processing logic for digest generation.

Handles post data preparation, OpenAI API calls, and database updates.
"""
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, Dict, List, Tuple
from sqlalchemy.orm import Session, joinedload
from app.database import get_db_session
from app.models import Post, User
from app.openai_client import (
    generate_digest_summary,
    prepare_batch_request,
    create_batch_job,
    get_batch_status,
    retrieve_batch_results,
    parse_batch_result
)
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


def wait_for_batch_completion(batch_id: str, poll_interval: int = 10, max_wait_time: int = 3600) -> bool:
    """
    Wait for a batch job to complete.
    
    Args:
        batch_id: The batch job ID
        poll_interval: Seconds between status checks
        max_wait_time: Maximum time to wait in seconds
    
    Returns:
        True if batch completed successfully, False otherwise
    """
    start_time = time.time()
    
    while True:
        elapsed = time.time() - start_time
        if elapsed > max_wait_time:
            logger.error(f"Batch {batch_id} exceeded max wait time of {max_wait_time}s")
            return False
        
        try:
            status = get_batch_status(batch_id)
            batch_status = status["status"]
            
            logger.info(
                f"Batch {batch_id} status: {batch_status} "
                f"(completed: {status.get('request_counts', {}).get('completed', 0)}, "
                f"failed: {status.get('request_counts', {}).get('failed', 0)})"
            )
            
            if batch_status == "completed":
                return True
            elif batch_status in ["failed", "expired", "cancelled"]:
                logger.error(f"Batch {batch_id} ended with status: {batch_status}")
                return False
            elif batch_status in ["validating", "in_progress", "finalizing", "cancelling"]:
                # Still processing, wait and check again
                time.sleep(poll_interval)
            else:
                logger.warning(f"Unknown batch status: {batch_status}, waiting...")
                time.sleep(poll_interval)
        
        except Exception as e:
            logger.error(f"Error checking batch status: {str(e)}")
            time.sleep(poll_interval)


def process_post_batch(posts_data: List[Dict], db: Session) -> Dict[str, int]:
    """
    Process a batch of prepared posts using OpenAI Batch API for cost savings.
    
    Args:
        posts_data: List of prepared post data dictionaries
        db: Database session
    
    Returns:
        Dictionary with processing statistics
    """
    stats = {
        "processed": 0,
        "failed": 0,
        "skipped": 0
    }
    
    if not posts_data:
        logger.info("No posts to process in batch")
        return stats
    
    logger.info(f"Preparing batch processing for {len(posts_data)} posts using OpenAI Batch API")
    
    # Step 1: Prepare batch requests
    batch_requests = []
    post_id_to_index = {}  # Map post_id to index in posts_data for result matching
    
    for idx, item in enumerate(posts_data):
        post = item["post"]
        author_name = item["author_name"]
        photo_urls = item["photo_urls"]
        
        try:
            batch_request = prepare_batch_request(
                post_content=post.content,
                author_name=author_name,
                image_urls=photo_urls,
                timestamp=post.created_at.isoformat() if post.created_at else None,
                custom_id=str(post.id)  # Use post ID as custom_id for matching results
            )
            batch_requests.append(batch_request)
            post_id_to_index[post.id] = idx
            logger.debug(f"Prepared batch request for post {post.id}")
        except Exception as e:
            logger.error(f"Failed to prepare batch request for post {post.id}: {str(e)}")
            stats["skipped"] += 1
    
    if not batch_requests:
        logger.warning("No valid batch requests prepared")
        return stats
    
    logger.info(f"Prepared {len(batch_requests)} batch requests, submitting to OpenAI...")
    
    # Step 2: Create and submit batch job
    try:
        batch_id = create_batch_job(batch_requests)
        logger.info(f"Batch job {batch_id} created successfully")
    except Exception as e:
        logger.error(f"Failed to create batch job: {str(e)}")
        stats["failed"] = len(posts_data)
        return stats
    
    # Step 3: Wait for batch completion
    logger.info(f"Waiting for batch {batch_id} to complete...")
    if not wait_for_batch_completion(batch_id, poll_interval=10, max_wait_time=3600):
        logger.error(f"Batch {batch_id} did not complete successfully")
        stats["failed"] = len(posts_data)
        return stats
    
    # Step 4: Retrieve and process results
    logger.info(f"Retrieving results from batch {batch_id}...")
    try:
        batch_results = retrieve_batch_results(batch_id)
    except Exception as e:
        logger.error(f"Failed to retrieve batch results: {str(e)}")
        stats["failed"] = len(posts_data)
        return stats
    
    # Step 5: Map results to posts and update database
    # Create a map of custom_id (post_id) to result
    results_map = {}
    for result in batch_results:
        custom_id = result.get("custom_id")
        if custom_id:
            try:
                post_id = int(custom_id)
                results_map[post_id] = result
            except ValueError:
                logger.warning(f"Invalid custom_id in batch result: {custom_id}")
    
    # Process each post with its result
    for item in posts_data:
        post = item["post"]
        
        if post.id not in results_map:
            logger.warning(f"No result found for post {post.id} in batch results")
            stats["failed"] += 1
            continue
        
        result = results_map[post.id]
        
        try:
            # Parse the batch result
            summary, importance = parse_batch_result(result)
            
            # Validate results
            if not summary or not isinstance(summary, str) or len(summary.strip()) == 0:
                raise ValueError("Generated summary is empty or invalid")
            if not isinstance(importance, (int, float)) or importance < 0 or importance > 10:
                raise ValueError(f"Generated importance score is invalid: {importance}")
            
            # Update post in database
            post.digest_summary = summary
            post.importance_score = importance
            db.commit()
            
            logger.info(
                f"Successfully processed post {post.id}: "
                f"importance={importance:.1f}, summary_length={len(summary)}"
            )
            stats["processed"] += 1
        
        except Exception as e:
            logger.error(f"Failed to process result for post {post.id}: {str(e)}")
            db.rollback()
            db.refresh(post)
            stats["failed"] += 1
    
    logger.info(
        f"Batch processing complete: {stats['processed']} processed, "
        f"{stats['failed']} failed, {stats['skipped']} skipped"
    )
    
    return stats


def process_post_async(
    post_data: Dict,
    db: Session
) -> Tuple[bool, Optional[str]]:
    """
    Process a single post asynchronously (for use in parallel processing).
    
    Args:
        post_data: Dictionary with post data (post, author_name, photo_urls)
        db: Database session (will create a new session for thread safety)
    
    Returns:
        Tuple of (success: bool, error_message: Optional[str])
    """
    post = post_data["post"]
    post_id = post.id
    
    try:
        # Create a new database session for this thread
        with get_db_session() as thread_db:
            # Refresh the post in the new session
            post = thread_db.query(Post).filter(Post.id == post_id).first()
            
            if not post:
                return False, f"Post {post_id} not found"
            
            # Check if already processed
            if post.digest_summary is not None:
                logger.debug(f"Post {post_id} already has a digest summary, skipping")
                return True, None
            
            # Generate summary
            try:
                summary, importance = generate_digest_summary(
                    post_content=post.content,
                    author_name=post_data["author_name"],
                    image_urls=post_data["photo_urls"],
                    timestamp=post.created_at.isoformat() if post.created_at else None
                )
                
                # Validate results
                if not summary or not isinstance(summary, str) or len(summary.strip()) == 0:
                    raise ValueError("Generated summary is empty or invalid")
                if not isinstance(importance, (int, float)) or importance < 0 or importance > 10:
                    raise ValueError(f"Generated importance score is invalid: {importance}")
                
                # Update post
                post.digest_summary = summary
                post.importance_score = importance
                thread_db.commit()
                
                logger.info(
                    f"Successfully processed post {post_id}: "
                    f"importance={importance:.1f}, summary_length={len(summary)}"
                )
                
                return True, None
                
            except Exception as e:
                logger.error(f"LLM call failed for post {post_id}: {str(e)}")
                thread_db.rollback()
                thread_db.refresh(post)
                return False, str(e)
    
    except Exception as e:
        logger.error(f"Error processing post {post_id}: {str(e)}", exc_info=True)
        return False, str(e)


def process_posts_async(
    posts_data: List[Dict],
    db: Session,
    batch_size: int = 5
) -> Dict[str, int]:
    """
    Process posts asynchronously in parallel sets using normal OpenAI API calls.
    
    Args:
        posts_data: List of prepared post data dictionaries
        db: Database session (for reference, but each thread uses its own session)
        batch_size: Number of posts to process in parallel (default: 5)
    
    Returns:
        Dictionary with processing statistics
    """
    stats = {
        "processed": 0,
        "failed": 0,
        "skipped": 0
    }
    
    if not posts_data:
        logger.info("No posts to process asynchronously")
        return stats
    
    logger.info(
        f"Starting async processing for {len(posts_data)} posts "
        f"(parallel batch size: {batch_size})"
    )
    
    # Process posts in batches of batch_size
    total_batches = (len(posts_data) + batch_size - 1) // batch_size
    
    for batch_num in range(total_batches):
        start_idx = batch_num * batch_size
        end_idx = min(start_idx + batch_size, len(posts_data))
        batch_posts = posts_data[start_idx:end_idx]
        
        logger.info(
            f"Processing batch {batch_num + 1}/{total_batches} "
            f"({len(batch_posts)} posts)"
        )
        
        # Process this batch in parallel
        with ThreadPoolExecutor(max_workers=batch_size) as executor:
            # Submit all posts in this batch
            future_to_post = {
                executor.submit(process_post_async, post_data, db): post_data
                for post_data in batch_posts
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_post):
                post_data = future_to_post[future]
                post_id = post_data["post"].id
                
                try:
                    success, error_msg = future.result()
                    if success:
                        stats["processed"] += 1
                        logger.debug(f"Post {post_id} processed successfully")
                    else:
                        stats["failed"] += 1
                        logger.warning(
                            f"Post {post_id} failed: {error_msg or 'Unknown error'}"
                        )
                except Exception as e:
                    stats["failed"] += 1
                    logger.error(f"Unexpected error processing post {post_id}: {str(e)}")
        
        logger.info(
            f"Batch {batch_num + 1}/{total_batches} complete: "
            f"{stats['processed']} processed, {stats['failed']} failed so far"
        )
    
    logger.info(
        f"Async processing complete: {stats['processed']} processed, "
        f"{stats['failed']} failed, {stats['skipped']} skipped"
    )
    
    return stats

