from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_, func
from pydantic import BaseModel
from typing import List
import logging

from app.core.deps import get_db, get_current_user
from app.config import settings
from app.models.user import User
from app.models.connection import Connection, ConnectionStatus
from app.models.tag import Tag
from app.models.connection_tag import ConnectionTag
from app.schemas.connection import ConnectionOut, ConnectionWithUser

router = APIRouter(prefix="/connections", tags=["Connections"])
logger = logging.getLogger(__name__)


# Define schemas for insights endpoint
class TagDistributionItem(BaseModel):
    tag_id: int
    tag_name: str
    color_scheme: str
    count: int
    percentage: float

    class Config:
        from_attributes = True


class ConnectionInsights(BaseModel):
    current_connections: int
    max_connections: int
    connection_percentage: float
    tag_distribution: List[TagDistributionItem]


# Define insights endpoint FIRST to avoid route conflicts with /{connection_id}/tags
# Using /stats instead of /insights to avoid conflicts with parameterized routes
@router.get("/stats", response_model=ConnectionInsights)
def get_connection_insights(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get connection insights for the current user only (connection count and tag distribution)"""
    
    # Get accepted connections count
    accepted_count = (
        db.query(Connection)
        .filter(
            or_(
                Connection.requester_id == current_user.id,
                Connection.recipient_id == current_user.id,
            ),
            Connection.status == ConnectionStatus.ACCEPTED,
        )
        .count()
    )
    
    max_connections = settings.MAX_CONNECTIONS
    connection_percentage = (accepted_count / max_connections * 100) if max_connections > 0 else 0
    
    # Get tag distribution - count how many connections have each tag
    # Only count tags that belong to the current user
    tag_distribution_query = (
        db.query(
            Tag.id,
            Tag.name,
            Tag.color_scheme,
            func.count(ConnectionTag.connection_id).label('count')
        )
        .join(ConnectionTag, Tag.id == ConnectionTag.tag_id)
        .join(Connection, ConnectionTag.connection_id == Connection.id)
        .filter(
            Tag.user_id == current_user.id,  # Only user's own tags
            or_(
                Connection.requester_id == current_user.id,
                Connection.recipient_id == current_user.id,
            ),
            Connection.status == ConnectionStatus.ACCEPTED,
        )
        .group_by(Tag.id, Tag.name, Tag.color_scheme)
        .all()
    )
    
    # Calculate percentages
    tag_distribution = []
    for tag_id, tag_name, color_scheme, count in tag_distribution_query:
        percentage = (count / accepted_count * 100) if accepted_count > 0 else 0
        tag_distribution.append(
            TagDistributionItem(
                tag_id=tag_id,
                tag_name=tag_name,
                color_scheme=color_scheme,
                count=count,
                percentage=round(percentage, 1)
            )
        )
    
    # Sort by count descending
    tag_distribution.sort(key=lambda x: x.count, reverse=True)
    
    return ConnectionInsights(
        current_connections=accepted_count,
        max_connections=max_connections,
        connection_percentage=round(connection_percentage, 1),
        tag_distribution=tag_distribution
    )


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
        if existing.status == ConnectionStatus.PENDING:
            # If they sent us a request, auto-accept it
            if existing.requester_id == recipient_id:
                existing.status = ConnectionStatus.ACCEPTED
                db.commit()
                logger.info(
                    f"Mutual connection auto-accepted between users {current_user.id} and {recipient_id}"
                )
                return {"detail": "Connection accepted (mutual request)", "connection_id": existing.id}
            else:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Connection request already sent",
                )
        elif existing.status == ConnectionStatus.ACCEPTED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Already connected",
            )
    
    # Create new connection request
    new_connection = Connection(
        requester_id=current_user.id,
        recipient_id=recipient_id,
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
    
    # Use joinedload to avoid N+1 queries (loads users in single query)
    requests = (
        db.query(Connection)
        .options(joinedload(Connection.requester))
        .filter(
            Connection.recipient_id == current_user.id,
            Connection.status == ConnectionStatus.PENDING,
        )
        .all()
    )
    
    return [
        ConnectionWithUser(
            id=req.id,
            status=req.status.value,  # Convert enum to string for response
            created_at=req.created_at,
            other_user_id=req.requester.id,
            other_user_username=req.requester.username,
        )
        for req in requests
    ]


@router.get("/requests/outgoing", response_model=list[ConnectionWithUser])
def get_outgoing_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all pending connection requests I sent."""
    
    # Use joinedload to avoid N+1 queries
    requests = (
        db.query(Connection)
        .options(joinedload(Connection.recipient))
        .filter(
            Connection.requester_id == current_user.id,
            Connection.status == ConnectionStatus.PENDING,
        )
        .all()
    )
    
    return [
        ConnectionWithUser(
            id=req.id,
            status=req.status.value,
            created_at=req.created_at,
            other_user_id=req.recipient.id,
            other_user_username=req.recipient.username,
        )
        for req in requests
    ]


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
                Connection.requester_id == current_user.id,
                Connection.recipient_id == current_user.id,
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
    
    logger.info(
        f"User {current_user.id} accepted connection request {connection_id} from user {connection.requester_id}"
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
    
    # Must be either the requester or recipient
    if connection.requester_id != current_user.id and connection.recipient_id != current_user.id:
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
    
    # Use joinedload for both requester and recipient to avoid N+1 queries
    connections = (
        db.query(Connection)
        .options(joinedload(Connection.requester), joinedload(Connection.recipient))
        .filter(
            or_(
                Connection.requester_id == current_user.id,
                Connection.recipient_id == current_user.id,
            ),
            Connection.status == ConnectionStatus.ACCEPTED,
        )
        .all()
    )
    
    result = []
    for conn in connections:
        # Determine the other user (already loaded via joinedload)
        other_user = conn.recipient if conn.requester_id == current_user.id else conn.requester
        
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
    if connection.requester_id != current_user.id and connection.recipient_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized",
        )
    
    db.delete(connection)
    db.commit()
    
    return {"detail": "Disconnected successfully"}
