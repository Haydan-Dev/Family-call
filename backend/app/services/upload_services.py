import os
import uuid
import shutil
from fastapi import UploadFile

def save_upload_file(file: UploadFile, upload_dir: str, server_url: str) -> dict:
    os.makedirs(upload_dir, exist_ok=True)
    
    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = os.path.join(upload_dir, unique_filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    file_url = f"{server_url}/static/uploads/{unique_filename}"
    
    return {
        "status": 200, 
        "message": "File uploaded successfully", 
        "file_type": file.content_type,
        "url": file_url
    }
