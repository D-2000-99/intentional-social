from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship

from app.db import Base


class PostAudienceTag(Base):
    __tablename__ = "post_audience_tags"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)
    tag_id = Column(Integer, ForeignKey("tags.id"), nullable=False)

    # Relationships
    post = relationship("Post", backref="audience_tags")
    tag = relationship("Tag", backref="post_audiences")
