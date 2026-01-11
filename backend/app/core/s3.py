import logging
import uuid
from datetime import datetime, timedelta
from io import BytesIO
from typing import List, Optional, Tuple, Dict

import boto3
from botocore.exceptions import ClientError
from botocore.config import Config
from PIL import Image

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


def validate_image(file_content: bytes, max_size_mb: float = 0.2) -> Tuple[bool, Optional[str], Optional[Dict]]:
    """
    Validate image file for security and quality.
    
    Args:
        file_content: Raw image bytes
        max_size_mb: Maximum file size in MB (default 0.2MB = 200KB)
    
    Returns:
        Tuple of (is_valid, error_message, image_info)
        image_info contains: width, height, format, size_bytes
    """
    try:
        # Check file size
        size_bytes = len(file_content)
        max_size_bytes = max_size_mb * 1024 * 1024
        
        if size_bytes > max_size_bytes:
            return False, f"Image size ({size_bytes / 1024:.1f}KB) exceeds maximum allowed size ({max_size_mb * 1024:.0f}KB)", None
        
        # Validate image format and get dimensions
        try:
            image = Image.open(BytesIO(file_content))
            width, height = image.size
            
            # Check format (only allow JPEG, PNG, WebP)
            allowed_formats = ['JPEG', 'PNG', 'WEBP']
            if image.format not in allowed_formats:
                return False, f"Image format {image.format} not allowed. Allowed formats: {', '.join(allowed_formats)}", None
            
            # Verify it's actually an image (PIL will raise exception if not)
            image.verify()
            
            # Reopen for metadata (verify() closes the image)
            image = Image.open(BytesIO(file_content))
            
            # Check dimensions (max 1920x1080 for 720p, but allow up to 1280x720 for MVP)
            max_width, max_height = 1280, 720
            if width > max_width or height > max_height:
                return False, f"Image dimensions ({width}x{height}) exceed maximum allowed ({max_width}x{max_height})", None
            
            # Check minimum dimensions
            min_dimension = 50
            if width < min_dimension or height < min_dimension:
                return False, f"Image dimensions ({width}x{height}) are too small. Minimum: {min_dimension}x{min_dimension}", None
            
            image_info = {
                'width': width,
                'height': height,
                'format': image.format,
                'size_bytes': size_bytes
            }
            
            return True, None, image_info
            
        except Exception as e:
            logger.error(f"Image validation error: {str(e)}")
            return False, f"Invalid image file: {str(e)}", None
            
    except Exception as e:
        logger.error(f"Image validation exception: {str(e)}")
        return False, f"Error validating image: {str(e)}", None


def upload_photo_to_s3(file_content: bytes, post_id: int, user_id: int, file_extension: str = "jpg") -> str:
    """
    Upload a photo to S3 and return the S3 key.
    
    Args:
        file_content: Raw image bytes
        post_id: ID of the post this photo belongs to
        user_id: ID of the user uploading the photo
        file_extension: File extension (jpg, png, webp)
    
    Returns:
        S3 key (path) of the uploaded photo
    """
    client = get_s3_client()
    
    # Generate unique filename: posts/photos/{user_id}/{post_id}/{uuid}.{ext}
    unique_id = str(uuid.uuid4())
    timestamp = datetime.utcnow().strftime("%Y%m%d")
    s3_key = f"{settings.S3_PHOTO_PREFIX}/{user_id}/{post_id}/{timestamp}_{unique_id}.{file_extension}"
    
    try:
        # Upload to S3 with proper content type
        content_type_map = {
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png',
            'webp': 'image/webp'
        }
        content_type = content_type_map.get(file_extension.lower(), 'image/jpeg')
        
        client.put_object(
            Bucket=settings.S3_BUCKET_NAME,
            Key=s3_key,
            Body=file_content,
            ContentType=content_type,
            # Note: ACL is not set - rely on bucket policies for access control
            # Objects are private by default in S3
            Metadata={
                'post_id': str(post_id),
                'user_id': str(user_id),
                'uploaded_at': datetime.utcnow().isoformat()
            }
        )
        
        logger.info(f"Successfully uploaded photo to S3: {s3_key}")
        return s3_key
        
    except ClientError as e:
        logger.error(f"Error uploading to S3: {str(e)}")
        raise Exception(f"Failed to upload photo to S3: {str(e)}")


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
    
    if expiration is None:
        expiration = settings.S3_PRESIGNED_URL_EXPIRATION
    
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


def upload_avatar_to_s3(file_content: bytes, user_id: int, file_extension: str = "jpg") -> str:
    """
    Upload an avatar image to S3 and return the S3 key.
    
    Args:
        file_content: Raw image bytes
        user_id: ID of the user uploading the avatar
        file_extension: File extension (jpg, png, webp)
    
    Returns:
        S3 key (path) of the uploaded avatar
    """
    client = get_s3_client()
    
    # Generate unique filename: users/avatars/{user_id}/{uuid}.{ext}
    unique_id = str(uuid.uuid4())
    timestamp = datetime.utcnow().strftime("%Y%m%d")
    s3_key = f"{settings.S3_AVATAR_PREFIX}/{user_id}/{timestamp}_{unique_id}.{file_extension}"
    
    try:
        # Upload to S3 with proper content type
        content_type_map = {
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png',
            'webp': 'image/webp'
        }
        content_type = content_type_map.get(file_extension.lower(), 'image/jpeg')
        
        client.put_object(
            Bucket=settings.S3_BUCKET_NAME,
            Key=s3_key,
            Body=file_content,
            ContentType=content_type,
            Metadata={
                'user_id': str(user_id),
                'uploaded_at': datetime.utcnow().isoformat()
            }
        )
        
        logger.info(f"Successfully uploaded avatar to S3: {s3_key}")
        return s3_key
        
    except ClientError as e:
        logger.error(f"Error uploading avatar to S3: {str(e)}")
        raise Exception(f"Failed to upload avatar to S3: {str(e)}")


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

