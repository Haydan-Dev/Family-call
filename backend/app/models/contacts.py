import uuid
import datetime as dt
user_contact = {
    "id": uuid.uuid4(),
    "owner_id": uuid.uuid4(),
    "contact_user_id": uuid.uuid4(),
    "nickname" : "",
    "is_pinned" : False,
    "is_blocked" : False,
    "created_at" : dt.datetime.now(),
    "updated_at": dt.datetime.now(),
}