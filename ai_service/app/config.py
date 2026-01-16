"""
Configuration for AI Service

Loads settings from environment variables.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database configuration (shared with main backend)
    DATABASE_URL: str
    
    # OpenAI configuration
    OPENAI_API_KEY: str
    OPENAI_MODEL_NAME: str = "gpt-4o-mini"  # Default to gpt-4o-mini, can be overridden
    
    # Service configuration
    LOG_LEVEL: str = "INFO"
    PROCESS_BATCH_SIZE: int = 1  # For now, process one at a time
    
    # Image processing
    MAX_IMAGE_SIZE_MB: int = 20  # Maximum image size to process
    IMAGE_DETAIL_LEVEL: str = "low"  # "low", "high", or "auto" for OpenAI vision
    
    # S3/R2 configuration (optional - for generating presigned URLs from S3 keys)
    R2_ACCESS_KEY_ID: Optional[str] = None
    R2_SECRET_ACCESS_KEY: Optional[str] = None
    R2_ENDPOINT_URL: Optional[str] = None
    R2_BUCKET_NAME: Optional[str] = None
    R2_REGION: str = "auto"
    STORAGE_PRESIGNED_URL_EXPIRATION: int = 3600  # 1 hour
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True
    )


settings = Settings()

