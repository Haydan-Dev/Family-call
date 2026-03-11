import uuid
import datetime as dt 
from pydantic import BaseModel,Field
from typing import Literal
class Message(BaseModel):
    id : str = Field(default_factory=lambda : str(uuid.uuid4()))
    chat_id : str 
    sender_id : str
    message_type : Literal["text", "image", "video", "audio", "doc", "location"]
    content : str       
    status : Literal["sent", "delivered", "seen"] = "sent"
    is_pinned : bool =False
    is_forwarded : bool = False
    reply_to_message_id : str | None = None
    is_edited : bool = False
    created_at : dt.datetime =  Field(default_factory=lambda: dt.datetime.now())
    updated_at : dt.datetime =  Field(default_factory=lambda: dt.datetime.now())