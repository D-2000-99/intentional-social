import logging
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import settings
from app.core.deps import get_db, get_moderator_user
from app.core.oauth import (
    generate_pkce_pair,
    generate_state,
    get_google_authorization_url,
    exchange_code_for_tokens,
    verify_google_id_token,
)
from app.core.security import create_access_token
from app.models.user import User
from app.schemas.auth import GoogleOAuthCallbackRequest, GoogleOAuthCallbackResponse

router = APIRouter(prefix="/auth", tags=["Auth"])
logger = logging.getLogger(__name__)

# Rate limiter will be set by main.py after app initialization
limiter = None


def rate_limit(limit_str: str):
    """Helper function to conditionally apply rate limiting."""
    def decorator(func):
        func._rate_limit = limit_str
        if limiter is not None:
            return limiter.limit(limit_str)(func)
        return func
    return decorator


@router.get("/google/authorize")
@rate_limit("10/minute")
async def initiate_google_oauth(request: Request):
    """Initiate Google OAuth flow for moderators."""
    try:
        code_verifier, code_challenge = generate_pkce_pair()
        state = generate_state()
        auth_url = get_google_authorization_url(state, code_challenge)
        
        return {
            "authorization_url": auth_url,
            "state": state,
            "code_verifier": code_verifier,
        }
    except Exception as e:
        logger.error(f"Error initiating OAuth: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate OAuth flow"
        )


@router.get("/google/callback")
@rate_limit("10/minute")
async def google_oauth_callback_get(
    request: Request,
    code: str,
    state: str,
):
    """Handle Google OAuth callback GET request."""
    # Redirect to observability frontend
    frontend_base = settings.OBSERVABILITY_CORS_ORIGINS.split(",")[0].strip()
    frontend_url = f"{frontend_base}/login?code={code}&state={state}"
    
    logger.info(f"OAuth callback redirecting to: {frontend_url}")
    return RedirectResponse(url=frontend_url)


@router.post("/google/callback", response_model=GoogleOAuthCallbackResponse)
@rate_limit("10/minute")
async def google_oauth_callback(
    request: Request,
    payload: GoogleOAuthCallbackRequest,
    db: Session = Depends(get_db),
):
    """Handle Google OAuth callback POST request and verify moderator email."""
    try:
        # Exchange authorization code for tokens
        tokens = await exchange_code_for_tokens(
            code=payload.code,
            code_verifier=payload.code_verifier
        )
        
        # Verify ID token and extract user info
        id_token_str = tokens.get("id_token")
        if not id_token_str:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No ID token received from Google"
            )
        
        # Verify token signature and get user info
        google_user_info = verify_google_id_token(id_token_str)
        
        # Extract user data from Google
        google_id = google_user_info.get("sub")
        email = google_user_info.get("email")
        full_name = google_user_info.get("name")
        picture_url = google_user_info.get("picture")
        
        if not google_id or not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing required information from Google"
            )
        
        # Check if email is in moderator list
        moderator_emails = settings.get_moderator_emails_list()
        if not moderator_emails:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Moderator emails not configured"
            )
        
        if email.lower() not in moderator_emails:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. Your email is not authorized as a moderator."
            )
        
        # Check if user exists by google_id
        user = db.query(User).filter(User.google_id == google_id).first()
        
        if user:
            # Update info if needed
            if full_name and not user.full_name:
                user.full_name = full_name
            if picture_url and not user.picture_url:
                user.picture_url = picture_url
            db.commit()
            db.refresh(user)
        else:
            # Create user if they don't exist
            existing_by_email = db.query(User).filter(User.email == email).first()
            if existing_by_email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered with different account"
                )
            
            user = User(
                email=email,
                username=None,
                google_id=google_id,
                auth_provider="google",
                full_name=full_name,
                picture_url=picture_url,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            logger.info(f"New moderator user created: {user.email}")
        
        # Generate JWT token
        token = create_access_token(subject=user.id)
        
        from app.schemas.user import UserOut
        
        return {
            "access_token": token,
            "token_type": "bearer",
            "needs_username": user.username is None,
            "user": UserOut.model_validate(user),
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in OAuth callback: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OAuth callback failed: {str(e)}"
        )


@router.get("/me")
def get_current_moderator(
    current_user: User = Depends(get_moderator_user),
):
    """Get current moderator user details."""
    from app.schemas.user import UserOut
    return UserOut.model_validate(current_user)

