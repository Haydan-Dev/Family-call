# importing pymongo,uuid,datetime to use it
import pymongo
# handling database fetching from mongodb using pymongo lib and variables
def get_database():
    client = pymongo.MongoClient("mongodb://localhost:27017/")
    db = client["Family-call"]
    return db

# Using __name__ = "main" best practices in python for databases 
if __name__ == "__main__":
    get_db = get_database()
    try:
        if(get_db.command("ping")):
            print("Database is Connected Successfully")
    except Exception as e:
        print(f"Connection Failed: {e}")
        
