from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_
import logging

from app.core.deps import get_db, get_current_user
from app.config import settings
from app.models.user import User
from app.models.connection import Connection, ConnectionStatus
from app.schemas.connection import ConnectionOut, ConnectionWithUser

router = APIRouter(prefix="/connections", tags=["Connections"])
logger = logging.getLogger(__name__)


@router.post("/request/{recipient_id}", status_code=status.HTTP_201_CREATED)
def send_connection_request(
    recipient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Send a connection request to another user"""
    
    # Can't connect to yourself
    if recipient_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot connect with yourself",
        )

    # Check if user has reached the maximum number of connections
    accepted_count = (
        db.query(Connection)
        .filter(
            or_(
                Connection.user_a_id == current_user.id,
                Connection.user_b_id == current_user.id,
            ),
            Connection.status == ConnectionStatus.ACCEPTED,
        )
        .count()
    )

    if accepted_count >= settings.MAX_CONNECTIONS:
        logger.warning(
            f"User {current_user.id} ({current_user.username}) reached connection limit: {accepted_count}"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"You have reached the maximum ({settings.MAX_CONNECTIONS}) connections",
        )
    
    # Check if recipient exists
    recipient = db.query(User).filter(User.id == recipient_id).first()
    if not recipient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    # Check for existing connection (direction doesn't matter)
    # Normalize: ensure user_a_id < user_b_id for consistency
    user_a_id = min(current_user.id, recipient_id)
    user_b_id = max(current_user.id, recipient_id)
    
    existing = (
        db.query(Connection)
        .filter(
            Connection.user_a_id == user_a_id,
            Connection.user_b_id == user_b_id,
        )
        .first()
    )
    
    if existing:
        if existing.status == ConnectionStatus.PENDING:
            # If they sent us a request, auto-accept it
            # Since direction doesn't matter, if status is PENDING, we can auto-accept
            existing.status = ConnectionStatus.ACCEPTED
            db.commit()
            logger.info(
                f"Mutual connection auto-accepted between users {current_user.id} and {recipient_id}"
            )
            return {"detail": "Connection accepted (mutual request)", "connection_id": existing.id}
        elif existing.status == ConnectionStatus.ACCEPTED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Already connected",
            )
    
    # Create new connection request (normalized: user_a_id < user_b_id)
    new_connection = Connection(
        user_a_id=user_a_id,
        user_b_id=user_b_id,
        status=ConnectionStatus.PENDING,
    )
    db.add(new_connection)
    db.commit()
    db.refresh(new_connection)
    
    logger.info(f"User {current_user.id} sent connection request to user {recipient_id}")
    return {"detail": "Connection request sent", "connection_id": new_connection.id}


@router.get("/requests/incoming", response_model=list[ConnectionWithUser])
def get_incoming_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all pending connection requests sent to me."""
    
    # Get pending connections where current user is involved
    # Use joinedload to avoid N+1 queries (loads users in single query)
    requests = (
        db.query(Connection)
        .options(joinedload(Connection.user_a), joinedload(Connection.user_b))
        .filter(
            or_(
                Connection.user_a_id == current_user.id,
                Connection.user_b_id == current_user.id,
            ),
            Connection.status == ConnectionStatus.PENDING,
        )
        .all()
    )
    
    result = []
    for req in requests:
        # Determine the other user
        other_user = req.user_b if req.user_a_id == current_user.id else req.user_a
        result.append(
            ConnectionWithUser(
                id=req.id,
                status=req.status.value,  # Convert enum to string for response
                created_at=req.created_at,
                other_user_id=other_user.id,
                other_user_username=other_user.username,
            )
        )
    
    return result


@router.get("/requests/outgoing", response_model=list[ConnectionWithUser])
def get_outgoing_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all pending connection requests I sent."""
    
    # Get pending connections where current user is involved
    # Use joinedload to avoid N+1 queries
    requests = (
        db.query(Connection)
        .options(joinedload(Connection.user_a), joinedload(Connection.user_b))
        .filter(
            or_(
                Connection.user_a_id == current_user.id,
                Connection.user_b_id == current_user.id,
            ),
            Connection.status == ConnectionStatus.PENDING,
        )
        .all()
    )
    
    result = []
    for req in requests:
        # Determine the other user
        other_user = req.user_b if req.user_a_id == current_user.id else req.user_a
        result.append(
            ConnectionWithUser(
                id=req.id,
                status=req.status.value,
                created_at=req.created_at,
                other_user_id=other_user.id,
                other_user_username=other_user.username,
            )
        )
    
    return result


@router.post("/accept/{connection_id}")
def accept_connection_request(
    connection_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Accept a connection request"""
    
    connection = db.query(Connection).filter(Connection.id == connection_id).first()
    
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection request not found",
        )
    
    # Must be part of the connection to accept
    if connection.user_a_id != current_user.id and connection.user_b_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized",
        )
    
    if connection.status == ConnectionStatus.ACCEPTED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Connection already accepted",
        )
    
    # Check connection limit before accepting
    accepted_count = (
        db.query(Connection)
        .filter(
            or_(
                Connection.user_a_id == current_user.id,
                Connection.user_b_id == current_user.id,
            ),
            Connection.status == ConnectionStatus.ACCEPTED,
        )
        .count()
    )
    
    if accepted_count >= settings.MAX_CONNECTIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"You have reached the maximum ({settings.MAX_CONNECTIONS}) connections",
        )
    
    connection.status = ConnectionStatus.ACCEPTED
    db.commit()
    
    other_user_id = connection.user_b_id if connection.user_a_id == current_user.id else connection.user_a_id
    logger.info(
        f"User {current_user.id} accepted connection request {connection_id} with user {other_user_id}"
    )
    return {"detail": "Connection accepted"}


@router.delete("/reject/{connection_id}")
def reject_connection_request(
    connection_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Reject or cancel a connection request"""
    
    connection = db.query(Connection).filter(Connection.id == connection_id).first()
    
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection request not found",
        )
    
    # Must be part of the connection
    if connection.user_a_id != current_user.id and connection.user_b_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized",
        )
    
    db.delete(connection)
    db.commit()
    
    logger.info(f"User {current_user.id} rejected/cancelled connection {connection_id}")
    return {"detail": "Connection request rejected"}


@router.get("", response_model=list[ConnectionWithUser])
def get_connections(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all accepted connections."""
    
    # Use joinedload for both user_a and user_b to avoid N+1 queries
    connections = (
        db.query(Connection)
        .options(joinedload(Connection.user_a), joinedload(Connection.user_b))
        .filter(
            or_(
                Connection.user_a_id == current_user.id,
                Connection.user_b_id == current_user.id,
            ),
            Connection.status == ConnectionStatus.ACCEPTED,
        )
        .all()
    )
    
    result = []
    for conn in connections:
        # Determine the other user (already loaded via joinedload)
        other_user = conn.user_b if conn.user_a_id == current_user.id else conn.user_a
        
        result.append(
            ConnectionWithUser(
                id=conn.id,
                status=conn.status.value,
                created_at=conn.created_at,
                other_user_id=other_user.id,
                other_user_username=other_user.username,
            )
        )
    
    return result


@router.delete("/{connection_id}")
def disconnect(
    connection_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove an existing connection"""
    
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
    
    db.delete(connection)
    db.commit()
    
    return {"detail": "Disconnected successfully"}
