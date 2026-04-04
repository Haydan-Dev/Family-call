import uuid 
import datetime as dt
from pydantic import BaseModel,Field
class Conversation(BaseModel):
    chat_id : str = Field(default_factory=lambda:str(uuid.uuid4()))
    is_group : bool = False
    group_name : str | None = None
    group_icon : str | None = None
    created_by : str | None = None
    participant_ids: list[str] = Field(default_factory=list)
    last_message: str | None = None
    last_message_at : dt.datetime | None = None
    created_at : dt.datetime = Field(default_factory=lambda:dt.datetime.now(dt.timezone.utc)) 
