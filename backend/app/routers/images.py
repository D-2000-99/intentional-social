import logging
from typing import Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from jose import JWTError
from sqlalchemy.orm import Session

from app.config import settings
from app.core.image_urls import is_storage_key
from app.core.security import decode_access_token
from app.core.deps import get_db
from app.core.s3 import generate_presigned_url
from app.models.user import User

router = APIRouter(prefix="/images", tags=["Images"])

logger = logging.getLogger(__name__)


def _get_authenticated_user(
    db: Session,
    authorization: Optional[str],
    token: Optional[str],
) -> User:
    auth_token = token
    if not auth_token and authorization and authorization.lower().startswith("bearer "):
        auth_token = authorization.split(" ", 1)[1].strip()

    if not auth_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_access_token(auth_token)
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user.is_banned:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been banned. Please contact support if you believe this is an error.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


@router.get("/{s3_key:path}")
def get_image_redirect(
    s3_key: str,
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
    token: Optional[str] = Query(default=None),
):
    """
    Redirect to a presigned URL for a storage object.
    This allows stable image URLs while keeping storage private.
    """
    _get_authenticated_user(db, authorization, token)
    if not is_storage_key(s3_key):
        raise HTTPException(status_code=404, detail="Image not found")

    try:
        presigned_url = generate_presigned_url(
            s3_key,
            expiration=settings.STORAGE_PRESIGNED_URL_EXPIRATION,
            response_cache_control=settings.STORAGE_IMAGE_CACHE_CONTROL,
        )
    except Exception as exc:
        logger.warning(f"Failed to generate presigned URL for {s3_key}: {exc}")
        raise HTTPException(status_code=500, detail="Failed to generate image URL") from exc

    response = RedirectResponse(url=presigned_url, status_code=302)
    response.headers["Cache-Control"] = f"private, max-age={settings.STORAGE_REDIRECT_CACHE_MAX_AGE}"
    response.headers["Vary"] = "Authorization"
    return response
