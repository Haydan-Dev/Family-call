from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional
from app.db import get_database
from app.core.security import get_current_user_token

router = APIRouter(
    prefix="/api/settings",
    tags=["Settings"]
)

db = get_database()

class ProfileUpdateRequest(BaseModel):
    name: Optional[str] = None
    is_2fa_enabled: Optional[bool] = None

@router.get("/")
async def get_settings(user_id: str = Depends(get_current_user_token)):
    user = await db.users.find_one({"_id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    return {
        "name": user.get("name", user.get("full_name", "")),
        "email": user.get("email"),
        "is_2fa_enabled": user.get("is_2fa_enabled", False),
        "profile_pic_url": user.get("profile_pic_url")
    }

@router.patch("/")
async def update_settings(data: ProfileUpdateRequest, user_id: str = Depends(get_current_user_token)):
    user = await db.users.find_one({"_id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    update_data = {}
    if data.name is not None:
        update_data["name"] = data.name
        # Keep full_name in sync for compatibility
        update_data["full_name"] = data.name
        
    if data.is_2fa_enabled is not None:
        update_data["is_2fa_enabled"] = data.is_2fa_enabled
        
    if update_data:
        await db.users.update_one(
            {"_id": user_id},
            {"$set": update_data}
        )
        
    return {"message": "Settings updated successfully"}
