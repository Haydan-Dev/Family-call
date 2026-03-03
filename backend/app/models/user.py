import uuid
import datetime as dt
from pydantic import BaseModel, Field
user = {
    "user_id" : str(uuid.uuid4()),
    "full_name" : "",
    "email" : "",
    "password_hash" : "",
    "profile_pic_url" : "",
    "role" : "",
    "is_online" : False,
    "last_seen_at" : dt.datetime.now(),
    "created_at" : dt.datetime.now(),
    "contacts" : [
    ],
    "fcm_tokens" : {},
    "is_deleted" : False,
    "deleted_at" : None 
}