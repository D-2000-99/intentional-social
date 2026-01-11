from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.db import Base


class ReportedPost(Base):
    __tablename__ = "reported_posts"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False, index=True)
    reported_by_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    reason = Column(Text, nullable=True)  # Optional reason for the report
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Relationships
    post = relationship("Post", backref="reports")
    reported_by = relationship("User", foreign_keys=[reported_by_id], backref="reports_made")
    resolved_by = relationship("User", foreign_keys=[resolved_by_id], backref="reports_resolved")

