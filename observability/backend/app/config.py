from typing import Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Observability backend settings.
    
    IMPORTANT: All sensitive values (AWS credentials, secrets, OAuth secrets) 
    MUST be provided via environment variables, NOT hardcoded in this file.
    Load from .env file or environment variables.
    """
    
    # Database settings - REQUIRED
    DATABASE_URL: str  # Must be set via environment variable
    SECRET_KEY: str  # Must be set via environment variable (min 32 chars)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    
    # Moderator configuration
    MODERATOR_EMAILS: Optional[str] = None  # Comma-separated list of moderator emails
    
    # CORS for observability frontend
    OBSERVABILITY_CORS_ORIGINS: str = "http://localhost:5174,http://localhost:3001"
    
    # Google OAuth - Loaded from environment variables
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REDIRECT_URI: Optional[str] = None
    
    # S3 settings - Loaded from environment variables (required for user deletion)
    # These are only needed if using S3 for file storage/deletion
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: str = "us-east-1"
    S3_BUCKET_NAME: Optional[str] = None
    S3_AVATAR_PREFIX: str = "users/avatars"
    S3_PHOTO_PREFIX: str = "posts/photos"
    S3_PRESIGNED_URL_EXPIRATION: int = 3600  # 1 hour in seconds
    
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
    
    def get_moderator_emails_list(self) -> list[str]:
        """Get list of moderator emails from comma-separated string."""
        if not self.MODERATOR_EMAILS:
            return []
        return [email.strip().lower() for email in self.MODERATOR_EMAILS.split(",") if email.strip()]


settings = Settings()

