from fastapi import APIRouter, Depends, HTTPException
from app.db import get_database
from app.core.security import get_current_user_token
from app.models.call_logs import CallStartRequest as callrequest
from app.models.call_logs import Call_Status_Update
from app.services.call_services import (
    call_initialize_db,
    call_status_update_db,
    call_history_db,
    delete_call_db
)

router = APIRouter(
    prefix="/calls",
    tags=["Calls"]
)

db = get_database()

@router.post("/start")
async def call_initialize(call_data: callrequest, user_id: str = Depends(get_current_user_token)):
    from bson import ObjectId
    
    # Resolve receiver_id from room_id
    try:
        room = await db.conversations.find_one({"_id": ObjectId(call_data.room_id)})
        if not room:
            raise HTTPException(status_code=404, detail="Room not found")
            
        participant_ids = room.get("participant_ids", [])
        receiver_id = next((str(pid) for pid in participant_ids if str(pid) != str(user_id)), None)
        
        if not receiver_id:
            raise HTTPException(status_code=404, detail="Receiver not found in room")
            
        db_call_data = {
            "receiver_id": receiver_id,
            "call_type": call_data.call_type
        }
        
        call_id = await call_initialize_db(db, user_id, db_call_data)
        if call_id:
            return {"status": 200, "Message": "Call is started and Noted in DB Successfully", "call_id": call_id} 
        else:
            raise HTTPException(status_code=500, detail="Database insertion failed.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/status_update/{call_id}")
async def call_status_update(call_id: str, call_update: Call_Status_Update, user_id: str = Depends(get_current_user_token)):
    success = await call_status_update_db(db, user_id, call_id, call_update.call_status)
    if not success:
        raise HTTPException(status_code=404, detail="Call not found or already updated")
    return {"status": 200, "message": f"Call status updated to {call_update.call_status}"}

@router.get("/history")
async def call_history(user_id: str = Depends(get_current_user_token)):
    call_list = await call_history_db(db, user_id)
    return {"status": 200, "data": call_list}

@router.delete("/delete/{call_id}")
async def delete_call(call_id: str, user_id: str = Depends(get_current_user_token)):
    success = await delete_call_db(db, user_id, call_id)
    if not success:
        raise HTTPException(status_code=404, detail="Call log not found")
    return {"status": 200, "message": "Call log removed from your history"}
