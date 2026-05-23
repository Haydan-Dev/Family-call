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
import asyncio
from firebase_admin import messaging
import logging
import datetime

logger = logging.getLogger(__name__)

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
        # receiver_id is the participant who is NOT the current user
        receiver_id = next((str(pid) for pid in participant_ids if str(pid) != str(user_id)), None)
        
        if not receiver_id:
            raise HTTPException(status_code=404, detail="Receiver not found in room")
            
        db_call_data = {
            "receiver_id": receiver_id,
            "room_id": call_data.room_id,
            "call_type": call_data.call_type
        }
        
        call_id = await call_initialize_db(db, user_id, db_call_data)
        
        if call_id:
            # ── PHASE 4: VOIP DATA PAYLOAD FIREBASE TRIGGER ──
            receiver = await db.users.find_one({"_id": receiver_id})
            caller = await db.users.find_one({"_id": user_id})
            caller_name = (caller.get("full_name") if caller else None) or "Family"
            
            if receiver:
                fcm_token = (receiver.get("fcm_tokens") or {}).get("android")
                if fcm_token:
                    call_type_label = (call_data.call_type or "video").capitalize()
                    
                    def send_voip_push():
                        try:
                            # 🎯 DATA-ONLY payload — ensures onMessageReceived fires
                            # in ALL states (foreground, background, KILLED).
                            # MyFirebaseMessagingService.java builds the notification natively.
                            message = messaging.Message(
                                data={
                                    "event": "incoming_call",
                                    "call_id": str(call_id),
                                    "call_type": call_data.call_type,
                                    "caller_id": str(user_id),
                                    "caller_name": caller_name,
                                    "room_id": str(call_data.room_id)
                                },
                                android=messaging.AndroidConfig(
                                    priority="high",
                                    ttl=datetime.timedelta(seconds=45)
                                ),
                                token=fcm_token
                            )
                            messaging.send(message)
                            logger.info(f"📞 VoIP push sent to {receiver_id}")
                        except Exception as e:
                            logger.error(f"FCM VoIP Error [{receiver_id}]: {str(e)}")
                    
                    # Fire and forget — non-blocking
                    asyncio.create_task(asyncio.to_thread(send_voip_push))
            # ─────────────────────────────────────────────────
            
            return {"status": 200, "Message": "Call is started and Noted in DB Successfully", "call_id": call_id} 
        else:
            raise HTTPException(status_code=500, detail="Database insertion failed.")
    except Exception as e:
        logger.error(f"Error in call_initialize: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/status_update/{call_id}")
async def call_status_update(call_id: str, call_update: Call_Status_Update, user_id: str = Depends(get_current_user_token)):
    success = await call_status_update_db(db, user_id, call_id, call_update.call_status)
    if not success:
        raise HTTPException(status_code=404, detail="Call not found or already updated")
        
    # Broadcast via websocket to the OTHER participant if connected
    from app.websockets.connection_manager import manager
    from bson import ObjectId
    try:
        call_doc = await db.calls.find_one({"_id": ObjectId(call_id)})
        if call_doc:
            room_id = call_doc.get("room_id")
            caller_id = str(call_doc.get("caller_id"))
            receiver_id = str(call_doc.get("receiver_id"))
            
            # The person who IS NOT the current user gets the message
            target_id = caller_id if user_id == receiver_id else receiver_id
            
            event_name = None
            if call_update.call_status == "rejected":
                event_name = "call_declined"
            elif call_update.call_status == "ended":
                event_name = "call_ended"
            elif call_update.call_status == "ongoing":
                event_name = "call_accepted"
                
            if event_name and target_id:
                logger.info(f"Broadcasting {event_name} to {target_id} via WS from HTTP fallback")
                await manager.send_personal_message({"event": event_name, "room_id": str(room_id), "call_id": call_id}, target_id)
    except Exception as e:
        logger.error(f"Error broadcasting status update WS: {e}")
        
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