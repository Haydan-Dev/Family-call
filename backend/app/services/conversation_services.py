from bson import ObjectId

async def create_conversation_db(db, user_id: str, contact_id: str) -> dict | None:
    try:
        contact_obj_id = ObjectId(contact_id)
    except:
        return None
        
    participant_list = await db.contacts.find_one({"_id": contact_obj_id})
    if not participant_list:
        return {"error": "Invalid Contact ID", "code": 401}
        
    email = participant_list.get("contact_email")
    user_data = await db.users.find_one({"email": email})
    if not user_data:
        return {"error": "receiver ID Not Found", "code": 404}
        
    receiver_id = str(user_data["_id"])
    caller_id = user_id
    
    check_participation_list = await db.conversations.find_one({
        "participant_ids": {"$all": [caller_id, receiver_id], "$size": 2}
    })
    
    if check_participation_list:
        return {"room_id": str(check_participation_list["_id"]), "is_new": False}
        
    new_room = await db.conversations.insert_one({"participant_ids": [caller_id, receiver_id]}) 
    return {"room_id": str(new_room.inserted_id), "is_new": True}

async def search_conversation_db(db, user_id: str) -> list:
    find_conversations = db.conversations.find({"participant_ids": user_id})
    formatted_list = []
    
    async for conversation in find_conversations:
        participant_ids = conversation.get("participant_ids", [])
        other_user_id = next((pid for pid in participant_ids if pid != user_id), None)
        
        if not other_user_id and participant_ids:
            other_user_id = user_id
            
        contact_name = "Unknown User"
        
        if other_user_id:
            try:
                other_user = await db.users.find_one({"_id": ObjectId(other_user_id)})
                if other_user:
                    other_email = other_user.get("email")
                    saved_contact = None
                    if other_email:
                        saved_contact = await db.contacts.find_one({"owner_id": user_id, "contact_email": other_email})
                    
                    if saved_contact and saved_contact.get("contact_nickname"):
                        contact_name = saved_contact.get("contact_nickname")
                    else:
                        if other_email:
                            contact_name = other_email.split('@')[0]
                        else:
                            contact_name = other_user.get("name") or "Unknown User"
            except Exception:
                pass
                
        is_pinned = user_id in conversation.get("pinned_by", [])
        is_archived = user_id in conversation.get("archived_by", [])
                
        formatted_list.append({
            "room_id": str(conversation["_id"]),
            "contact_name": contact_name,
            "last_message": str(conversation.get("last_message", "No messages yet")),
            "is_pinned": is_pinned,
            "is_archived": is_archived
        })
        
    return formatted_list

async def toggle_pin_room_db(db, user_id: str, room_id: str) -> dict | None:
    try:
        room_obj_id = ObjectId(room_id)
    except:
        return None
        
    room = await db.conversations.find_one({"_id": room_obj_id, "participant_ids": user_id})
    if not room:
        return None
        
    pinned_by = room.get("pinned_by", [])
    if user_id in pinned_by:
        await db.conversations.update_one(
            {"_id": room_obj_id},
            {"$pull": {"pinned_by": user_id}}
        )
        return {"is_pinned": False}
    else:
        await db.conversations.update_one(
            {"_id": room_obj_id},
            {"$addToSet": {"pinned_by": user_id}}
        )
        return {"is_pinned": True}

async def archive_room_db(db, user_id: str, room_id: str) -> dict | None:
    try:
        room_obj_id = ObjectId(room_id)
    except:
        return None
        
    room = await db.conversations.find_one({"_id": room_obj_id, "participant_ids": user_id})
    if not room:
        return None
        
    archived_by = room.get("archived_by", [])
    if user_id in archived_by:
        await db.conversations.update_one(
            {"_id": room_obj_id},
            {"$pull": {"archived_by": user_id}}
        )
        return {"is_archived": False}
    else:
        await db.conversations.update_one(
            {"_id": room_obj_id},
            {"$addToSet": {"archived_by": user_id}}
        )
        return {"is_archived": True}

async def delete_conversations_db(db, user_id: str, room_id: str) -> bool:
    try:
        room_obj_id = ObjectId(room_id)
    except:
        return False
        
    room = await db.conversations.find_one({"_id": room_obj_id, "participant_ids": user_id})
    if not room:
        return False
        
    await db.conversations.update_one(
        {"_id": room_obj_id},
        {"$pull": {"participant_ids": user_id}}
    )
    
    updated_room = await db.conversations.find_one({"_id": room_obj_id})
    if updated_room and not updated_room.get("participant_ids"):
        await db.conversations.delete_one({"_id": room_obj_id})
        await db.messages.delete_many({"conversation_id": room_id})
        
    return True
