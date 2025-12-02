from sqlalchemy import Column, Integer, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime

from app.db import Base


class ConnectionTag(Base):
    __tablename__ = "connection_tags"

    id = Column(Integer, primary_key=True, index=True)
    connection_id = Column(Integer, ForeignKey("connections.id"), nullable=False)
    tag_id = Column(Integer, ForeignKey("tags.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    connection = relationship("Connection", backref="connection_tags")
    tag = relationship("Tag", backref="connection_tags")

    # Constraints
    __table_args__ = (
        UniqueConstraint('connection_id', 'tag_id', name='unique_connection_tag'),
    )
