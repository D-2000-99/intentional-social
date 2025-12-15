from datetime import datetime, timezone
import logging
from functools import wraps
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_
from slowapi import Limiter
from slowapi.util import get_remote_address

from fastapi import UploadFile, File, Form
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
from app.core.s3 import validate_image, upload_avatar_to_s3, generate_presigned_url, delete_photo_from_s3
from app.config import settings
from app.models.user import User
from app.schemas.user import UserOut, UserCreate, UserBioUpdate
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


@router.get("/google/callback")
@rate_limit("10/minute")
async def google_oauth_callback_get(
    request: Request,
    code: str = Query(...),
    state: str = Query(...),
):
    """
    Handle Google OAuth callback GET request (redirect from Google).
    Redirects to frontend with code/state so frontend can complete the flow.
    """
    from app.config import settings
    
    # Redirect to frontend with code and state
    # Frontend will extract these and make POST request with code_verifier
    # Remove trailing slash from FRONTEND_URL to avoid double slashes
    frontend_base = settings.FRONTEND_URL.rstrip('/')
    frontend_url = f"{frontend_base}/login?code={code}&state={state}"
    
    # Log for debugging (helps identify which backend is handling the request)
    logger.info(f"OAuth callback redirecting to: {frontend_url} (FRONTEND_URL={settings.FRONTEND_URL})")
    
    return RedirectResponse(url=frontend_url)


@router.post("/google/callback", response_model=GoogleOAuthCallbackResponse)
@rate_limit("10/minute")
async def google_oauth_callback(
    request: Request,
    payload: GoogleOAuthCallbackRequest,
    db: Session = Depends(get_db),
):
    """
    Handle Google OAuth callback POST request (from frontend).
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
            
            # Create user without username - user must set it via username selection endpoint
            user = User(
                email=email,
                username=None,  # User must set username during registration
                google_id=google_id,
                auth_provider="google",
                full_name=full_name,
                picture_url=picture_url,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            
            logger.info(f"New Google OAuth user created without username: {user.email}")
        
        # Generate our JWT token
        token = create_access_token(subject=user.id)
        
        # Check if user needs to set username - only if username is NULL
        needs_username = user.username is None
        
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
    Username can only be set once and cannot be changed.
    """
    # Check if user already has a username set
    if current_user.username is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username has already been set and cannot be changed"
        )
    
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
    
    # Set username (permanent, cannot be changed)
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
    user_out = UserOut.model_validate(current_user)
    
    # If avatar_url is an S3 key, generate presigned URL
    if user_out.avatar_url and user_out.avatar_url.startswith(settings.S3_AVATAR_PREFIX):
        try:
            user_out.avatar_url = generate_presigned_url(user_out.avatar_url)
        except Exception as e:
            logger.warning(f"Failed to generate presigned URL for avatar: {str(e)}")
            # Keep the S3 key if presigned URL generation fails
    
    return user_out


@router.get("/user/{username}", response_model=UserOut)
def get_user_by_username(
    username: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get user profile by username"""
    user = db.query(User).filter(User.username == username).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user_out = UserOut.model_validate(user)
    
    # If avatar_url is an S3 key, generate presigned URL
    if user_out.avatar_url and user_out.avatar_url.startswith(settings.S3_AVATAR_PREFIX):
        try:
            user_out.avatar_url = generate_presigned_url(user_out.avatar_url)
        except Exception as e:
            logger.warning(f"Failed to generate presigned URL for avatar: {str(e)}")
            # Keep the S3 key if presigned URL generation fails
    
    return user_out


@router.put("/me/avatar", response_model=UserOut)
@rate_limit("10/minute")
async def update_user_avatar(
    avatar: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update user's avatar image.
    Accepts multipart/form-data with avatar file.
    """
    try:
        # Read file content
        file_content = await avatar.read()
        
        # Validate image
        is_valid, error_msg, image_info = validate_image(file_content, max_size_mb=0.2)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Avatar validation failed: {error_msg}"
            )
        
        # Determine file extension from content type or filename
        file_extension = "jpg"  # default
        if avatar.filename:
            if avatar.filename.lower().endswith(('.png',)):
                file_extension = "png"
            elif avatar.filename.lower().endswith(('.webp',)):
                file_extension = "webp"
        elif image_info and image_info.get('format'):
            format_lower = image_info['format'].lower()
            if format_lower == 'png':
                file_extension = "png"
            elif format_lower == 'webp':
                file_extension = "webp"
        
        # Delete old avatar from S3 if it exists and is an S3 URL
        if current_user.avatar_url:
            # Check if it's an S3 key (starts with our prefix)
            if current_user.avatar_url.startswith(settings.S3_AVATAR_PREFIX):
                try:
                    delete_photo_from_s3(current_user.avatar_url)
                except Exception as e:
                    logger.warning(f"Failed to delete old avatar from S3: {str(e)}")
        
        # Upload new avatar to S3
        s3_key = upload_avatar_to_s3(file_content, current_user.id, file_extension)
        
        # Generate presigned URL for the avatar
        avatar_url = generate_presigned_url(s3_key)
        
        # Update user's avatar_url (store the S3 key, not the presigned URL)
        # We'll generate presigned URLs when needed
        current_user.avatar_url = s3_key
        db.commit()
        db.refresh(current_user)
        
        logger.info(f"User {current_user.id} updated avatar to {s3_key}")
        
        # Return user with presigned URL in avatar_url for immediate use
        user_out = UserOut.model_validate(current_user)
        # Override avatar_url with presigned URL for response
        user_out.avatar_url = avatar_url
        return user_out
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating avatar: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update avatar: {str(e)}"
        )


@router.put("/me/bio", response_model=UserOut)
@rate_limit("10/minute")
def update_user_bio(
    payload: UserBioUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update user's bio/note.
    Accepts a JSON body with optional bio field (max 500 characters).
    """
    try:
        # Validate bio length if provided
        if payload.bio is not None and len(payload.bio) > 500:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bio must be 500 characters or less"
            )
        
        # Update bio
        current_user.bio = payload.bio
        db.commit()
        db.refresh(current_user)
        
        logger.info(f"User {current_user.id} updated bio")
        
        # Return user with presigned URL for avatar if needed
        user_out = UserOut.model_validate(current_user)
        if user_out.avatar_url and user_out.avatar_url.startswith(settings.S3_AVATAR_PREFIX):
            try:
                user_out.avatar_url = generate_presigned_url(user_out.avatar_url)
            except Exception as e:
                logger.warning(f"Failed to generate presigned URL for avatar: {str(e)}")
        
        return user_out
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating bio: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update bio: {str(e)}"
        )
