from app.config import settings


def is_storage_key(value: str) -> bool:
    """Check if a value looks like a storage object key."""
    if not value:
        return False
    prefixes = [
        settings.STORAGE_PHOTO_PREFIX,
        settings.STORAGE_AVATAR_PREFIX,
        settings.S3_PHOTO_PREFIX,
        settings.S3_AVATAR_PREFIX,
    ]
    return any(value.startswith(prefix) for prefix in prefixes if prefix)


def build_image_path(s3_key: str) -> str:
    """Build the stable image path for a storage key."""
    return f"/images/{s3_key}"
