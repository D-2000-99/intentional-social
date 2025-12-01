from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_current_user
from app.models.post import Post
from app.schemas.post import PostCreate, PostOut
from app.models.user import User

router = APIRouter(prefix="/posts", tags=["Posts"])


@router.post("/", response_model=PostOut, status_code=status.HTTP_201_CREATED)
def create_post(
    payload: PostCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    new_post = Post(
        author_id=current_user.id,
        content=payload.content,
    )

    db.add(new_post)
    db.commit()
    db.refresh(new_post)

    return new_post
