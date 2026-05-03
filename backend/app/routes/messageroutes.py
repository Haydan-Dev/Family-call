from fastapi import APIRouter, Depends, HTTPException
from app.db import get_database
from app.core.security import get_current_user_token
from app.models.message import First_Message, Edit_Message, ForwardRequest
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
    success = await create_message_db(db, conversation_id, user_id, message_data.model_dump())
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
            "action": "MESSAGE_SEEN",
            "message_ids": updated_ids,
            "user_id": user_id
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
            "action": "MESSAGE_DELETED",
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
            "action": "MESSAGE_EDITED",
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