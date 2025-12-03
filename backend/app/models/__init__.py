from app.db import Base  # re-export for Alembic convenience

# Import all models for Alembic
from app.models.user import User
from app.models.connection import Connection
from app.models.post import Post
from app.models.tag import Tag
from app.models.connection_tag import ConnectionTag
from app.models.post_audience_tag import PostAudienceTag
from app.models.email_verification import EmailVerification
