from typing import Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings.
    
    IMPORTANT: All sensitive values (AWS credentials, secrets, OAuth secrets, SMTP passwords)
    MUST be provided via environment variables, NOT hardcoded in this file.
    Load from .env file or environment variables.
    """
    
    # Database and core settings - REQUIRED
    DATABASE_URL: str  # Must be set via environment variable
    SECRET_KEY: str  # Must be set via environment variable (min 32 chars)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    MAX_CONNECTIONS: int = 10
    
    # CORS configuration
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000,https://intentional-social.pages.dev/,https://intentionalsocial.org,https://dev.intentional-social.pages.dev"
    
    # Email configuration (optional for MVP - can skip in dev)
    # These are only needed if sending emails
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: Optional[str] = None  # Loaded from environment variable
    SMTP_PASSWORD: Optional[str] = None  # Loaded from environment variable
    SMTP_FROM_EMAIL: Optional[str] = None
    
    # Storage configuration - Loaded from environment variables
    # Prefix settings (used for both S3 and R2)
    STORAGE_PHOTO_PREFIX: str = "posts/photos"  # Prefix for photo objects
    STORAGE_AVATAR_PREFIX: str = "users/avatars"  # Prefix for avatar objects
    STORAGE_PRESIGNED_URL_EXPIRATION: int = 3600  # 1 hour in seconds
    
    # R2 (Cloudflare) configuration - Destination for migration and future use
    R2_ACCESS_KEY_ID: Optional[str] = None  # R2 Access Key ID
    R2_SECRET_ACCESS_KEY: Optional[str] = None  # R2 Secret Access Key
    R2_ENDPOINT_URL: Optional[str] = None  # R2 endpoint URL (e.g., https://<account-id>.r2.cloudflarestorage.com)
    R2_BUCKET_NAME: Optional[str] = None  # R2 bucket name
    R2_REGION: str = "auto"  # R2 uses "auto" for compatibility
    
    # S3 (AWS) configuration - Source for migration (legacy)
    S3_SOURCE_ACCESS_KEY_ID: Optional[str] = None  # S3 Access Key ID (source for migration)
    S3_SOURCE_SECRET_ACCESS_KEY: Optional[str] = None  # S3 Secret Access Key (source for migration)
    S3_SOURCE_REGION: str = "us-east-1"  # S3 bucket region
    S3_SOURCE_BUCKET_NAME: Optional[str] = None  # S3 bucket name (source for migration)
    
    # Legacy aliases for backward compatibility (will be removed after migration)
    # These map to R2 values after migration is complete
    AWS_ACCESS_KEY_ID: Optional[str] = None  # DEPRECATED: Use R2_ACCESS_KEY_ID
    AWS_SECRET_ACCESS_KEY: Optional[str] = None  # DEPRECATED: Use R2_SECRET_ACCESS_KEY
    AWS_REGION: str = "auto"  # DEPRECATED: Use R2_REGION
    S3_BUCKET_NAME: Optional[str] = None  # DEPRECATED: Use R2_BUCKET_NAME
    S3_PHOTO_PREFIX: str = "posts/photos"  # DEPRECATED: Use STORAGE_PHOTO_PREFIX
    S3_AVATAR_PREFIX: str = "users/avatars"  # DEPRECATED: Use STORAGE_AVATAR_PREFIX
    S3_PRESIGNED_URL_EXPIRATION: int = 3600  # DEPRECATED: Use STORAGE_PRESIGNED_URL_EXPIRATION
    
    # Google OAuth configuration - Loaded from environment variables
    GOOGLE_CLIENT_ID: Optional[str] = None  # Must be set via environment variable
    GOOGLE_CLIENT_SECRET: Optional[str] = None  # Must be set via environment variable
    GOOGLE_REDIRECT_URI: Optional[str] = None  # Must be set via environment variable
    FRONTEND_URL: str = "http://localhost:5173"  # For redirects after OAuth
    
    # Moderator configuration
    MODERATOR_EMAILS: Optional[str] = None  # Comma-separated list of moderator emails

    @field_validator('SECRET_KEY')
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Ensure SECRET_KEY is secure."""
        if not v or len(v) < 32:
            raise ValueError('SECRET_KEY must be at least 32 characters long. Set via environment variable.')
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # Ignore extra environment variables
        # Ensure we read from environment variables first
        case_sensitive=True
    )


settings = Settings()
