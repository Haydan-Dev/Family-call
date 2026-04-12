from fastapi import APIRouter
from app.db import get_database
router = APIRouter(
    prefix="/messages",
    tags=["Messages"]
)

db = get_database()
# messages ko bheejne ke liye 
@router.post("/send_messages/{conversation_id}")
async def send_messages(conversation_id:str):
    pass


# messages ko dekhne ke liye
@router.get("/see_messages")
async def see_messages():
    pass
# messages ko delete karne ke liye
@router.delete("/delete_messages")
async def delete_messages():
    pass
# messages ko update karne ke liye
@router.patch("/update_messages")
async def update_messages():
    pass