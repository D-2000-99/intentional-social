from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from app.core.deps import get_db, get_current_user
from app.config import settings
from app.models.user import User
from app.models.connection import Connection
from app.schemas.connection import ConnectionOut, ConnectionWithUser

router = APIRouter(prefix="/connections", tags=["Connections"])


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
                Connection.requester_id == current_user.id,
                Connection.recipient_id == current_user.id,
            ),
            Connection.status == "accepted",
        )
        .count()
    )

    if accepted_count >= settings.MAX_FOLLOWS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"You have reached the maximum ({settings.MAX_FOLLOWS}) connections",
        )
    
    # Check if recipient exists
    recipient = db.query(User).filter(User.id == recipient_id).first()
    if not recipient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    # Check for existing connection in either direction
    existing = (
        db.query(Connection)
        .filter(
            or_(
                and_(
                    Connection.requester_id == current_user.id,
                    Connection.recipient_id == recipient_id,
                ),
                and_(
                    Connection.requester_id == recipient_id,
                    Connection.recipient_id == current_user.id,
                ),
            )
        )
        .first()
    )
    
    if existing:
        if existing.status == "pending":
            # If they sent us a request, auto-accept it
            if existing.requester_id == recipient_id:
                existing.status = "accepted"
                db.commit()
                return {"detail": "Connection accepted (mutual request)", "connection_id": existing.id}
            else:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Connection request already sent",
                )
        elif existing.status == "accepted":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Already connected",
            )
    
    # Create new connection request
    new_connection = Connection(
        requester_id=current_user.id,
        recipient_id=recipient_id,
        status="pending",
    )
    db.add(new_connection)
    db.commit()
    db.refresh(new_connection)
    
    return {"detail": "Connection request sent", "connection_id": new_connection.id}


@router.get("/requests/incoming", response_model=list[ConnectionWithUser])
def get_incoming_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all pending connection requests sent to me"""
    
    requests = (
        db.query(Connection)
        .filter(
            Connection.recipient_id == current_user.id,
            Connection.status == "pending",
        )
        .all()
    )
    
    result = []
    for req in requests:
        requester = db.query(User).filter(User.id == req.requester_id).first()
        result.append(
            ConnectionWithUser(
                id=req.id,
                status=req.status,
                created_at=req.created_at,
                other_user_id=requester.id,
                other_user_username=requester.username,
                other_user_email=requester.email,
            )
        )
    
    return result


@router.get("/requests/outgoing", response_model=list[ConnectionWithUser])
def get_outgoing_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all pending connection requests I sent"""
    
    requests = (
        db.query(Connection)
        .filter(
            Connection.requester_id == current_user.id,
            Connection.status == "pending",
        )
        .all()
    )
    
    result = []
    for req in requests:
        recipient = db.query(User).filter(User.id == req.recipient_id).first()
        result.append(
            ConnectionWithUser(
                id=req.id,
                status=req.status,
                created_at=req.created_at,
                other_user_id=recipient.id,
                other_user_username=recipient.username,
                other_user_email=recipient.email,
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
    
    # Must be the recipient to accept
    if connection.recipient_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only accept requests sent to you",
        )
    
    if connection.status == "accepted":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Connection already accepted",
        )
    
    connection.status = "accepted"
    db.commit()
    
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
    
    # Must be either the requester or recipient
    if connection.requester_id != current_user.id and connection.recipient_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized",
        )
    
    db.delete(connection)
    db.commit()
    
    return {"detail": "Connection request rejected"}


@router.get("", response_model=list[ConnectionWithUser])
def get_connections(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all accepted connections"""
    
    connections = (
        db.query(Connection)
        .filter(
            or_(
                Connection.requester_id == current_user.id,
                Connection.recipient_id == current_user.id,
            ),
            Connection.status == "accepted",
        )
        .all()
    )
    
    result = []
    for conn in connections:
        # Determine the other user
        if conn.requester_id == current_user.id:
            other_user_id = conn.recipient_id
        else:
            other_user_id = conn.requester_id
        
        other_user = db.query(User).filter(User.id == other_user_id).first()
        
        result.append(
            ConnectionWithUser(
                id=conn.id,
                status=conn.status,
                created_at=conn.created_at,
                other_user_id=other_user.id,
                other_user_username=other_user.username,
                other_user_email=other_user.email,
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
    if connection.requester_id != current_user.id and connection.recipient_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized",
        )
    
    db.delete(connection)
    db.commit()
    
    return {"detail": "Disconnected successfully"}
