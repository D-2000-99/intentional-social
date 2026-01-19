"""Database utilities for improved transaction management."""
from contextlib import contextmanager
from sqlalchemy.orm import Session


@contextmanager
def transaction(db: Session):
    """
    Context manager for database transactions.
    Automatically commits on success, rolls back on error.
    
    Usage:
        with transaction(db):
            # Create post
            new_post = Post(...)
            db.add(new_post)
            db.flush()  # Get post.id without committing
            
            # Upload photos
            for photo in photos:
                s3_key = upload_photo_to_s3(...)
                photo_s3_keys.append(s3_key)
            
            # Update post
            new_post.photo_urls = photo_s3_keys
            
            # Transaction commits here automatically
    """
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
