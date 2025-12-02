from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.core.deps import get_db, get_current_user
from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
)
from app.models.user import User
from app.schemas.user import UserCreate, UserOut
from app.schemas.auth import Token, LoginRequest

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register_user(payload: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken",
        )

    hashed = get_password_hash(payload.password)

    new_user = User(
        email=payload.email,
        username=payload.username,
        hashed_password=hashed,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


@router.post("/login", response_model=Token)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
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