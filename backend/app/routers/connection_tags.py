from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.deps import get_db, get_current_user
from app.models.user import User
from app.models.connection import Connection
from app.models.tag import Tag
from app.models.connection_tag import ConnectionTag
from app.schemas.tag import ConnectionTagCreate, ConnectionTagOut, TagOut

router = APIRouter(prefix="/connections", tags=["Connection Tags"])


@router.get("/{connection_id}/tags", response_model=list[TagOut])
def get_connection_tags(
    connection_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all tags for a specific connection"""
    # Verify connection belongs to current user
    connection = db.query(Connection).filter(Connection.id == connection_id).first()
    
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection not found",
        )
    
    # Must be part of the connection
    if connection.requester_id != current_user.id and connection.recipient_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized",
        )
    
    # Get tags for this connection that belong to the current user
    connection_tags = (
        db.query(ConnectionTag)
        .options(joinedload(ConnectionTag.tag))
        .join(Tag, ConnectionTag.tag_id == Tag.id)
        .filter(
            ConnectionTag.connection_id == connection_id,
            Tag.user_id == current_user.id
        )
        .all()
    )
    
    return [ct.tag for ct in connection_tags]


@router.post("/{connection_id}/tags", status_code=status.HTTP_201_CREATED)
def add_tag_to_connection(
    connection_id: int,
    payload: ConnectionTagCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a tag to a connection"""
    # Verify connection belongs to current user
    connection = db.query(Connection).filter(Connection.id == connection_id).first()
    
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection not found",
        )
    
    if connection.requester_id != current_user.id and connection.recipient_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized",
        )
    
    # Verify tag belongs to current user
    tag = db.query(Tag).filter(Tag.id == payload.tag_id, Tag.user_id == current_user.id).first()
    
    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found",
        )
    
    # Check if already tagged
    existing = (
        db.query(ConnectionTag)
        .filter(
            ConnectionTag.connection_id == connection_id,
            ConnectionTag.tag_id == payload.tag_id,
        )
        .first()
    )
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Connection already has this tag",
        )
    
    # Create connection tag
    connection_tag = ConnectionTag(
        connection_id=connection_id,
        tag_id=payload.tag_id,
    )
    
    db.add(connection_tag)
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
    
    if connection.requester_id != current_user.id and connection.recipient_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized",
        )
    
    # Verify tag belongs to current user
    tag = db.query(Tag).filter(Tag.id == tag_id, Tag.user_id == current_user.id).first()
    
    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found",
        )
    
    # Find and delete connection tag
    connection_tag = (
        db.query(ConnectionTag)
        .filter(
            ConnectionTag.connection_id == connection_id,
            ConnectionTag.tag_id == tag_id,
        )
        .first()
    )
    
    if not connection_tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found on this connection",
        )
    
    db.delete(connection_tag)
    db.commit()
    
    return {"detail": "Tag removed from connection"}
