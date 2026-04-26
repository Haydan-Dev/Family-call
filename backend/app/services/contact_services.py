from bson import ObjectId
from bson.errors import InvalidId
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
