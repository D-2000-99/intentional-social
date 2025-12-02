from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session, joinedload

from app.core.deps import get_db, get_current_user
from app.models.post import Post
from app.models.post_audience_tag import PostAudienceTag
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
        audience_type=payload.audience_type,
    )

    db.add(new_post)
    db.commit()
    db.refresh(new_post)
    
    # If audience is tags, create post_audience_tags
    if payload.audience_type == "tags" and payload.audience_tag_ids:
        for tag_id in payload.audience_tag_ids:
            audience_tag = PostAudienceTag(
                post_id=new_post.id,
                tag_id=tag_id,
            )
            db.add(audience_tag)
        db.commit()

    return new_post


@router.get("/me", response_model=list[PostOut])
def get_my_posts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all posts by the current user"""
    posts = (
        db.query(Post)
        .options(joinedload(Post.author))
        .filter(Post.author_id == current_user.id)
        .order_by(Post.created_at.desc())
        .all()
    )
    return posts
