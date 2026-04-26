from fastapi import APIRouter, UploadFile, File, HTTPException
from app.core.config import settings
from app.services.upload_services import save_upload_file

router = APIRouter(
    prefix="/media",
    tags=["Media Uploads"]
)

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        result = save_upload_file(file, settings.UPLOAD_DIR, settings.SERVER_URL)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload Failed: {str(e)}")