# importing pymongo libs and settings to use it
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings    

# Global variables ko None set kiya taaki ek hi connection poori app use kare (No Memory Leaks)
client = AsyncIOMotorClient(settings.MONGO_URL)
db = client["Family-call"]

# Ye function FastAPI ke START hote hi chalega (Lifespan ke through)
async def connect_to_mongo():
    # Global variables ko modify karne ke liye 'global' keyword use kiya
    global client, db
    try:
        # Ping karke check kar rahe hain connection zinda hai ya nahi
        await db.command("ping")
        print("Database is Connected Successfully")
        
        # Indexing yahan karenge taaki server start hote hi lag jaye
        await db.users.create_index([("email", 1)], unique=True)
    except Exception as e:
        print(f"Database Connection Failed: {e}")

# Ye function FastAPI ke SHUTDOWN hote hi chalega
async def close_mongo_connection():
    global client
    if client:
        # Pura connection pool safely band kar dega
        client.close()
        print("Database Connection Closed safely")

# Handling database fetching from mongodb
def get_database():
    # Ab ye naya client nahi banayega, balki global zinda 'db' variable return karega
    return db