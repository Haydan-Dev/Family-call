import os 
from dotenv import load_dotenv
load_dotenv()
class Settings:
    MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-default-secret-key-replace-in-env")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080
    
    # File Upload Configuration
    UPLOAD_DIR: str = "app/static/uploads"
    # Ye tera Abu-Hurairah ka base URL hoga (port 8000 ke sath)
    SERVER_URL: str = "http://127.0.0.1:8000"

settings = Settings()