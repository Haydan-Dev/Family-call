from fastapi import APIRouter, Depends, HTTPException
from app.db import get_database
from app.core.security import get_current_user_token
from bson import ObjectId
from app.models.message import First_Message, Edit_Message, ForwardRequest, Message
from app.services.message_services import (
    create_message_db,
    get_history_db,
    delete_message_db,
    edit_message_db,
    toggle_pin_db,
    forward_msg_db
)

router = APIRouter(
    prefix="/messages",
    tags=["Messages"]
)

db = get_database()

# POST: Send a new message to an existing conversation
@router.post("/send/{conversation_id}")
async def send_messages(conversation_id: str, message_data: First_Message, user_id: str = Depends(get_current_user_token)):
    full_message = Message(
        conversation_id=conversation_id,
        sender_id=user_id,
        message_type=message_data.message_type,
        content=message_data.content
    )
    success = await create_message_db(db, conversation_id, user_id, full_message)
    if success:
        return {"status": 200, "message": "Message sent successfully"}
    else:
        raise HTTPException(status_code=404, detail="Conversation not found, access denied, or insertion failed")

# GET: Fetch message history for a specific room
@router.get("/history/{conversation_id}")
async def messages_history(conversation_id: str, user_id: str = Depends(get_current_user_token)):
    from app.services.message_services import mark_messages_seen_db
    from app.websockets.connection_manager import manager
    
    participants, updated_ids = await mark_messages_seen_db(db, conversation_id, user_id)
    if updated_ids:
        payload = {
            "event": "STATUS_UPDATE",
            "message_ids": updated_ids,
            "room_id": str(conversation_id),
            "new_status": "seen"
        }
        for pid in participants:
            await manager.send_personal_message(payload, pid)

    chat_history = await get_history_db(db, conversation_id, user_id)
    if chat_history is not None:
        return {"status": 200, "Message": "Chat History Found", "Chat": chat_history}
    else:
        raise HTTPException(status_code=404, detail="Conversation ID Not Found")

# DELETE: Remove a specific message document
@router.delete("/delete/{message_id}")  
async def delete_messages(message_id: str, user_id: str = Depends(get_current_user_token)):
    participant_ids = await delete_message_db(db, message_id, user_id)
    if participant_ids is not None:
        payload = {
            "event": "MESSAGE_DELETED",
            "message_id": message_id
        }
        for pid in participant_ids:
            await manager.send_personal_message(payload, pid)
            
        return {"status": 200, "Message": "Message Deleted Successfully"}
    else:
        raise HTTPException(status_code=404, detail="Message Not Found or Unauthorized")

from app.websockets.connection_manager import manager

# PATCH: Edit message content and set is_edited flag
@router.patch("/edit/{message_id}")
async def edit_messages(edit_message: Edit_Message, message_id: str, user_id: str = Depends(get_current_user_token)):
    participant_ids = await edit_message_db(db, message_id, user_id, edit_message.content)
    if participant_ids is not None:
        payload = {
            "event": "MESSAGE_EDITED",
            "message_id": message_id,
            "new_content": edit_message.content
        }
        for pid in participant_ids:
            await manager.send_personal_message(payload, pid)
            
        return {"status": 200, "Message": "Message Edited Successfully"}
    else:
        raise HTTPException(status_code=404, detail="Message Not Found or Unauthorized")

# PATCH: Pin/Unpin message
@router.patch("/pin/{message_id}")
async def pin_message(message_id: str, user_id: str = Depends(get_current_user_token)):
    result = await toggle_pin_db(db, message_id)
    if result is not None:
        return {"status": 200, "Message": "Message Pinned/Unpinned successfully"}
    else:
        raise HTTPException(status_code=404, detail="Message Not Found")

# POST: Forward a message
@router.post("/forward/{message_id}")
async def forward_message(message_id: str, forward_req: ForwardRequest, user_id: str = Depends(get_current_user_token)):
    success = await forward_msg_db(db, message_id, forward_req.target_room_id, user_id)
    if success:
        return {"status": 200, "Message": "Message Forwarded Successfully"}
    else:
        raise HTTPException(status_code=404, detail="Original Message or Target Conversation Not Found/Denied")

# PUT: Mark messages in a conversation as seen
@router.put("/{conversation_id}/seen")
async def mark_messages_as_seen(conversation_id: str, current_user_id: str = Depends(get_current_user_token)):
    filter_query = {
        "conversation_id": str(conversation_id),
        "sender_id": {"$ne": str(current_user_id)},
        "status": {"$ne": "seen"}
    }
    
    cursor = db.messages.find(filter_query)
    messages = await cursor.to_list(length=None)
    
    if messages:
        msg_ids = [m["_id"] for m in messages]
        str_msg_ids = [str(m_id) for m_id in msg_ids]
        
        update_operation = {"$set": {"status": "seen"}}
        result = await db.messages.update_many({"_id": {"$in": msg_ids}}, update_operation)
        
        senders = set(str(m["sender_id"]) for m in messages)
        from app.websockets.connection_manager import manager
        
        for sender in senders:
            await manager.send_personal_message({
                "event": "STATUS_UPDATE",
                "room_id": str(conversation_id),
                "message_ids": str_msg_ids,
                "new_status": "seen"
            }, sender)
            
        await manager.send_personal_message({
            "event": "STATUS_UPDATE",
            "room_id": str(conversation_id),
            "message_ids": str_msg_ids,
            "new_status": "seen"
        }, current_user_id)
        
        return {"status": 200, "Message": "Messages marked as seen", "modified_count": result.modified_count}
    
    return {"status": 200, "Message": "No messages to mark as seen", "modified_count": 0}

# PUT: Mark all pending incoming messages as delivered
@router.put("/mark_delivered")
async def mark_messages_delivered(user_id: str = Depends(get_current_user_token)):
    from app.websockets.connection_manager import manager
    
    # 1. Find all rooms for this user
    user_rooms = await db.conversations.find({"participant_ids": str(user_id)}).to_list(length=None)
    room_ids_str = [str(r["_id"]) for r in user_rooms]
    
    if not room_ids_str:
        return {"status": 200, "Message": "No rooms found"}
        
    # 2. Find all "sent" messages directed to this user using String IDs to match schema
    cursor = db.messages.find({
        "conversation_id": {"$in": room_ids_str},
        "sender_id": {"$ne": str(user_id)},
        "status": "sent"
    })
    messages = await cursor.to_list(length=None)
    
    if messages:
        msg_ids = [m["_id"] for m in messages]
        str_msg_ids = [str(m_id) for m_id in msg_ids]
        
        # 3. Mark as delivered
        await db.messages.update_many(
            {"_id": {"$in": msg_ids}},
            {"$set": {"status": "delivered"}}
        )
        
        # 4. Notify senders via WebSocket
        senders = set(str(m["sender_id"]) for m in messages)
        for sender in senders:
            sender_msgs = [m for m in messages if str(m["sender_id"]) == sender]
            rooms_for_sender = set(str(m["conversation_id"]) for m in sender_msgs)
            for r_id in rooms_for_sender:
                r_msg_ids = [str(m["_id"]) for m in sender_msgs if str(m["conversation_id"]) == r_id]
                await manager.send_personal_message({
                    "event": "STATUS_UPDATE",
                    "room_id": r_id,
                    "message_ids": r_msg_ids,
                    "new_status": "delivered"
                }, sender)
                
                await manager.send_personal_message({
                    "event": "STATUS_UPDATE",
                    "room_id": r_id,
                    "message_ids": r_msg_ids,
                    "new_status": "delivered"
                }, user_id)
            
    return {"status": 200, "Message": "Messages marked as delivered"}