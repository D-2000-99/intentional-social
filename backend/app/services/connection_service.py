"""Connection service for centralized connection business logic."""
from typing import List, Set
from sqlalchemy.orm import Session
from sqlalchemy import case, or_
from app.models.connection import Connection, ConnectionStatus
from app.models.user import User


class ConnectionService:
    """Centralized connection business logic."""
    
    @staticmethod
    def get_connected_user_ids(
        current_user: User,
        db: Session,
        include_self: bool = True
    ) -> List[int]:
        """
        Get IDs of all users connected to current user.
        Uses SQL CASE for efficiency instead of Python loops.
        """
        connected_ids = (
            db.query(
                case(
                    (Connection.user_a_id == current_user.id, Connection.user_b_id),
                    else_=Connection.user_a_id
                )
            )
            .filter(
                or_(
                    Connection.user_a_id == current_user.id,
                    Connection.user_b_id == current_user.id
                ),
                Connection.status == ConnectionStatus.ACCEPTED
            )
            .all()
        )
        
        result = [uid[0] for uid in connected_ids]
        
        if include_self:
            result.append(current_user.id)
        
        return result
    
    @staticmethod
    def are_connected(
        user1_id: int,
        user2_id: int,
        db: Session
    ) -> bool:
        """Check if two users are connected."""
        user_a_id = min(user1_id, user2_id)
        user_b_id = max(user1_id, user2_id)
        
        connection = (
            db.query(Connection)
            .filter(
                Connection.user_a_id == user_a_id,
                Connection.user_b_id == user_b_id,
                Connection.status == ConnectionStatus.ACCEPTED
            )
            .first()
        )
        
        return connection is not None
    
    @staticmethod
    def build_connection_graph(
        current_user: User,
        db: Session
    ) -> Set[tuple]:
        """
        Build a set of all connection pairs for fast lookup.
        Returns: {(user_a_id, user_b_id), ...}
        """
        connections = (
            db.query(Connection.user_a_id, Connection.user_b_id)
            .filter(
                or_(
                    Connection.user_a_id == current_user.id,
                    Connection.user_b_id == current_user.id
                ),
                Connection.status == ConnectionStatus.ACCEPTED
            )
            .all()
        )
        
        return {(min(a, b), max(a, b)) for a, b in connections}
