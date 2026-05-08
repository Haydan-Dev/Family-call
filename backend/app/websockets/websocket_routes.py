from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from app.websockets.connection_manager import manager
from app.services.message_services import create_message_db
from app.db import get_database
from jose import jwt, JWTError
from app.core.config import settings
import json
from bson import ObjectId
from app.models.message import Message

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
                        await manager.send_personal_message(msg_dict, recipient_id)
                    continue

                full_message = Message(
                    conversation_id=room_id,
                    sender_id=user_id,
                    message_type=msg_dict.get("message_type", "text"),
                    content=msg_dict.get("content", "")
                )
            except Exception:
                continue
                
            success = await create_message_db(db, room_id, user_id, full_message)
            
            if success:
                sender_name = "Unknown"
                try:
                    sender_user = await db.users.find_one({"_id": ObjectId(user_id)})
                    if sender_user:
                        sender_name = sender_user.get("full_name", "Unknown")
                except Exception:
                    pass

                # Send confirmation to sender
                await manager.send_personal_message({
                    "event": "new_message_sent", 
                    "room_id": room_id,
                    "content": full_message.content,
                    "sender_id": user_id,
                    "sender_name": sender_name,
                    "message_type": full_message.message_type
                }, user_id)
                
                # Notify recipient
                if recipient_id and recipient_id != user_id:
                    await manager.send_personal_message({
                        "event": "new_message", 
                        "room_id": room_id,
                        "content": full_message.content,
                        "sender_id": user_id,
                        "sender_name": sender_name,
                        "message_type": full_message.message_type
                    }, recipient_id)
                
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
                room_obj_id = ObjectId(room_id)
                room = await db.conversations.find_one({"_id": room_obj_id})
                if room:
                    participant_ids = room.get("participant_ids", [])
                    recipient_id = next((pid for pid in participant_ids if pid != client_id), None)
                    if recipient_id:
                        await manager.send_personal_message(msg_dict, recipient_id)
            except Exception:
                continue
    except WebSocketDisconnect:
        try:
            manager.disconnect(client_id)
        except TypeError:
            manager.disconnect(websocket, client_id)