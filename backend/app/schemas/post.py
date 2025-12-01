from datetime import datetime
from pydantic import BaseModel

class PostCreate(BaseModel):
    content: str

class PostOut(BaseModel):
    id: int
    author_id: int
    content: str
    created_at: datetime

    class Config:
        from_attributes = True
