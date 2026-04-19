from fastapi import APIRouter, UploadFile, File, HTTPException
import shutil
import os
import uuid # Unique naam banane ke liye taaki purani file overwrite na ho
from app.core.config import settings

router = APIRouter(
    prefix="/media",
    tags=["Media Uploads"]
)

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        # STEP 1: Upload folder ka rasta settings se uthaya
        upload_dir = settings.UPLOAD_DIR
        
        # STEP 2: Agar folder nahi bana hai, toh server khud bana dega (exist_ok=True se crash nahi hoga)
        os.makedirs(upload_dir, exist_ok=True)
        
        # STEP 3: File ka original extension nikalna (jaise .jpg, .mp4, .pdf)
        file_extension = os.path.splitext(file.filename)[1]
        
        # STEP 4: Ek unique naam generate karna (uuid) taki same naam ki do photos aapas mein na takrayein
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        
        # STEP 5: Poora rasta banana jahan file save hogi (e.g., app/static/uploads/ab12-cd34.jpg)
        file_path = os.path.join(upload_dir, unique_filename)
        
        # STEP 6: File ko hard-drive par save karna (shutil RAM ko safe rakhta hai)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # STEP 7: Frontend ke liye URL banana jo DB mein save hoga
        file_url = f"{settings.SERVER_URL}/static/uploads/{unique_filename}"
        
        return {
            "status": 200, 
            "message": "File uploaded successfully", 
            "file_type": file.content_type,
            "url": file_url
        }
        
    except Exception as e:
        # Agar hard-drive full ho ya permission error aaye toh catch karega
        raise HTTPException(status_code=500, detail=f"Upload Failed: {str(e)}")