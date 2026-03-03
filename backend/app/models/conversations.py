import uuid 
import datetime as dt
conversation = {
    "chat_id" : uuid.uuid4(),
    "is_group": False,
    "group_name" : None,
    "group_icon" : None,
    "created_by" : uuid.uuid4(),
    "participant_ids":[
        uuid.uuid4(),
        uuid.uuid4(),
        uuid.uuid4(),
    ],
    "last_message" : "",
    "last_message_at" : dt.datetime.now(),
    "created_at" : dt.datetime.now()
}