# importing pymongo,uuid,datetime to use it
from motor.motor_asyncio import AsyncIOMotorClient
import asyncio
from core.config import settings    
# handling database fetching from mongodb using pymongo lib and variables
def get_database():
    client = AsyncIOMotorClient(settings.MONGO_URL)
    db = client["Family-call"]
    return db

async def main():
# Using __name__ = "main" best practices in python for databases 
    get_db = get_database()
    try:
        if(await get_db.command("ping")):
            print("Database is Connected Successfully")
            await get_db.users.create_index([("email",1)],unique = True)
    except Exception as e:
        print(f"Database Connection Failed: {e}")

if __name__ == "__main__":
     asyncio.run(main())
