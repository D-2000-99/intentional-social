from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.deps import get_db, get_current_user
from app.models.user import User
from app.models.connection import Connection
from app.models.tag import Tag
from app.models.user_tag import UserTag
from app.schemas.tag import ConnectionTagCreate, ConnectionTagOut, TagOut

router = APIRouter(prefix="/connections", tags=["Connection Tags"])


@router.get("/{connection_id}/tags", response_model=list[TagOut])
def get_connection_tags(
    connection_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all tags for a specific connection (tags that current user has applied to the other user)"""
    # Verify connection belongs to current user
    connection = db.query(Connection).filter(Connection.id == connection_id).first()
    
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection not found",
        )
    
    # Must be part of the connection
    if connection.user_a_id != current_user.id and connection.user_b_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized",
        )
    
    # Determine the target user (the other user in the connection)
    target_user_id = connection.user_b_id if connection.user_a_id == current_user.id else connection.user_a_id
    
    # Get tags that current user (owner) has applied to the target user
    # Only return tags that belong to the current user
    user_tags_query = (
        db.query(UserTag)
        .options(joinedload(UserTag.tag))
        .join(Tag, UserTag.tag_id == Tag.id)
        .filter(
            UserTag.owner_user_id == current_user.id,
            UserTag.target_user_id == target_user_id,
            Tag.owner_user_id == current_user.id  # CRITICAL: Only show tags owned by current user
        )
        .all()
    )
    
    # Extract tags
    tags = [ut.tag for ut in user_tags_query if ut.tag]
    return tags


@router.post("/{connection_id}/tags", status_code=status.HTTP_201_CREATED)
def add_tag_to_connection(
    connection_id: int,
    payload: ConnectionTagCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a tag to a connection (tag the other user with one of your tags)"""
    # Verify connection belongs to current user
    connection = db.query(Connection).filter(Connection.id == connection_id).first()
    
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection not found",
        )
    
    if connection.user_a_id != current_user.id and connection.user_b_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized",
        )
    
    # Determine the target user (the other user in the connection)
    target_user_id = connection.user_b_id if connection.user_a_id == current_user.id else connection.user_a_id
    
    # Verify tag belongs to current user
    tag = db.query(Tag).filter(Tag.id == payload.tag_id, Tag.owner_user_id == current_user.id).first()
    
    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found",
        )
    
    # Check if already tagged
    existing = (
        db.query(UserTag)
        .filter(
            UserTag.owner_user_id == current_user.id,
            UserTag.target_user_id == target_user_id,
            UserTag.tag_id == payload.tag_id,
        )
        .first()
    )
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User already has this tag",
        )
    
    # Create user tag
    user_tag = UserTag(
        owner_user_id=current_user.id,
        target_user_id=target_user_id,
        tag_id=payload.tag_id,
    )
    
    db.add(user_tag)
    db.commit()
    
    return {"detail": "Tag added to connection"}


@router.delete("/{connection_id}/tags/{tag_id}")
def remove_tag_from_connection(
    connection_id: int,
    tag_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove a tag from a connection"""
    # Verify connection belongs to current user
    connection = db.query(Connection).filter(Connection.id == connection_id).first()
    
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection not found",
        )
    
    if connection.user_a_id != current_user.id and connection.user_b_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized",
        )
    
    # Determine the target user (the other user in the connection)
    target_user_id = connection.user_b_id if connection.user_a_id == current_user.id else connection.user_a_id
    
    # Verify tag belongs to current user
    tag = db.query(Tag).filter(Tag.id == tag_id, Tag.owner_user_id == current_user.id).first()
    
    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found",
        )
    
    # Find and delete user tag
    user_tag = (
        db.query(UserTag)
        .filter(
            UserTag.owner_user_id == current_user.id,
            UserTag.target_user_id == target_user_id,
            UserTag.tag_id == tag_id,
        )
        .first()
    )
    
    if not user_tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found on this connection",
        )
    
    db.delete(user_tag)
    db.commit()
    
    return {"detail": "Tag removed from connection"}
