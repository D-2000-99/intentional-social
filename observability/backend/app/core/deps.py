from typing import Generator, Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.config import settings
from app.core.security import decode_access_token
from app.db import SessionLocal
from app.models.user import User


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def get_db() -> Generator:
    """Get database session - uses main backend's database."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_moderator_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Session = Depends(get_db)
) -> User:
    """
    Get current user and verify they are a moderator.
    Checks both JWT validity and that email is in MODERATOR_EMAILS list.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = decode_access_token(token)
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise credentials_exception
    
    # Check if user is banned
    if user.is_banned:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been banned.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if user email is in moderator list
    moderator_emails = settings.get_moderator_emails_list()
    if not moderator_emails:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Moderator emails not configured"
        )
    
    if user.email.lower() not in moderator_emails:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Moderator privileges required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user

