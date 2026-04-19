from fastapi import APIRouter
from app.db import get_database
from app.core.security import get_current_user_token
from fastapi import Depends
from app.models.call_logs import CallStartRequest as callrequest
from app.models.call_logs import Call_logs 
from fastapi import HTTPException
from bson import ObjectId
from app.models.call_logs import Call_Status_Update
import datetime as dt
router = APIRouter(
    prefix="/calls",
    tags=["Calls"]
)

db = get_database()


# call ko start karne ki info ko db may daalne ki api hai, abhi call status ringing par hai 
@router.post("/start")
async def call_initialize(call_data:callrequest,user_id:str = Depends(get_current_user_token)):
    caller_id = user_id
    # receiver_id = call_data.receiver_id
    # call_type = call_data.call_type
    new_call = Call_logs(caller_id=caller_id,**call_data.model_dump()).model_dump()
    insert_result = await db.calls.insert_one(new_call)
    if insert_result:
        return{"status":200,"Message":"Call is started and Noted in DB Successfully","call_id": str(insert_result.inserted_id)} 
    else:
        raise HTTPException(status_code=500, detail="Database insertion failed. Call log could not be created.")
    


# call ka status ringing ne badal kar ongoing,missed,rejected,ended karne ki info ko db may daalne ki api hai
@router.patch("/status_update/{call_id}")
async def call_status_update(call_id: str, call_update: Call_Status_Update, user_id: str = Depends(get_current_user_token)):
    # 1. MongoDB ObjectId setup
    id = ObjectId(call_id)
    # 2. Jo update karna hai uska dabba banao
    new_status = call_update.call_status
    update_fields = {"call_status": new_status}
    # 3. Agar call cut gayi, toh time save karo
    if new_status == "ended":
        update_fields: dict = {"call_status": new_status}
        update_fields["disconnected_by"] = user_id
    # 4. Asli Alpha Query (No kachra syntax)
    update_result = await db.calls.update_one({"_id": id}, {"$set": update_fields})
    if update_result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Call not found or already updated")
    return {"status": 200, "message": f"Call status updated to {new_status}"}

# saare calls ki history user ko dikhane ki api hai
@router.get("/history")
async def call_history(user_id: str = Depends(get_current_user_token)):
    # 1. Database se list uthao jahan Haydan ne call kiya YA uthaya
    search_result = db.calls.find({"$or": [{"caller_id": user_id},{"receiver_id": user_id}]})
    # 2. Cursor ko Python ki list mein convert karo (max 100 calls)
    call_list = await search_result.to_list(length=100)
    # 3. MongoDB ki ObjectId ko string mein badalna padta hai frontend ke liye
    for call in call_list:
        call["_id"] = str(call["_id"])
    return {"status": 200, "data": call_list}

# user ko agar call ki history delete karni hoo to uss ki api hai 
@router.delete("/delete/{call_id}")
async def delete_call(call_id:str,user_id: str = Depends(get_current_user_token)):
    id = ObjectId(call_id)
    # 2. Logic: User ki ID ko deleted_by array mein "Push" karo
    # $addToSet best hai kyunki ye duplicate entry nahi hone deta
    update_result = await db.calls.update_one({"_id": id},{"$addToSet": {"deleted_by": user_id}})
    if update_result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Call log not found")
    return {"status": 200, "message": "Call log removed from your history"}
