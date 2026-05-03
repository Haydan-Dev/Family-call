import datetime as dt
from bson import ObjectId
from app.models.message import Message

async def create_message_db(db, conversation_id: str, sender_id: str, message_data: Message) -> bool:
    """
    Validates room and inserts a new message.
    Returns True on success, False if validation fails.
    """
    chat_id = ObjectId(conversation_id)
    search_result = await db.conversations.find_one({"_id": chat_id, "participant_ids": sender_id})
    if not search_result:
        return False
        
    insert_result = await db.messages.insert_one(message_data.model_dump())
    if insert_result.inserted_id:
        await db.conversations.update_one(
            {"_id": chat_id},
            {"$set": {
                "last_message": message_data.content,
                "last_message_at": message_data.created_at
            }}
        )
        return True
    return False

async def get_history_db(db, conversation_id: str, sender_id: str) -> list | None:
    """
    Fetches chat history for the specified room.
    Returns a list of messages, or None if room invalid.
    """
    chat_id = ObjectId(conversation_id)
    search_result = await db.conversations.find_one({"_id": chat_id, "participant_ids": sender_id})
    if not search_result:
        return None
        
    chat_history = await db.messages.find({"conversation_id": str(chat_id), "is_deleted": False}).sort("created_at", 1).to_list(length=75)
    for msg in chat_history:
        msg["_id"] = str(msg["_id"])
    return chat_history

async def delete_message_db(db, message_id: str, sender_id: str) -> list | None:
    """
    Marks a message as deleted.
    Returns participant_ids if modified, None otherwise.
    """
    msg_id = ObjectId(message_id)
    message = await db.messages.find_one({"sender_id": sender_id, "_id": msg_id})
    if not message:
        return None
        
    update_result = await db.messages.update_one(
        {"_id": msg_id},
        {"$set": {
            "updated_at": dt.datetime.now(dt.timezone.utc),
            "is_deleted": True,
            "content": "This Message Was Deleted"
        }}
    )
    
    room = await db.conversations.find_one({"_id": ObjectId(message["conversation_id"])})
    if room:
        return room.get("participant_ids", [])
    return []

async def edit_message_db(db, message_id: str, sender_id: str, new_content: str) -> list | None:
    """
    Edits a message's content.
    Returns participant_ids of the conversation if successful, None otherwise.
    """
    msg_id = ObjectId(message_id)
    message = await db.messages.find_one({"sender_id": sender_id, "_id": msg_id})
    if not message:
        return None
        
    await db.messages.update_one(
        {"_id": msg_id},
        {"$set": {
            "content": new_content,
            "is_edited": True,
            "updated_at": dt.datetime.now(dt.timezone.utc)
        }}
    )
    
    room = await db.conversations.find_one({"_id": ObjectId(message["conversation_id"])})
    if room:
        return room.get("participant_ids", [])
    return []

async def toggle_pin_db(db, message_id: str) -> dict | None:
    """
    Toggles is_pinned status of a message.
    Returns the message dict after toggle if successful, or None if message not found.
    """
    msg_id = ObjectId(message_id)
    message = await db.messages.find_one({"_id": msg_id})
    if not message:
        return None
        
    new_status = not message.get("is_pinned", False)
    update_result = await db.messages.update_one(
        {"_id": msg_id},
        {"$set": {"is_pinned": new_status, "updated_at": dt.datetime.now(dt.timezone.utc)}}
    )
    if update_result.modified_count == 1:
        message["is_pinned"] = new_status
        return message
    return None

async def forward_msg_db(db, message_id: str, target_room_id: str, user_id: str) -> bool:
    """
    Forwards a message to another room.
    Returns True if successfully forwarded, False otherwise.
    """
    msg_id = ObjectId(message_id)
    original_msg = await db.messages.find_one({"_id": msg_id})
    if not original_msg:
        return False
        
    target_chat_id = ObjectId(target_room_id)
    target_room = await db.conversations.find_one({"_id": target_chat_id, "participant_ids": user_id})
    if not target_room:
        return False
        
    new_msg_data = dict(original_msg)
    new_msg_data.pop("_id", None)
    new_msg_data["conversation_id"] = str(target_chat_id)
    new_msg_data["sender_id"] = user_id
    new_msg_data["is_forwarded"] = True
    new_msg_data["is_edited"] = False
    new_msg_data["is_pinned"] = False
    new_msg_data["created_at"] = dt.datetime.now(dt.timezone.utc)
    new_msg_data["updated_at"] = dt.datetime.now(dt.timezone.utc)
    new_msg_data["updated_at"] = dt.datetime.now(dt.timezone.utc)
    
    insert_result = await db.messages.insert_one(new_msg_data)
    if insert_result.inserted_id:
        await db.conversations.update_one(
            {"_id": target_chat_id},
            {"$set": {
                "last_message": new_msg_data.get("content", "Forwarded message"),
                "last_message_at": new_msg_data["created_at"]
            }}
        )
        return True
    return False

async def mark_messages_seen_db(db, conversation_id: str, user_id: str) -> tuple[list, list]:
    """
    Marks all unread messages in a conversation sent by others as 'seen'.
    Returns (participant_ids, list_of_updated_message_ids_as_strings)
    """
    chat_id = ObjectId(conversation_id)
    room = await db.conversations.find_one({"_id": chat_id})
    if not room or user_id not in room.get("participant_ids", []):
        return [], []

    cursor = db.messages.find({
        "conversation_id": str(chat_id),
        "sender_id": {"$ne": user_id},
        "status": {"$ne": "seen"}
    })
    messages = await cursor.to_list(length=100)
    
    if not messages:
        return room.get("participant_ids", []), []
        
    msg_ids = [msg["_id"] for msg in messages]
    str_msg_ids = [str(m_id) for m_id in msg_ids]
    
    await db.messages.update_many(
        {"_id": {"$in": msg_ids}},
        {"$set": {"status": "seen", "updated_at": dt.datetime.now(dt.timezone.utc)}}
    )
    
    return room.get("participant_ids", []), str_msg_ids
