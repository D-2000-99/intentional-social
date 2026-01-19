from app.db import Base  # re-export for Alembic convenience

# Import all models for Alembic
from app.models.user import User
from app.models.connection import Connection
from app.models.post import Post
from app.models.tag import Tag
from app.models.user_tag import UserTag
from app.models.post_audience_tag import PostAudienceTag
from app.models.comment import Comment
from app.models.reported_post import ReportedPost
# MVP TEMPORARY: Registration request model - remove when moving beyond MVP
from app.models.registration_request import RegistrationRequest

