"""
AI Service Main Entry Point

Processes posts to generate digest summaries using OpenAI.
Supports single post, batch processing, and continuous modes.
"""
import logging
import sys
import time
from typing import Optional
from app.config import settings
from app.database import get_db_session
from app.models import Post
from app.post_processor import (
    process_single_post,
    prepare_post_data,
    process_post_batch,
    process_posts_async
)
from app.week_utils import get_week_bounds
from sqlalchemy.orm import joinedload

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)


def process_weekly_posts_async(limit: Optional[int] = None) -> dict:
    """
    Process all posts from the current week that don't have digest summaries.
    Uses async processing to process posts in parallel sets for immediate updates.
    
    Args:
        limit: Maximum number of posts to process (None for all)
    
    Returns:
        Dictionary with processing statistics
    """
    week_start, week_end = get_week_bounds()
    
    logger.info(
        f"Async processing weekly digest for week {week_start.date()} to {week_end.date()}"
    )
    
    stats = {
        "processed": 0,
        "failed": 0,
        "skipped": 0,
        "total_found": 0
    }
    
    try:
        with get_db_session() as db:
            # Step 1: Collect all pending posts
            posts = (
                db.query(Post)
                .options(joinedload(Post.author))
                .filter(
                    Post.created_at >= week_start,
                    Post.created_at <= week_end,
                    Post.digest_summary.is_(None)
                )
                .order_by(Post.created_at.asc())
                .limit(limit)
                .all()
            )
            
            stats["total_found"] = len(posts)
            
            if not posts:
                logger.info("No pending posts found to process")
                return stats
            
            logger.info(f"Found {len(posts)} pending posts to process asynchronously")
            
            # Step 2: Prepare all posts for processing
            posts_to_process = []
            for post in posts:
                post_data = prepare_post_data(post, db)
                if post_data:
                    posts_to_process.append(post_data)
                else:
                    stats["skipped"] += 1
                    logger.warning(f"Skipping post {post.id} due to preparation failure")
            
            # Step 3: Process all posts asynchronously
            async_batch_size = settings.ASYNC_BATCH_SIZE
            logger.info(
                f"Starting async processing of {len(posts_to_process)} posts "
                f"(parallel batch size: {async_batch_size})..."
            )
            async_stats = process_posts_async(posts_to_process, db, batch_size=async_batch_size)
            stats["processed"] = async_stats["processed"]
            stats["failed"] = async_stats["failed"]
        
        logger.info(
            f"Async processing complete: {stats['processed']} processed, "
            f"{stats['failed']} failed, {stats['skipped']} skipped"
        )
        
        return stats
    
    except Exception as e:
        logger.error(f"Error in async processing: {str(e)}", exc_info=True)
        return stats


def process_weekly_posts_batch(limit: Optional[int] = None) -> dict:
    """
    Process all posts from the current week that don't have digest summaries.
    Uses batch processing to collect all posts, process them, and update DB.
    
    Args:
        limit: Maximum number of posts to process (None for all)
    
    Returns:
        Dictionary with processing statistics
    """
    week_start, week_end = get_week_bounds()
    
    logger.info(
        f"Batch processing weekly digest for week {week_start.date()} to {week_end.date()}"
    )
    
    stats = {
        "processed": 0,
        "failed": 0,
        "skipped": 0,
        "total_found": 0
    }
    
    try:
        with get_db_session() as db:
            # Step 1: Collect all pending posts
            posts = (
                db.query(Post)
                .options(joinedload(Post.author))
                .filter(
                    Post.created_at >= week_start,
                    Post.created_at <= week_end,
                    Post.digest_summary.is_(None)
                )
                .order_by(Post.created_at.asc())
                .limit(limit)
                .all()
            )
            
            stats["total_found"] = len(posts)
            
            if not posts:
                logger.info("No pending posts found to process")
                return stats
            
            logger.info(f"Found {len(posts)} pending posts to process in batch")
            
            # Step 2: Prepare all posts for processing
            posts_to_process = []
            for post in posts:
                post_data = prepare_post_data(post, db)
                if post_data:
                    posts_to_process.append(post_data)
                else:
                    stats["skipped"] += 1
                    logger.warning(f"Skipping post {post.id} due to preparation failure")
            
            # Step 3: Process all posts in batch
            logger.info(f"Starting batch processing of {len(posts_to_process)} posts...")
            batch_stats = process_post_batch(posts_to_process, db)
            stats["processed"] = batch_stats["processed"]
            stats["failed"] = batch_stats["failed"]
        
        logger.info(
            f"Batch processing complete: {stats['processed']} processed, "
            f"{stats['failed']} failed, {stats['skipped']} skipped"
        )
        
        return stats
    
    except Exception as e:
        logger.error(f"Error in batch processing: {str(e)}", exc_info=True)
        return stats


def process_posts_continuously(interval_seconds: int = 5):
    """
    Continuously process posts one at a time from the current week.
    
    Args:
        interval_seconds: Seconds to wait between processing posts
    """
    logger.info("Starting continuous post processing mode...")
    logger.info(f"Will process posts one at a time with {interval_seconds}s interval")
    
    while True:
        try:
            week_start, week_end = get_week_bounds()
            
            with get_db_session() as db:
                # Find one post from this week without summary
                post = (
                    db.query(Post)
                    .filter(
                        Post.created_at >= week_start,
                        Post.created_at <= week_end,
                        Post.digest_summary.is_(None)
                    )
                    .order_by(Post.created_at.asc())
                    .first()
                )
                
                if post:
                    logger.info(f"Found unprocessed post {post.id}, processing...")
                    success = process_single_post(post.id)
                    if success:
                        logger.info(f"Successfully processed post {post.id}")
                    else:
                        logger.error(f"Failed to process post {post.id}")
                else:
                    logger.info("No unprocessed posts found in current week. Waiting...")
            
            # Wait before checking for next post
            time.sleep(interval_seconds)
            
        except KeyboardInterrupt:
            logger.info("Received interrupt signal, shutting down...")
            break
        except Exception as e:
            logger.error(f"Error in continuous processing: {str(e)}", exc_info=True)
            logger.info(f"Waiting {interval_seconds}s before retrying...")
            time.sleep(interval_seconds)


def main():
    """Main entry point for the service."""
    import argparse
    
    parser = argparse.ArgumentParser(description="AI Service for Digest Generation")
    parser.add_argument(
        "--post-id",
        type=int,
        help="Process a specific post by ID"
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Process all posts from current week using OpenAI Batch API (then exit)"
    )
    parser.add_argument(
        "--async",
        action="store_true",
        dest="async_mode",
        help="Process all posts from current week using async parallel API calls (then exit)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of posts to process in batch mode"
    )
    parser.add_argument(
        "--continuous",
        action="store_true",
        default=True,  # Default to continuous mode
        help="Continuously process posts one at a time (default behavior)"
    )
    parser.add_argument(
        "--no-continuous",
        action="store_false",
        dest="continuous",
        help="Disable continuous mode (use with --batch or --post-id)"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=5,
        help="Seconds to wait between posts in continuous mode (default: 5)"
    )
    
    args = parser.parse_args()
    
    logger.info("AI Service starting...")
    logger.info(f"Using OpenAI model: {settings.OPENAI_MODEL_NAME}")
    
    if args.post_id:
        # Process single post
        logger.info(f"Processing post {args.post_id}")
        success = process_single_post(args.post_id)
        sys.exit(0 if success else 1)
    
    elif args.batch:
        # Process batch (collect all, process, update DB, exit)
        stats = process_weekly_posts_batch(limit=args.limit)
        exit_code = 0 if stats["failed"] == 0 else 1
        logger.info(f"Batch processing complete. Exiting with code {exit_code}")
        sys.exit(exit_code)
    
    elif args.async_mode:
        # Process async (collect all, process in parallel sets, update DB, exit)
        stats = process_weekly_posts_async(limit=args.limit)
        exit_code = 0 if stats["failed"] == 0 else 1
        logger.info(f"Async processing complete. Exiting with code {exit_code}")
        sys.exit(exit_code)
    
    elif args.continuous:
        # Continuous mode (default)
        process_posts_continuously(interval_seconds=args.interval)
    
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()

