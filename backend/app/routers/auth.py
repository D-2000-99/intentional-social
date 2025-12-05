from datetime import datetime, timezone
import logging
import re
from functools import wraps
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.deps import get_db, get_current_user
from app.core.security import create_access_token
from app.core.oauth import (
    generate_pkce_pair,
    generate_state,
    get_google_authorization_url,
    exchange_code_for_tokens,
    verify_google_id_token,
    get_google_user_info,
)
from app.models.user import User
from app.schemas.user import UserOut, UserCreate
from app.schemas.auth import Token, GoogleOAuthCallbackRequest, GoogleOAuthCallbackResponse, UsernameSelectionRequest

router = APIRouter(prefix="/auth", tags=["Auth"])
logger = logging.getLogger(__name__)

# Rate limiter will be set by main.py after app initialization
limiter = None


def rate_limit(limit_str: str):
    """Helper function to conditionally apply rate limiting.
    Returns a no-op decorator if limiter is None.
    The actual rate limiting will be applied in main.py after limiter is initialized.
    """
    def decorator(func):
        # Store the limit string as an attribute so we can apply it later
        func._rate_limit = limit_str
        # If limiter is already set, apply it now
        if limiter is not None:
            return limiter.limit(limit_str)(func)
        # Otherwise, return function unchanged (will be applied in main.py)
        return func
    return decorator


@router.get("/google/authorize")
@rate_limit("10/minute")
async def initiate_google_oauth(request: Request):
    """
    Initiate Google OAuth flow.
    Generates PKCE challenge and state, then redirects to Google.
    Frontend should store code_verifier in sessionStorage.
    """
    try:
        # Generate PKCE pair
        code_verifier, code_challenge = generate_pkce_pair()
        
        # Generate state for CSRF protection
        state = generate_state()
        
        # Build authorization URL
        auth_url = get_google_authorization_url(state, code_challenge)
        
        # Return URL and verifier to frontend
        # Frontend will store code_verifier in sessionStorage and redirect to auth_url
        return {
            "authorization_url": auth_url,
            "state": state,
            "code_verifier": code_verifier,  # Frontend stores this temporarily
        }
    except Exception as e:
        logger.error(f"Error initiating OAuth: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate OAuth flow"
        )


@router.post("/google/callback", response_model=GoogleOAuthCallbackResponse)
@rate_limit("10/minute")
async def google_oauth_callback(
    request: Request,
    payload: GoogleOAuthCallbackRequest,
    db: Session = Depends(get_db),
):
    """
    Handle Google OAuth callback.
    Verifies the authorization code, exchanges for tokens, and creates/updates user.
    Returns JWT token for our API.
    """
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
        
        # Check if user exists by google_id
        user = db.query(User).filter(User.google_id == google_id).first()
        
        if user:
            # Existing user - update info if needed
            if full_name and not user.full_name:
                user.full_name = full_name
            if picture_url and not user.picture_url:
                user.picture_url = picture_url
            db.commit()
            db.refresh(user)
        else:
            # New user - check if email already exists (shouldn't happen, but safety check)
            existing_by_email = db.query(User).filter(User.email == email).first()
            if existing_by_email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered with different account"
                )
            
            # Create user but username will be set later via username selection endpoint
            # For now, use a temporary username based on email
            temp_username = email.split("@")[0].lower()[:50]
            # Ensure uniqueness
            counter = 1
            base_username = temp_username
            while db.query(User).filter(User.username == temp_username).first():
                temp_username = f"{base_username}{counter}"
                counter += 1
            
            user = User(
                email=email,
                username=temp_username,  # Temporary, user will set proper username
                google_id=google_id,
                auth_provider="google",
                full_name=full_name,
                picture_url=picture_url,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            
            logger.info(f"New Google OAuth user created: {user.username} ({user.email})")
        
        # Generate our JWT token
        token = create_access_token(subject=user.id)
        
        # Check if user needs to set username
        # Temporary usernames are based on email prefix, so check if username matches that pattern
        email_prefix = email.split("@")[0].lower()
        is_temp_username = (
            user.username == email_prefix or
            (user.username.startswith(email_prefix) and 
             re.match(f"^{re.escape(email_prefix)}\\d+$", user.username) is not None)
        )
        
        # Also check if username is very short (likely temporary)
        needs_username = is_temp_username or len(user.username) < 4
        
        return {
            "access_token": token,
            "token_type": "bearer",
            "needs_username": needs_username,
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


@router.post("/username/select")
@rate_limit("5/minute")
def select_username(
    request: Request,
    payload: UsernameSelectionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Allow user to set their username after Google OAuth registration.
    Username must be unique and meet validation requirements.
    """
    # Check if username is already taken
    existing_user = db.query(User).filter(
        User.username == payload.username,
        User.id != current_user.id
    ).first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )
    
    # Update username
    current_user.username = payload.username
    db.commit()
    db.refresh(current_user)
    
    logger.info(f"User {current_user.id} set username to {payload.username}")
    return UserOut.model_validate(current_user)


@router.get("/users", response_model=list[UserOut])
def get_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    users = db.query(User).offset(skip).limit(limit).all()
    return users


@router.get("/users/search", response_model=list[UserOut])
def search_users(
    q: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Search for users by exact username or email match"""
    if not q or len(q) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Search query must be at least 2 characters",
        )
    
    # Exact match on username or email
    results = (
        db.query(User)
        .filter(or_(User.username == q, User.email == q))
        .all()
    )

    # Exclude current user from search results
    results = [u for u in results if u.id != current_user.id]

    return results


@router.get("/me", response_model=UserOut)
def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current authenticated user's details"""
    return current_user
