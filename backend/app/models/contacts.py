import uuid
import datetime as dt
from pydantic import BaseModel,Field
class User_Contact(BaseModel):
    owner_id : str 
    contact_user_id : str 
    nickname : str | None = None
    is_pinned : bool = False
    is_blocked : bool = False
    created_at : dt.datetime = Field(default_factory=lambda:dt.datetime.now(dt.timezone.utc))
    updated_at: dt.datetime = Field(default_factory=lambda:dt.datetime.now(dt.timezone.utc))
