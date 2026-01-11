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
    """Lazy initialization of S3 client.
    
    Raises:
        ValueError: If AWS credentials or S3 bucket name are not configured.
    """
    global s3_client
    if s3_client is None:
        if not settings.AWS_ACCESS_KEY_ID or not settings.AWS_SECRET_ACCESS_KEY:
            raise ValueError(
                "AWS credentials not configured. "
                "Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables."
            )
        
        if not settings.S3_BUCKET_NAME:
            raise ValueError(
                "S3_BUCKET_NAME not configured. "
                "Set S3_BUCKET_NAME environment variable."
            )
        
        # Use the configured region - must match the bucket's region
        # Ensure we use signature version 4 for pre-signed URLs
        # Use virtual-hosted-style addressing to match AWS CLI behavior
        # This ensures pre-signed URLs use the regional endpoint format
        s3_config = Config(
            signature_version='s3v4',
            region_name=settings.AWS_REGION,
            s3={
                'addressing_style': 'virtual'  # Forces bucket.s3.region.amazonaws.com format
            }
        )
        s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION,
            config=s3_config
        )
        logger.info(f"Initialized S3 client for bucket '{settings.S3_BUCKET_NAME}' in region '{settings.AWS_REGION}'")
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
    Delete a photo from S3.
    
    Args:
        s3_key: S3 key (path) of the object to delete
    
    Returns:
        True if successful, False otherwise
    """
    client = get_s3_client()
    
    try:
        client.delete_object(
            Bucket=settings.S3_BUCKET_NAME,
            Key=s3_key
        )
        logger.info(f"Successfully deleted photo from S3: {s3_key}")
        return True
        
    except ClientError as e:
        logger.error(f"Error deleting from S3: {str(e)}")
        return False

