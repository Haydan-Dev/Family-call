from fastapi import APIRouter, HTTPException, Depends
from app.core.config import settings
from app.utils.zego_token import generate_token04

router = APIRouter(prefix="/zego", tags=["ZegoCloud"])

@router.get("/generate_token")
async def generate_zego_token(user_id: str, room_id: str):
    try:
        app_id = int(settings.ZEGO_APP_ID)
        server_secret = settings.ZEGO_SERVER_SECRET
        effective_time = 3600
        
        # Token04 signature: app_id, user_id, secret, effective_time_in_seconds, payload
        token_info = generate_token04(
            app_id,
            user_id,
            server_secret,
            effective_time,
            ""
        )
        if token_info.error_code != 0:
            raise HTTPException(status_code=400, detail=f"Zego Token Error: {token_info.error_message}")
            
        return {"token": token_info.token, "app_id": app_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
