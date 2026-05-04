from fastapi import APIRouter, Depends, HTTPException
from app.core.security import get_current_user_token
from app.db import get_database
from app.services.conversation_services import (
    create_conversation_db,
    search_conversation_db,
    delete_conversations_db,
    toggle_pin_room_db,
    archive_room_db
)

db = get_database()

router = APIRouter(
    prefix="/conversations",
    tags=["Conversation"]
)

@router.post("/start_conversation/{contact_id}")
async def create_conversation(contact_id: str, user_id: str = Depends(get_current_user_token)):
    result = await create_conversation_db(db, user_id, contact_id)
    
    if not result:
        raise HTTPException(status_code=400, detail="Invalid request")
        
    if "error" in result:
        raise HTTPException(status_code=result.get("code", 400), detail=result["error"])
        
    if result.get("is_new"):
        return {"Status": "New Room Created Sucessfully", "new_room_id": result["room_id"]}
    else:
        return {"status": "success", "room_id": result["room_id"]}

@router.get("/display_conversations")
async def search_conversation(user_id: str = Depends(get_current_user_token)):
    formatted_list, total_archived = await search_conversation_db(db, user_id, fetch_archived=False)
    return {"data": formatted_list, "total_archived_unread": total_archived, "Message": "Conversations found"}

@router.get("/archived_conversations")
async def get_archived_conversations(user_id: str = Depends(get_current_user_token)):
    formatted_list, _ = await search_conversation_db(db, user_id, fetch_archived=True)
    return {"data": formatted_list, "Message": "Archived Conversations found"}

@router.patch("/pin/{room_id}")
async def pin_room(room_id: str, user_id: str = Depends(get_current_user_token)):
    result = await toggle_pin_room_db(db, user_id, room_id)
    if result is not None:
        return {"status": 200, "Message": "Room pin status updated", "is_pinned": result["is_pinned"]}
    else:
        raise HTTPException(status_code=404, detail="Room Not Found or Access Denied")

@router.patch("/archive/{room_id}")
async def archive_room(room_id: str, user_id: str = Depends(get_current_user_token)):
    result = await archive_room_db(db, user_id, room_id)
    if result is not None:
        return {"status": 200, "Message": "Room archive status updated", "is_archived": result["is_archived"]}
    else:
        raise HTTPException(status_code=404, detail="Room Not Found or Access Denied")

@router.delete("/delete_conversations/{room_id}")
async def delete_conversations(room_id: str, user_id: str = Depends(get_current_user_token)):
    success = await delete_conversations_db(db, user_id, room_id)
    if success:
        return {"status": 200, "Message": "Conversation Deleted Successfully"}
    else:
        raise HTTPException(status_code=404, detail="Conversation Not Found")

@router.get("/unread_counts")
async def get_unread_counts(current_user_id: str = Depends(get_current_user_token)):
    pipeline = [
        {
            "$match": {
                "sender_id": {"$ne": current_user_id},
                "status": {"$ne": "seen"}
            }
        },
        {
            "$group": {
                "_id": "$conversation_id",
                "unread_count": {"$sum": 1}
            }
        }
    ]
    cursor = db.messages.aggregate(pipeline)
    unread_counts = await cursor.to_list(length=None)
    return {"data": unread_counts, "Message": "Unread counts fetched successfully"}