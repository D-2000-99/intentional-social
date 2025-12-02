from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, aliased

from app.core.deps import get_db, get_current_user
from app.models.user import User
from app.models.follow import Follow

from app.config import settings

router = APIRouter(prefix="/follows", tags=["Follows"])


@router.post("/{followee_id}", status_code=status.HTTP_201_CREATED)
def follow_user(
    followee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if followee_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot follow yourself",
        )

    followee = db.query(User).filter(User.id == followee_id).first()
    if not followee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Duplicate check
    existing = (
        db.query(Follow)
        .filter(
            Follow.follower_id == current_user.id,
            Follow.followee_id == followee_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Already following this user",
        )

    # Count enforcement
    count = (
        db.query(Follow)
        .filter(Follow.follower_id == current_user.id)
        .count()
    )
    if count >= settings.MAX_FOLLOWS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"You already follow the maximum ({settings.MAX_FOLLOWS}) users",
        )

    record = Follow(
        follower_id=current_user.id,
        followee_id=followee_id,
    )
    db.add(record)
    db.commit()

    return {"detail": f"You are now following {followee.username}"}


@router.delete("/{followee_id}", status_code=status.HTTP_200_OK)
def unfollow_user(
    followee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rel = (
        db.query(Follow)
        .filter(
            Follow.follower_id == current_user.id,
            Follow.followee_id == followee_id,
        )
        .first()
    )

    if not rel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You are not following this user",
        )

    db.delete(rel)
    db.commit()

    return {"detail": "Unfollowed successfully"}
