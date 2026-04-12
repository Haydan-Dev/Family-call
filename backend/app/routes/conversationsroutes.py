from fastapi import APIRouter
from app.core.security import get_current_user_token
from fastapi import Depends
from app.models.contacts import User_Contact
from fastapi import HTTPException
from bson import ObjectId
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
    
# conversation search karne ki api hai , abhi delete karne ke bhi banegi
# API: User ke saare existing chat rooms dhoondhne ke liye (For Home Screen)
@router.get("/display_conversations")
async def search_conversation(user_id: str = Depends(get_current_user_token)):
    # STEP 1: Database se cursor nikala (Bina 'await' ke) jo user ki IDs match kare
    find_conversations = db.conversations.find({"participant_ids": user_id})
    # STEP 2: Ek khali balti (list) banayi data store karne ke liye
    existing_conversations = []
    # STEP 3: Async loop lagaya taaki cursor se ek-ek karke chat room nikal sake
    async for conversation in find_conversations:
        # CRITICAL FIX: MongoDB ke ajeeb 'ObjectId' ko normal String mein badla (To prevent 500 Error)
        conversation["_id"] = str(conversation["_id"])
        # Room ko balti mein daal diya
        existing_conversations.append(conversation)
    # Loop ke bahar check karte hain ki list khali hai ya nahi
    if len(existing_conversations) == 0:
        return {"conversation": [], "Message": "Conversation not found"}
    else:
        return {"conversation": existing_conversations, "Message": "Conversation found"}


# User ke saare existing chat rooms delete ke liye (For Home Screen)
# API: /conversations/delete_conversation/{room_id}
# Method: DELETE
@router.delete("/conversations/delete_conversations/{room_id}")
# STEP 1: IDENTITY CHECK
# - Token se 'user_id' (Haydan) nikalo.
# - URL se 'room_id' (Wo chat jo udani hai) pakdo.
async def delete_conversations(room_id:str,user_id: str = Depends(get_current_user_token)):
# STEP 2: DATABASE SURGERY 🗡️
# - MongoDB ko bolo: "db.conversations collection mein jao."
# - Ek nishana (Query) lagao jahan:
#     1. "_id" match kare frontend wale 'room_id' se.
#     2. "participant_ids" ki list ke andar 'user_id' (Haydan) maujood ho.
# - Isko 'delete_one' command ke sath chala do.
    room_id = ObjectId(room_id)
    delete_result = await db.conversations.delete_one({"_id":room_id,"participant_ids":user_id})
# STEP 3: RESULT AUDIT 📊
# - MongoDB ek 'result' wapas dega.
# - Usme check karo 'deleted_count' kitna hai.""
# STEP 4: FINAL RESPONSE 📢
# - IF deleted_count == 1:
#     Return "Status: Success, Message: Room deleted permanently" (Code 200)
# - ELSE (Agar count 0 hai):
#     Return "Status: Error, Message: Invalid Room or Access Denied" (Code 404)
    if delete_result.deleted_count == 1:
        return {"status":200,"Message":"Conversation Deleted Successfully"}
    else:
        raise HTTPException(status_code=404,detail="Conversation Not Found")