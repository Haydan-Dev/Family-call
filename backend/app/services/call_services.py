import datetime as dt
from bson import ObjectId
from app.models.call_logs import Call_logs

async def call_initialize_db(db, user_id: str, call_data: dict) -> str | None:
    new_call = Call_logs(caller_id=user_id, **call_data).model_dump()
    insert_result = await db.calls.insert_one(new_call)
    if insert_result:
        return str(insert_result.inserted_id)
    return None

async def call_status_update_db(db, user_id: str, call_id: str, new_status: str) -> bool:
    try:
        id = ObjectId(call_id)
    except:
        return False
        
    update_fields = {"call_status": new_status}
    if new_status == "ended":
        update_fields["disconnected_by"] = user_id
        
    update_result = await db.calls.update_one({"_id": id}, {"$set": update_fields})
    return update_result.modified_count > 0

async def call_history_db(db, user_id: str) -> list:
    search_result = db.calls.find({
        "$or": [{"caller_id": user_id}, {"receiver_id": user_id}]
    })
    call_list = await search_result.to_list(length=100)
    for call in call_list:
        call["_id"] = str(call["_id"])
    return call_list

async def delete_call_db(db, user_id: str, call_id: str) -> bool:
    try:
        id = ObjectId(call_id)
    except:
        return False
        
    update_result = await db.calls.update_one(
        {"_id": id},
        {"$addToSet": {"deleted_by": user_id}}
    )
    return update_result.matched_count > 0
