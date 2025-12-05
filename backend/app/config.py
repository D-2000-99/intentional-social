from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    MAX_CONNECTIONS: int = 10
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000,https://intentional-social.pages.dev/"
    
    # Email configuration (optional for MVP - can skip in dev)
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = ""
    
    # S3 configuration for photo storage
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "us-east-1"
    S3_BUCKET_NAME: str = ""
    S3_PHOTO_PREFIX: str = "posts/photos"  # Prefix for photo objects in S3
    S3_PRESIGNED_URL_EXPIRATION: int = 3600  # 1 hour in seconds
    
    # Google OAuth configuration
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = ""
    FRONTEND_URL: str = "http://localhost:5173"  # For redirects after OAuth

    @field_validator('SECRET_KEY')
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError('SECRET_KEY must be at least 32 characters long')
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )


settings = Settings()
