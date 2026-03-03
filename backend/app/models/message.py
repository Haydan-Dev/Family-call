import uuid
import datetime as dt 
message = {
    "id" : uuid.uuid4(),
    "chat_id" : uuid.uuid4(),
    "sender_id" : uuid.uuid4(),
    "content" : "",
    "message" : "text",
    "status" : "sent",
    "is_pinned" : False,
    "is_forwarded" : False,
    "reply_to_message_id" : None,
    "is_edited" : False,
    "created_at" : dt.datetime.now(),
    "updated_at" : dt.datetime.now(),
}