from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, func, and_
from pydantic import BaseModel
from typing import List

from app.core.deps import get_db, get_current_user
from app.config import settings
from app.models.user import User
from app.models.connection import Connection, ConnectionStatus
from app.models.tag import Tag
from app.models.user_tag import UserTag

router = APIRouter(prefix="/insights", tags=["Insights"])


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


@router.get("/connections", response_model=ConnectionInsights)
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
                Connection.user_a_id == current_user.id,
                Connection.user_b_id == current_user.id,
            ),
            Connection.status == ConnectionStatus.ACCEPTED,
        )
        .count()
    )
    
    max_connections = settings.MAX_CONNECTIONS
    connection_percentage = (accepted_count / max_connections * 100) if max_connections > 0 else 0
    
    # Get tag distribution - count how many connected users have each tag (where current user is the owner)
    # Only count tags that belong to the current user
    # First, get list of connected user IDs
    connections = (
        db.query(Connection)
        .filter(
            or_(
                Connection.user_a_id == current_user.id,
                Connection.user_b_id == current_user.id,
            ),
            Connection.status == ConnectionStatus.ACCEPTED,
        )
        .all()
    )
    
    connected_user_ids = []
    for conn in connections:
        if conn.user_a_id == current_user.id:
            connected_user_ids.append(conn.user_b_id)
        else:
            connected_user_ids.append(conn.user_a_id)
    
    if not connected_user_ids:
        # No connections, return empty tag distribution
        tag_distribution = []
    else:
        tag_distribution_query = (
            db.query(
                Tag.id,
                Tag.name,
                Tag.color_scheme,
                func.count(UserTag.target_user_id).label('count')
            )
            .join(UserTag, Tag.id == UserTag.tag_id)
            .filter(
                Tag.owner_user_id == current_user.id,  # Only user's own tags
                UserTag.owner_user_id == current_user.id,  # Only tags applied by current user
                UserTag.target_user_id.in_(connected_user_ids)
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
