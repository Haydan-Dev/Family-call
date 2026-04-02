# importing pymongo,uuid,datetime to use it
from motor.motor_asyncio import AsyncIOMotorClient
import asyncio
# handling database fetching from mongodb using pymongo lib and variables
def get_database():
    client = AsyncIOMotorClient("mongodb://localhost:27017/")
    db = client["Family-call"]
    return db

async def main():
# Using __name__ = "main" best practices in python for databases 
    get_db = get_database()
    try:
        if(await get_db.command("ping")):
            print("Database is Connected Successfully")
    except Exception as e:
        print(f"Connection Failed: {e}")

if __name__ == "__main__":
     asyncio.run(main())
