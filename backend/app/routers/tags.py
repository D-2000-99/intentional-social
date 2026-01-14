from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_current_user
from app.models.user import User
from app.models.tag import Tag
from app.schemas.tag import TagCreate, TagUpdate, TagOut

router = APIRouter(prefix="/tags", tags=["Tags"])


@router.get("", response_model=list[TagOut])
def get_user_tags(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all tags for the current user"""
    tags = (
        db.query(Tag)
        .filter(Tag.owner_user_id == current_user.id)
        .order_by(Tag.created_at)
        .all()
    )
    return tags


@router.post("", response_model=TagOut, status_code=status.HTTP_201_CREATED)
def create_tag(
    payload: TagCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new tag"""
    # Check if tag name already exists for this user
    existing = (
        db.query(Tag)
        .filter(Tag.owner_user_id == current_user.id, Tag.name == payload.name)
        .first()
    )
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Tag '{payload.name}' already exists",
        )
    
    new_tag = Tag(
        owner_user_id=current_user.id,
        name=payload.name,
        color_scheme=payload.color_scheme,
    )
    
    db.add(new_tag)
    db.commit()
    db.refresh(new_tag)
    
    return new_tag


@router.put("/{tag_id}", response_model=TagOut)
def update_tag(
    tag_id: int,
    payload: TagUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a tag"""
    tag = db.query(Tag).filter(Tag.id == tag_id, Tag.owner_user_id == current_user.id).first()
    
    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found",
        )
    
    if payload.name:
        # Check for duplicate name
        existing = (
            db.query(Tag)
            .filter(
                Tag.owner_user_id == current_user.id,
                Tag.name == payload.name,
                Tag.id != tag_id,
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Tag '{payload.name}' already exists",
            )
        tag.name = payload.name
    
    if payload.color_scheme:
        tag.color_scheme = payload.color_scheme
    
    db.commit()
    db.refresh(tag)
    
    return tag


@router.delete("/{tag_id}")
def delete_tag(
    tag_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a tag"""
    tag = db.query(Tag).filter(Tag.id == tag_id, Tag.owner_user_id == current_user.id).first()
    
    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found",
        )
    
    db.delete(tag)
    db.commit()
    
    return {"detail": "Tag deleted successfully"}
