from bson import ObjectId
from bson.errors import InvalidId
import datetime as dt
from app.models.contacts import User_Contact

async def save_contact_db(db, user_id: str, contact_data: dict) -> str | None:
    if_contact_exist = await db.contacts.find_one({
        "owner_id": user_id, 
        "contact_email": contact_data.get("contact_email"), 
        "contact_nickname": contact_data.get("contact_nickname")
    })
    if if_contact_exist:
        return None
        
    new_contact_obj = User_Contact(owner_id=user_id, **contact_data)
    contact_info = new_contact_obj.model_dump() 
    save_result = await db.contacts.insert_one(contact_info)   
    return str(save_result.inserted_id) 

async def delete_contact_db(db, user_id: str, contact_id: str) -> bool:
    try:
        valid_object_id = ObjectId(contact_id)
    except InvalidId:
        return False
        
    delete_result = await db.contacts.delete_one({"_id": valid_object_id, "owner_id": user_id})
    return delete_result.deleted_count == 1

async def search_contact_db(db, user_id: str, contact_nickname: str) -> list:
    search_result = await db.contacts.find({
        "contact_nickname": {"$regex": contact_nickname, "$options": "i"},
        "owner_id": user_id
    }).to_list(length=100)
    
    for contact in search_result:
        contact["_id"] = str(contact["_id"])
    return search_result

async def get_all_contacts_db(db, user_id: str) -> list:
    cursor = db.contacts.find({"owner_id": user_id})
    contacts_list = []
    async for contact in cursor:
        contact["_id"] = str(contact["_id"])
        contacts_list.append(contact)
    return contacts_list


# ── Helper: resolve other participant's email from room_id ────────────────────
async def _get_contact_email_from_room(db, room_id: str, user_id: str) -> str | None:
    """Returns the other participant's email for a given conversation room_id."""
    try:
        room = await db.conversations.find_one({"_id": ObjectId(room_id)})
    except Exception:
        return None
    if not room or "participant_ids" not in room:
        return None

    participant_ids = room.get("participant_ids", [])
    
    # Identify the other person's ID (filter out the current user)
    other_user_id = next(
        (pid for pid in participant_ids if str(pid) != str(user_id)), None
    )
    
    if not other_user_id:
        # If it's a self-chat or room has only one participant
        return None

    try:
        other_user = await db.users.find_one({"_id": ObjectId(other_user_id)})
        return other_user.get("email") if other_user else None
    except Exception:
        return None


async def rename_contact_db(db, user_id: str, room_id: str, new_name: str) -> bool:
    """Update contact_nickname for the contact in this room. Creates contact if missing."""
    # 1. Resolve current user email for logging
    current_user = await db.users.find_one({"_id": ObjectId(user_id)})
    current_user_email = current_user.get("email") if current_user else "Unknown"

    # 2. Identify the other participant's email
    other_participant_email = await _get_contact_email_from_room(db, room_id, user_id)
    
    # 3. Logging as requested
    print(f"DEBUG: current_user_email={current_user_email}, room_id={room_id}, identified other_participant_email={other_participant_email}")

    if not other_participant_email:
        return False

    # 4. Update or Create (Upsert)
    # Even if the contact doesn't exist in the 'Contacts' collection yet, we create it.
    query = {"owner_id": user_id, "contact_email": other_participant_email}
    update_data = {
        "$set": {
            "contact_nickname": new_name,
            "updated_at": dt.datetime.now(dt.timezone.utc)
        },
        "$setOnInsert": {
            "owner_id": user_id,
            "contact_email": other_participant_email,
            "is_pinned": False,
            "is_blocked": False,
            "created_at": dt.datetime.now(dt.timezone.utc)
        }
    }
    
    result = await db.contacts.update_one(query, update_data, upsert=True)
    return result.modified_count > 0 or result.upserted_id is not None or result.matched_count > 0


async def block_contact_db(db, user_id: str, room_id: str) -> bool:
    """Set is_blocked=True on the contact in this room. Creates contact if missing."""
    email = await _get_contact_email_from_room(db, room_id, user_id)
    if not email:
        return False
    query = {"owner_id": user_id, "contact_email": email}
    update_data = {
        "$set": {
            "is_blocked": True,
            "updated_at": dt.datetime.now(dt.timezone.utc)
        },
        "$setOnInsert": {
            "owner_id": user_id,
            "contact_email": email,
            "contact_nickname": email.split('@')[0],
            "is_pinned": False,
            "created_at": dt.datetime.now(dt.timezone.utc)
        }
    }
    result = await db.contacts.update_one(query, update_data, upsert=True)
    return result.modified_count > 0 or result.upserted_id is not None or result.matched_count > 0


async def unblock_contact_db(db, user_id: str, room_id: str) -> bool:
    """Set is_blocked=False on the contact in this room. Creates contact if missing."""
    email = await _get_contact_email_from_room(db, room_id, user_id)
    if not email:
        return False
    query = {"owner_id": user_id, "contact_email": email}
    update_data = {
        "$set": {
            "is_blocked": False,
            "updated_at": dt.datetime.now(dt.timezone.utc)
        },
        "$setOnInsert": {
            "owner_id": user_id,
            "contact_email": email,
            "contact_nickname": email.split('@')[0],
            "is_pinned": False,
            "created_at": dt.datetime.now(dt.timezone.utc)
        }
    }
    result = await db.contacts.update_one(query, update_data, upsert=True)
    return result.modified_count > 0 or result.upserted_id is not None or result.matched_count > 0


async def get_blocked_contacts_db(db, user_id: str) -> list:
    """Return all contacts where is_blocked=True."""
    cursor = db.contacts.find({"owner_id": user_id, "is_blocked": True})
    results = []
    async for contact in cursor:
        contact["_id"] = str(contact["_id"])
        results.append(contact)
    return results
