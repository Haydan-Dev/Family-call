from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from app.websockets.connection_manager import manager
from app.services.message_services import create_message_db
from app.db import get_database
from jose import jwt, JWTError
from app.core.config import settings
import json
from bson import ObjectId
from app.models.message import Message
import datetime
from pydantic import BaseModel
from fastapi import BackgroundTasks

class NativeDeclineRequest(BaseModel):
    room_id: str
    call_id: str

router = APIRouter(
    prefix="/ws",
    tags=["WebSockets"]
)

db = get_database()

async def get_ws_user_id(token: str):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        return user_id
    except JWTError:
        return None

@router.post("/decline")
async def native_decline_call(req: NativeDeclineRequest):
    """
    Called by Android Native Code (killed state UI) to instantly terminate a caller's ring.
    """
    try:
        room_obj_id = ObjectId(req.room_id)
        room = await db.conversations.find_one({"_id": room_obj_id})
        if room:
            # We want to send call_declined to everyone in the room to stop their ringing
            for participant_id in room.get("participant_ids", []):
                await manager.send_personal_message({
                    "event": "call_declined",
                    "room_id": req.room_id,
                    "call_id": req.call_id
                }, str(participant_id))
        return {"status": "declined"}
    except Exception as e:
        import logging
        logging.error(f"Native Decline Error: {e}")
        return {"status": "error", "message": str(e)}

@router.websocket("/global")
async def global_websocket_endpoint(websocket: WebSocket, token: str = Query(...)):
    user_id = await get_ws_user_id(token)
    if not user_id:
        await websocket.close(code=1008)
        return

    await manager.connect(websocket, user_id)

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)

@router.websocket("/chat/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str, token: str = Query(...)):
    user_id = await get_ws_user_id(token)
    if not user_id:
        await websocket.close(code=1008)
        return

    try:
        room_obj_id = ObjectId(room_id)
    except:
        await websocket.close(code=1003)
        return
        
    room = await db.conversations.find_one({"_id": room_obj_id, "participant_ids": user_id})
    if not room:
        await websocket.close(code=1008)
        return

    await manager.connect(websocket, user_id)

    participant_ids = room.get("participant_ids", [])
    recipient_id = next((pid for pid in participant_ids if pid != user_id), None)
    if not recipient_id and participant_ids:
        recipient_id = user_id

    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg_dict = json.loads(data)
                
                # ── STRICT SIGNALING GATEWAY ──
                if msg_dict.get("event") in ("incoming_call", "call_accepted", "call_rejected", "call_cancelled", "call_declined", "call_ended"):
                    if recipient_id and recipient_id != user_id:
                        is_online = recipient_id in manager.active_connections
                        is_in_room = False
                        
                        if is_online:
                            recipient_ws = manager.active_connections.get(recipient_id)
                            if recipient_ws and hasattr(recipient_ws, 'url'):
                                if f"/ws/chat/{room_id}" in str(recipient_ws.url):
                                    is_in_room = True
                                    
                            await manager.send_personal_message(msg_dict, recipient_id)
                        
                        event_name = msg_dict.get("event")
                        # If recipient is offline or on a different page, send FCM VoIP push
                        if not is_in_room:
                            import logging
                            logger = logging.getLogger(__name__)
                            try:
                                receiver = await db.users.find_one({"_id": recipient_id})
                                if not receiver:
                                    try:
                                        receiver = await db.users.find_one({"_id": ObjectId(recipient_id)})
                                    except: pass
                                if receiver:
                                    fcm_token = (receiver.get("fcm_tokens") or {}).get("android")
                                    if fcm_token:
                                        from firebase_admin import messaging
                                        import asyncio
                                        
                                        def send_call_push():
                                            try:
                                                message = messaging.Message(
                                                    data={
                                                        "event": event_name,
                                                        "room_id": str(room_id),
                                                        "call_id": str(msg_dict.get("call_id", "")),
                                                        "caller_name": str(msg_dict.get("caller_name", "Family Member")),
                                                        "call_type": str(msg_dict.get("call_type", "voice"))
                                                    },
                                                    android=messaging.AndroidConfig(
                                                        priority="high",
                                                        ttl=datetime.timedelta(seconds=0)
                                                    ),
                                                    token=fcm_token
                                                )
                                                messaging.send(message)
                                                logger.info(f"📞 VoIP Push ({event_name}) sent to {recipient_id}")
                                            except Exception as e:
                                                logger.error(f"FCM Call Push Error: {str(e)}")
                                        asyncio.create_task(asyncio.to_thread(send_call_push))
                            except Exception as e:
                                logger.error(f"WebSocket Call Push Error: {str(e)}")
                    continue

                full_message = Message(
                    conversation_id=room_id,
                    sender_id=user_id,
                    message_type=msg_dict.get("message_type", "text"),
                    content=msg_dict.get("content", "")
                )
            except Exception:
                continue
                
            message_id = await create_message_db(db, room_id, user_id, full_message)
            
            if message_id:
                sender_name = "Unknown"
                try:
                    sender_user = await db.users.find_one({"_id": user_id})
                    if not sender_user:
                        try:
                            sender_user = await db.users.find_one({"_id": ObjectId(user_id)})
                        except: pass
                    if sender_user:
                        sender_name = sender_user.get("full_name", "Unknown")
                except Exception:
                    pass

                # Send confirmation to sender
                await manager.send_personal_message({
                    "event": "new_message_sent", 
                    "message_id": message_id,
                    "room_id": room_id,
                    "content": full_message.content,
                    "sender_id": user_id,
                    "sender_name": sender_name,
                    "message_type": full_message.message_type
                }, user_id)
                
                # Notify recipient
                if recipient_id and recipient_id != user_id:
                    is_online = recipient_id in manager.active_connections
                    await manager.send_personal_message({
                        "event": "new_message", 
                        "message_id": message_id,
                        "room_id": room_id,
                        "content": full_message.content,
                        "sender_id": user_id,
                        "sender_name": sender_name,
                        "message_type": full_message.message_type
                    }, recipient_id)
                    
                    # If recipient is offline, send FCM push notification!
                    if not is_online:
                        import logging
                        logger = logging.getLogger(__name__)
                        try:
                            receiver = await db.users.find_one({"_id": recipient_id})
                            if not receiver:
                                try:
                                    receiver = await db.users.find_one({"_id": ObjectId(recipient_id)})
                                except: pass
                            
                            if receiver:
                                fcm_token = (receiver.get("fcm_tokens") or {}).get("android")
                                if fcm_token:
                                    from firebase_admin import messaging
                                    import asyncio
                                    
                                    # Truncate long messages for notification preview
                                    preview = (full_message.content[:80] + "...") if len(full_message.content) > 80 else full_message.content
                                    
                                    def send_msg_push():
                                        try:
                                            message = messaging.Message(
                                                data={
                                                    "event": "new_message",
                                                    "conversation_id": str(room_id),
                                                    "sender_name": sender_name,
                                                    "message_body": preview,
                                                    "room_id": str(room_id)
                                                },
                                                android=messaging.AndroidConfig(
                                                    priority="high",
                                                    ttl=datetime.timedelta(seconds=45)
                                                ),
                                                token=fcm_token
                                            )
                                            messaging.send(message)
                                            logger.info(f"📩 WebSocket offline message push sent to {recipient_id}")
                                        except Exception as e:
                                            logger.error(f"FCM WS Message Error: {str(e)}")
                                            
                                    asyncio.create_task(asyncio.to_thread(send_msg_push))
                        except Exception as e:
                            logger.error(f"WebSocket Push Notification Error: {str(e)}")
                
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)

@router.websocket("/call/{room_id}/{client_id}")
async def call_websocket_endpoint(websocket: WebSocket, room_id: str, client_id: str):
    await manager.connect(websocket, client_id)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg_dict = json.loads(data)
                
                # Check if room_id is valid ObjectId
                if ObjectId.is_valid(room_id):
                    room_obj_id = ObjectId(room_id)
                    room = await db.conversations.find_one({"_id": room_obj_id})
                    if room:
                        participant_ids = room.get("participant_ids", [])
                        recipient_id = next((str(pid) for pid in participant_ids if str(pid) != str(client_id)), None)
                        if recipient_id:
                            await manager.send_personal_message(msg_dict, recipient_id)
                            
                            # 🚨 Dispatch background FCM push for termination events (cancellations/declines/ends)
                            event_name = msg_dict.get("event")
                            if event_name in ("call_cancelled", "call_declined", "call_ended", "call_rejected"):
                                import logging
                                logger = logging.getLogger(__name__)
                                try:
                                    receiver = await db.users.find_one({"_id": recipient_id})
                                    if not receiver:
                                        try:
                                            receiver = await db.users.find_one({"_id": ObjectId(recipient_id)})
                                        except: pass
                                    if receiver:
                                        fcm_token = (receiver.get("fcm_tokens") or {}).get("android")
                                        if fcm_token:
                                            from firebase_admin import messaging
                                            import asyncio
                                            
                                            def send_cancel_push():
                                                try:
                                                    message = messaging.Message(
                                                        data={
                                                            "event": event_name,
                                                            "room_id": str(room_id),
                                                            "call_id": str(msg_dict.get("call_id", ""))
                                                        },
                                                        android=messaging.AndroidConfig(
                                                            priority="high",
                                                            ttl=datetime.timedelta(seconds=0)
                                                        ),
                                                        token=fcm_token
                                                    )
                                                    messaging.send(message)
                                                    logger.info(f"📞 FCM Call Termination push ({event_name}) sent to {recipient_id}")
                                                except Exception as e:
                                                    logger.error(f"FCM Call Termination Push Error: {str(e)}")
                                            asyncio.create_task(asyncio.to_thread(send_cancel_push))
                                except Exception as e:
                                    logger.error(f"Failed to dispatch FCM call cancellation push in call websocket: {str(e)}")
                        continue
                
                # Fallback: If DB routing fails or room is a demo string, broadcast to all OTHER connected users
                for other_user_id in list(manager.active_connections.keys()):
                    if str(other_user_id) != str(client_id):
                        await manager.send_personal_message(msg_dict, other_user_id)
                        
            except Exception as e:
                import logging
                logging.error(f"WebSocket routing error: {e}")
                continue
    except WebSocketDisconnect:
        manager.disconnect(websocket, client_id)