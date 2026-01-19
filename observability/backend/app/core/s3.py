import logging
from typing import List, Optional

import boto3
from botocore.exceptions import ClientError
from botocore.config import Config

from app.config import settings

logger = logging.getLogger(__name__)

# Initialize S3 client
s3_client = None


def get_s3_client():
    """Lazy initialization of S3-compatible client (R2 or S3).
    
    Raises:
        ValueError: If storage credentials or bucket name are not configured.
    """
    global s3_client
    if s3_client is None:
        # Use R2 configuration (with fallback to legacy AWS_* variables for backward compatibility)
        access_key = settings.R2_ACCESS_KEY_ID or settings.AWS_ACCESS_KEY_ID
        secret_key = settings.R2_SECRET_ACCESS_KEY or settings.AWS_SECRET_ACCESS_KEY
        bucket_name = settings.R2_BUCKET_NAME or settings.S3_BUCKET_NAME
        endpoint_url = settings.R2_ENDPOINT_URL
        
        if not access_key or not secret_key:
            raise ValueError(
                "Storage credentials not configured. "
                "Set R2_ACCESS_KEY_ID and R2_SECRET_ACCESS_KEY (or AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY) environment variables."
            )
        
        if not bucket_name:
            raise ValueError(
                "Storage bucket name not configured. "
                "Set R2_BUCKET_NAME (or S3_BUCKET_NAME) environment variable."
            )
        
        # Configure for R2 if endpoint_url is provided, otherwise use S3
        if endpoint_url:
            # R2 configuration
            s3_config = Config(
                signature_version='s3v4',
            )
            s3_client = boto3.client(
                's3',
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                endpoint_url=endpoint_url,
                region_name='auto',  # Required for R2 - must be 'auto'
                config=s3_config
            )
            logger.info(f"Initialized R2 client for bucket '{bucket_name}' at endpoint '{endpoint_url}'")
        else:
            # Legacy S3 configuration
            s3_config = Config(
                signature_version='s3v4',
                region_name=settings.AWS_REGION,
                s3={
                    'addressing_style': 'virtual'  # Forces bucket.s3.region.amazonaws.com format
                }
            )
            s3_client = boto3.client(
                's3',
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                region_name=settings.AWS_REGION,
                config=s3_config
            )
            logger.info(f"Initialized S3 client for bucket '{bucket_name}' in region '{settings.AWS_REGION}'")
    return s3_client


def generate_presigned_url(s3_key: str, expiration: Optional[int] = None) -> str:
    """
    Generate a pre-signed URL for reading an S3 object.
    
    Note: Pre-signed URLs can be generated even if the object doesn't exist yet.
    The URL will only work if the object exists when accessed.
    
    Args:
        s3_key: S3 key (path) of the object
        expiration: URL expiration time in seconds (default from settings)
    
    Returns:
        Pre-signed URL string
    
    Raises:
        Exception: If pre-signed URL generation fails (e.g., invalid credentials)
    """
    client = get_s3_client()
    
    # Default expiration (1 hour) if not set in settings
    if expiration is None:
        expiration = getattr(settings, 'S3_PRESIGNED_URL_EXPIRATION', 3600)
    
    try:
        # Generate pre-signed URL directly without checking object existence
        # Note: s3:GetObject IAM permission is required (not s3:HeadObject)
        # The URL will only work if the object exists when accessed
        url = client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': settings.S3_BUCKET_NAME,
                'Key': s3_key
            },
            ExpiresIn=expiration
        )
        logger.debug(f"Generated pre-signed URL for {s3_key}")
        return url
        
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_message = e.response.get('Error', {}).get('Message', str(e))
        logger.error(f"Error generating pre-signed URL for {s3_key}")
        logger.error(f"Error Code: {error_code}, Message: {error_message}")
        logger.error(f"Bucket: {settings.S3_BUCKET_NAME}, Region: {settings.AWS_REGION}")
        logger.error(f"Full error: {str(e)}")
        raise Exception(f"Failed to generate pre-signed URL ({error_code}): {error_message}")


def generate_presigned_urls(s3_keys: List[str], expiration: Optional[int] = None) -> List[str]:
    """
    Generate multiple pre-signed URLs at once.
    
    Args:
        s3_keys: List of S3 keys
        expiration: URL expiration time in seconds
    
    Returns:
        List of pre-signed URLs in the same order as input keys
    """
    return [generate_presigned_url(key, expiration) for key in s3_keys]


def delete_photo_from_s3(s3_key: str) -> bool:
    """
    Delete a photo from S3/R2 storage.
    
    Args:
        s3_key: S3 key (path) of the object to delete
    
    Returns:
        True if successful, False otherwise
    """
    client = get_s3_client()
    
    # Use R2 bucket name if available, otherwise fall back to S3 bucket name
    bucket_name = settings.R2_BUCKET_NAME or settings.S3_BUCKET_NAME
    
    if not bucket_name:
        logger.error("No bucket name configured for deletion")
        return False
    
    try:
        client.delete_object(
            Bucket=bucket_name,
            Key=s3_key
        )
        logger.info(f"Successfully deleted photo from storage: {s3_key}")
        return True
        
    except ClientError as e:
        logger.error(f"Error deleting from storage: {str(e)}")
        return False

