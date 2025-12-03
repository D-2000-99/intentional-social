from datetime import datetime, timezone, timedelta
import logging
from functools import wraps
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import or_
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.deps import get_db, get_current_user
from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
)
from app.core.email import generate_otp, send_otp_email
from app.models.user import User
from app.models.email_verification import EmailVerification
from app.schemas.user import UserCreate, UserOut
from app.schemas.auth import Token, LoginRequest, SendOTPRequest, VerifyOTPRequest, CompleteRegistrationRequest

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


@router.post("/send-registration-otp")
@rate_limit("3/hour")
def send_registration_otp(request: Request, payload: SendOTPRequest, db: Session = Depends(get_db)):
    """
    Send OTP for email verification during registration.
    Rate limited to 3 requests per hour per IP address.
    """
    # Check if email already registered
    existing_user = db.query(User).filter(User.email == payload.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    
    # Generate OTP
    otp_code = generate_otp()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    
    # Invalidate any existing unverified OTPs for this email
    db.query(EmailVerification).filter(
        EmailVerification.email == payload.email,
        EmailVerification.verified_at.is_(None),
    ).update({"verified_at": datetime.now(timezone.utc)})
    
    # Create verification record
    verification = EmailVerification(
        user_id=None,  # Will be set when user registers
        email=payload.email,
        otp_code=otp_code,
        expires_at=expires_at,
    )
    
    db.add(verification)
    db.commit()
    
    # Send email
    if not send_otp_email(payload.email, otp_code):
        logger.error(f"Failed to send OTP email to {payload.email}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send verification email. Please try again later.",
        )
    
    logger.info(f"Registration OTP sent to {payload.email}")
    return {"detail": "Verification code sent to your email"}


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
@rate_limit("3/hour")
def complete_registration(request: Request, payload: CompleteRegistrationRequest, db: Session = Depends(get_db)):
    """
    Complete registration by verifying OTP and creating account.
    Requires valid OTP code sent to email.
    """
    # Check if email already registered
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Check if username already taken
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken",
        )
    
    # Verify OTP
    verification = (
        db.query(EmailVerification)
        .filter(
            EmailVerification.email == payload.email,
            EmailVerification.otp_code == payload.otp_code,
            EmailVerification.expires_at > datetime.now(timezone.utc),
            EmailVerification.verified_at.is_(None),
        )
        .first()
    )
    
    if not verification:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification code",
        )
    
    # Validate password using schema validation
    # OTP validation is handled by CompleteRegistrationRequest schema
    from app.schemas.user import UserCreate
    try:
        UserCreate(email=payload.email, username=payload.username, password=payload.password)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    
    # Create user
    hashed = get_password_hash(payload.password)
    new_user = User(
        email=payload.email,
        username=payload.username,
        hashed_password=hashed,
        email_verified="true",
    )

    db.add(new_user)
    db.flush()  # Get user ID without committing
    
    # Mark verification as used
    verification.user_id = new_user.id
    verification.verified_at = datetime.now(timezone.utc)
    
    db.commit()
    db.refresh(new_user)

    logger.info(f"New user registered: {new_user.username} ({new_user.email})")
    return new_user


@router.post("/login", response_model=Token)
@rate_limit("5/minute")
def login(request: Request, payload: LoginRequest, db: Session = Depends(get_db)):
    user = (
        db.query(User)
        .filter(
            (User.email == payload.username_or_email)
            | (User.username == payload.username_or_email)
        )
        .first()
    )

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect credentials",
        )

    token = create_access_token(subject=user.id)

    return Token(access_token=token)


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


@router.post("/send-verification-email")
@rate_limit("3/hour")
def send_verification_email(
    request: Request,
    payload: SendOTPRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Send OTP to user's email for verification."""
    
    # Verify email belongs to current user
    if current_user.email != payload.email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only verify your own email address",
        )
    
    # Check if already verified
    if current_user.email_verified == "true":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already verified",
        )
    
    # Generate OTP
    otp_code = generate_otp()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    
    # Invalidate any existing OTPs for this user
    db.query(EmailVerification).filter(
        EmailVerification.user_id == current_user.id,
        EmailVerification.verified_at.is_(None),
    ).update({"verified_at": datetime.now(timezone.utc)})
    
    # Create new verification record
    verification = EmailVerification(
        user_id=current_user.id,
        email=payload.email,
        otp_code=otp_code,
        expires_at=expires_at,
    )
    
    db.add(verification)
    db.commit()
    
    # Send email
    if send_otp_email(payload.email, otp_code):
        return {"detail": "Verification email sent"}
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send verification email",
        )


@router.post("/verify-email")
def verify_email(
    payload: VerifyOTPRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Verify email using OTP code."""
    
    # Verify email belongs to current user
    if current_user.email != payload.email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only verify your own email address",
        )
    
    # Find valid OTP
    verification = (
        db.query(EmailVerification)
        .filter(
            EmailVerification.user_id == current_user.id,
            EmailVerification.email == payload.email,
            EmailVerification.otp_code == payload.otp_code,
            EmailVerification.expires_at > datetime.now(timezone.utc),
            EmailVerification.verified_at.is_(None),
        )
        .first()
    )
    
    if not verification:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OTP code",
        )
    
    # Mark as verified
    verification.verified_at = datetime.now(timezone.utc)
    current_user.email_verified = "true"
    
    db.commit()
    
    return {"detail": "Email verified successfully"}