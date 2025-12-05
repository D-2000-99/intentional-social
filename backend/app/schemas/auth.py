from pydantic import BaseModel, field_validator
from typing import Optional
from app.schemas.user import UserOut

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class GoogleOAuthCallbackRequest(BaseModel):
    code: str
    state: str
    code_verifier: str

class GoogleOAuthCallbackResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    needs_username: bool = False
    user: UserOut

class UsernameSelectionRequest(BaseModel):
    username: str
    
    @field_validator('username')
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not v or len(v) < 3:
            raise ValueError('Username must be at least 3 characters long')
        if len(v) > 50:
            raise ValueError('Username must be at most 50 characters long')
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Username can only contain letters, numbers, underscores, and hyphens')
        return v.lower()  # Normalize to lowercase
