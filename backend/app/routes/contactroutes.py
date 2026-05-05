from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.db import get_database
from app.models.contacts import Contact_save
from app.core.security import get_current_user_token
from app.services.contact_services import (
    save_contact_db,
    delete_contact_db,
    search_contact_db,
    get_all_contacts_db,
    rename_contact_db,
    block_contact_db,
    unblock_contact_db,
    get_blocked_contacts_db,
)

router = APIRouter(
    prefix="/contacts",
    tags=["Contacts"]
)

db = get_database()

# ── Request schemas ───────────────────────────────────────────────────────────
class RenameRequest(BaseModel):
    name: str


# ── Existing routes ───────────────────────────────────────────────────────────
@router.post("/save")
async def save_contact(contact_data: Contact_save, user_id: str = Depends(get_current_user_token)):
    save_contact_id = await save_contact_db(db, user_id, contact_data.model_dump())
    if not save_contact_id:
        raise HTTPException(status_code=409, detail="Contact Already Exist")
    return {
        "Message": "Contact save Successfully",
        "data": save_contact_id
    }

@router.delete("/delete/{contact_id}")
async def delete_contact(contact_id: str, user_id: str = Depends(get_current_user_token)):
    success = await delete_contact_db(db, user_id, contact_id)
    if success:
        return {"Message": "Contact Deleted Successfully", "_id": contact_id, "user_id": user_id}
    else:
        raise HTTPException(status_code=404, detail="Contact Not Found or Invalid ID format")

@router.get("/search_contact/{contact_nickname}")
async def search_contact(contact_nickname: str, user_id: str = Depends(get_current_user_token)):
    search_result = await search_contact_db(db, user_id, contact_nickname)
    if search_result:
        return {"number": len(search_result), "Message": "Contact Found", "contacts": search_result}
    else:
        return {"number": 0, "Message": "Contact Not Found", "contacts": []}

@router.get("/")
async def get_all_contacts(user_id: str = Depends(get_current_user_token)):
    contacts_list = await get_all_contacts_db(db, user_id)
    return contacts_list


# ── New routes ────────────────────────────────────────────────────────────────
@router.patch("/rename/{room_id}")
async def rename_contact(room_id: str, body: RenameRequest, user_id: str = Depends(get_current_user_token)):
    """Update the display name (contact_nickname) for a contact by room_id."""
    success = await rename_contact_db(db, user_id, room_id, body.name.strip())
    if not success:
        raise HTTPException(status_code=404, detail="Contact not found for this room")
    return {"status": 200, "message": "Contact renamed successfully"}


@router.post("/block/{room_id}")
async def block_contact(room_id: str, user_id: str = Depends(get_current_user_token)):
    """Block the contact associated with this room."""
    success = await block_contact_db(db, user_id, room_id)
    if not success:
        raise HTTPException(status_code=404, detail="Contact not found for this room")
    return {"status": 200, "message": "Contact blocked"}


@router.post("/unblock/{room_id}")
async def unblock_contact(room_id: str, user_id: str = Depends(get_current_user_token)):
    """Unblock the contact associated with this room."""
    success = await unblock_contact_db(db, user_id, room_id)
    if not success:
        raise HTTPException(status_code=404, detail="Contact not found for this room")
    return {"status": 200, "message": "Contact unblocked"}


@router.get("/blocked")
async def get_blocked_contacts(user_id: str = Depends(get_current_user_token)):
    """Return all contacts this user has blocked."""
    blocked = await get_blocked_contacts_db(db, user_id)
    return {"data": blocked, "count": len(blocked)}


@router.post("/unblock_by_id/{contact_id}")
async def unblock_by_contact_id(contact_id: str, user_id: str = Depends(get_current_user_token)):
    """Unblock a contact by its MongoDB _id (used by blocked_users.html page)."""
    try:
        from bson import ObjectId
        result = await db.contacts.update_one(
            {"_id": ObjectId(contact_id), "owner_id": user_id},
            {"$set": {"is_blocked": False}}
        )
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid contact ID")
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Contact not found")
    return {"status": 200, "message": "Contact unblocked"}