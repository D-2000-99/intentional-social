from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import jwt, JWTError

from app.config import settings

def create_access_token(
    subject: str | int,
    expires_delta: Optional[timedelta] = None,
):
    if expires_delta is None:
        expires_delta = timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode = {
        "sub": str(subject),
        "exp": datetime.now(timezone.utc) + expires_delta,
    }

    return jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )

def decode_access_token(token: str):
    return jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=[settings.ALGORITHM],
    )
