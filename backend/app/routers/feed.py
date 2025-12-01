from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_current_user
from app.models.post import Post
from app.models.follow import Follow
from app.models.user import User
from app.schemas.post import PostOut

router = APIRouter(prefix="/feed", tags=["Feed"])


@router.get("/", response_model=list[PostOut])
def get_feed(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Get list of followees the user is following
    followee_subq = (
        db.query(Follow.followee_id)
        .filter(Follow.follower_id == current_user.id)
        .subquery()
    )

    posts = (
        db.query(Post)
        .filter(Post.author_id.in_(followee_subq))
        .order_by(Post.created_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )

    return posts
