from fastapi import APIRouter
from app.db import get_database
from fastapi import Depends
from app.core.security import get_current_user_token
from bson import ObjectId
from app.models.message import First_Message, Message ,Edit_Message
from fastapi import HTTPException 

router = APIRouter(
    prefix="/messages",
    tags=["Messages"]
)
db = get_database()

# POST: Send a new message to an existing conversation
@router.post("/send/{conversation_id}")
async def send_messages(conversation_id: str, message_data: First_Message, user_id: str = Depends(get_current_user_token)):
    sender_id = user_id 
    chat_id = ObjectId(conversation_id)
    # Extract frontend DTO to a raw dictionary
    message = message_data.model_dump()
    # Inject context variables (URL params & Token auth)
    message["conversation_id"] = str(chat_id)
    message["sender_id"] = sender_id
    # Auth Check: Ensure room exists and user is an active participant
    search_result = await db.conversations.find_one({"_id": chat_id, "participant_ids": sender_id})
    if search_result:
        # Unpack raw dict into main Pydantic model (Auto-injects timestamps & status)
        final_message = Message(**message) 
        # Serialize and execute DB insertion
        insert_result = await db.messages.insert_one(final_message.model_dump())
        if insert_result:
            return {"status": 200, "message": "Message sent successfully"}
        else:
            raise HTTPException(status_code=400, detail="Database insertion failed")
    else:
        raise HTTPException(status_code=404, detail="Conversation not found or access denied")

# GET: Fetch message history for a specific room
@router.get("/history/{conversation_id}")
async def messages_history(conversation_id: str,user_id:str = Depends(get_current_user_token)):
    chat_id = ObjectId(conversation_id) 
    sender_id = user_id
    search_result = await db.conversations.find_one({"_id":chat_id,"participant_ids":sender_id})
    if search_result:
        chat_history = await db.messages.find({"conversation_id":str(chat_id)}).sort("created_at",1).to_list(length=75)
        return{"status":200,"Message":"Chat History Found","Chat":chat_history}
    else:
        raise HTTPException(status_code=404,detail="Conversation ID Not Found")


# DELETE: Remove a specific message document
@router.delete("/delete/{message_id}")  
async def delete_messages(message_id: str,user_id:str = Depends(get_current_user_token)):
    sender_id = user_id
    messages_id = ObjectId(message_id) 
    update_result = await db.messages.update_one({"sender_id":sender_id,"_id":messages_id},{"$set":{"message_type":"text","content":"This Message Was Deleted"}})
    if update_result.modified_count == 1:
        return {"status":200,"Message":"Message Deleted Successfully"}
    else:
        raise HTTPException(status_code=404,detail="Message Not Found or Unauthorized")

# PATCH: Edit message content and set is_edited flag
@router.patch("/edit/{message_id}")
async def edit_messages(edit_message:Edit_Message,message_id:str,user_id:str=Depends(get_current_user_token)):
    sender_id = user_id
    msg_id = ObjectId(message_id)
    edit_result = await db.messages.update_one({"sender_id":sender_id,"_id":msg_id},{"$set":{"message_type":edit_message.message_type,"content":edit_message.content,"is_edited":True}})
    if edit_result.modified_count ==1:
        return {"status":200,"Message":"Message Edited Successfully"}