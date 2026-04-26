from fastapi import APIRouter, Depends, HTTPException
from app.db import get_database
from app.models.contacts import Contact_save
from app.core.security import get_current_user_token
from app.services.contact_services import (
    save_contact_db,
    delete_contact_db,
    search_contact_db,
    get_all_contacts_db
)

router = APIRouter(
    prefix="/contacts",
    tags=["Contacts"]
)

db = get_database()

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