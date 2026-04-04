import uuid 
import datetime as dt
from pydantic import BaseModel,Field
from typing import Literal
class Call_logs(BaseModel):
    call_id :  str = Field(default_factory=lambda:str(uuid.uuid4()))
    caller_id : str 
    receiver_id : str 
    call_type : Literal["audio","video"]
    status : Literal["ringing", "ongoing", "missed", "rejected", "ended"] = "ringing"
    started_at : dt.datetime = Field(default_factory=lambda:dt.datetime.now(dt.timezone.utc))
    ended_at : dt.datetime | None = None
    duration : int | None = None
    disconnected_by: str |None = None

