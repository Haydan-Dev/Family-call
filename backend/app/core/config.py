import os 
from dotenv import load_dotenv
load_dotenv()
class Settings:
    MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
settings = Settings()