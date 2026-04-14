import uuid 
import datetime as dt
from pydantic import BaseModel,Field
from typing import Literal
class Call_logs(BaseModel):
    caller_id : str 
    receiver_id : str 
    call_type : Literal["audio","video"]
    call_status : Literal["ringing", "ongoing", "missed", "rejected", "ended"] = "ringing"
    started_at : dt.datetime = Field(default_factory=lambda:dt.datetime.now(dt.timezone.utc))
    ended_at : dt.datetime | None = None
    duration : int | None = None
    disconnected_by: str |None = None
    deleted_by: list = []

# call start karne ke liye ek model 
class CallStartRequest(BaseModel):
    receiver_id: str
    call_type: Literal["audio", "video"]

# call status update karne ke liye ek model
class Call_Status_Update(BaseModel): 
    call_status: Literal["ringing", "ongoing", "missed", "rejected", "ended"] = "ringing"
    