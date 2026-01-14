"""
S3/R2 helper for generating presigned URLs.

Optional module - only used if S3 credentials are configured.
"""
import logging
from typing import Optional, List
import boto3
from botocore.exceptions import ClientError
from botocore.config import Config
from app.config import settings

logger = logging.getLogger(__name__)

_s3_client = None


def get_s3_client():
    """Lazy initialization of S3-compatible client (R2)."""
    global _s3_client
    if _s3_client is None:
        access_key = settings.R2_ACCESS_KEY_ID
        secret_key = settings.R2_SECRET_ACCESS_KEY
        bucket_name = settings.R2_BUCKET_NAME
        endpoint_url = settings.R2_ENDPOINT_URL
        
        if not all([access_key, secret_key, bucket_name, endpoint_url]):
            logger.warning("S3/R2 credentials not fully configured. Image processing may be limited.")
            return None
        
        _s3_client = boto3.client(
            's3',
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=settings.R2_REGION,
            config=Config(signature_version='s3v4')
        )
        logger.info("S3/R2 client initialized")
    
    return _s3_client


def generate_presigned_url(s3_key: str, expiration: Optional[int] = None) -> Optional[str]:
    """
    Generate a presigned URL for an S3 key.
    
    Args:
        s3_key: S3 key (e.g., "posts/photos/xxx.jpg")
        expiration: URL expiration time in seconds
    
    Returns:
        Presigned URL or None if S3 is not configured
    """
    client = get_s3_client()
    if not client:
        return None
    
    if expiration is None:
        expiration = settings.STORAGE_PRESIGNED_URL_EXPIRATION
    
    try:
        bucket_name = settings.R2_BUCKET_NAME
        url = client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': bucket_name,
                'Key': s3_key
            },
            ExpiresIn=expiration
        )
        logger.debug(f"Generated presigned URL for {s3_key}")
        return url
    except ClientError as e:
        logger.error(f"Error generating presigned URL for {s3_key}: {str(e)}")
        return None


def generate_presigned_urls(s3_keys: List[str], expiration: Optional[int] = None) -> List[str]:
    """
    Generate multiple presigned URLs.
    
    Args:
        s3_keys: List of S3 keys
        expiration: URL expiration time in seconds
    
    Returns:
        List of presigned URLs (None values filtered out)
    """
    urls = [generate_presigned_url(key, expiration) for key in s3_keys]
    return [url for url in urls if url is not None]


def is_s3_key(url_or_key: str) -> bool:
    """
    Check if a string is an S3 key (not a full URL).
    
    Args:
        url_or_key: String to check
    
    Returns:
        True if it looks like an S3 key, False if it's a URL
    """
    return not (url_or_key.startswith('http://') or url_or_key.startswith('https://'))

