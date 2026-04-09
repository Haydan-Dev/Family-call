from fastapi import APIRouter
from app.core.security import get_current_user_token
from fastapi import Depends
from app.models.contacts import User_Contact
from fastapi import HTTPException

from app.db import get_database
db = get_database()

router = APIRouter(
    prefix="/conversations",
    tags=["Conversation"]
)
# conversation create karne ki api hai abhi search and delete karne ke bhi banegi
@router.post("/start_conversation/{contact_id}") # james ki contact_id hai
async def create_conversation(contact_id:str,user_id: str = Depends(get_current_user_token)):
    email = ""
    nickname = "" # just in case aage jaake zarurat pade to 
    reciever_id = ""
    participant_list = await db.contacts.find_one({"_id":contact_id})
    if participant_list:
        email = participant_list["contact_email"]
        nickname = participant_list["contact_nickname"]  # just in case aage jaake zarurat pade to ?
        user_data = await db.user.find_one({"email":email})
        if user_data:
            reciever_id = str(user_data["_id"])
        else:
            raise HTTPException(status_code=404,detail="Reciever ID Not Found")
    else:
        raise HTTPException(status_code=401,detail="Invalid Contact ID")
    caller_id = user_id
    check_participation_list = await db.conversations.find_one({"participant_ids": {"$all": [caller_id, reciever_id], "$size": 2}})
    if check_participation_list:
        room_id = str(check_participation_list["_id"])
        return {"status": "success", "room_id": room_id}
    else:
        new_room = await db.conversations.insert_one({"participant_ids":[caller_id,reciever_id]}) 
        return {"Status": "New Room Created Sucessfully","new_room_id":str(new_room.inserted_id)}