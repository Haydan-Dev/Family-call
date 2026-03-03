import uuid 
import datetime as dt
call_logs= {
    "call_id" :  uuid.uuid4(),
    "caller_id" : uuid.uuid4(),
    "receiver_id" : uuid.uuid4(),
    "call_type" : "audio",
    "status" : "calling",
    "started_at" : dt.datetime.now(),
    "ended_at" : None,
    "duration" : 0,
    "disconnected_by": None

}