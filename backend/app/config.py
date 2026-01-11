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
    
    # S3 configuration for photo storage - Loaded from environment variables
    # These are required if using S3 for file storage
    AWS_ACCESS_KEY_ID: Optional[str] = None  # Must be set via environment variable
    AWS_SECRET_ACCESS_KEY: Optional[str] = None  # Must be set via environment variable
    AWS_REGION: str = "us-east-1"
    S3_BUCKET_NAME: Optional[str] = None  # Must be set via environment variable
    S3_PHOTO_PREFIX: str = "posts/photos"  # Prefix for photo objects in S3
    S3_AVATAR_PREFIX: str = "users/avatars"  # Prefix for avatar objects in S3
    S3_PRESIGNED_URL_EXPIRATION: int = 3600  # 1 hour in seconds
    
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
