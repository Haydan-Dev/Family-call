# Note : haydan pls yaar tu har ek comment ko dhyaan se padhna 

# IMP imports 
from fastapi import APIRouter
from app.models.user import User,UserLogin
from app.db import get_database
from app.core.security import PasswordHelper 
from app.utils.validators import Check_password
from fastapi import HTTPException
import bcrypt
from pymongo.errors import DuplicateKeyError
import datetime as dt
import logging
logger = logging.getLogger(__name__)
# router may kuch prefic daala taaki har api routes may bar bar user naa likhna pade mujhe
router = APIRouter(
    prefix="/users",
    tags=["Users"]
)
db = get_database()

# signup karne ka route hai ye 
@router.post("/signup")
#async funtion hai signup ke liye user_data ka data type user hai jo ki hamm user se hi frontend se le rahe hai
async def signup(user_data:User):
    # checking nahi ki ke email pehle se exist karta hai yaa nahi 
    # db may email ko and id ko unique karenge duplicate pe error dega and checking ki tention khatam
     # email ko lower case karna hai 
    user_data.email = user_data.email.lower()
    # user jo ki ek class tha uss ko .model_dump() se dicstiony may convert ki ya hai 
    user_dict = user_data.model_dump()
    #password check karo ke validation i.e 1 cap,1 small, 1 digit hai yaa nahi 
    Check_password(user_dict["password"])
    try:
        # password hashed karo ye ek class hai jo dusri file may se aayi hai
        user_dict["password"] = PasswordHelper.hash_password(user_dict["password"]) 
        # abb sab sahi hai to db may user ko insert karo signup ho gaya 
        # id ko result may save karo aage kaam
        result = await db.users.insert_one(user_dict)
        # db json samjhta hai and python class and str issi liye id ko object se str bana na pada 
        # taaki python id ko samjh sake
        user_dict["_id"] = str(result.inserted_id)
        # frontend ko return may success message dikha ya and ho gaya
        return {"message": "Account created successfully." , "user_id":user_dict["_id"],"user_email":user_dict["email"]}
    # agar exist karta haai to phir ye httpexception error dega 
    except DuplicateKeyError:
        # Sirf tabhi 409 dena jab email/id sach mein duplicate ho
        raise HTTPException(status_code=409, detail="User already exists, please login")
    except Exception as e:
        # Agar koi aur error hai (DB connection, code bug), toh ye terminal mein dikhega
        logger.error(f"System Error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error. Check Terminal!")
        
        
# ye login ki api hai 
@router.post("/login")
async def login(user_data:UserLogin):
    user_data.email = user_data.email.lower()
    existing_login = await db.users.find_one({"email":user_data.email})
    if not existing_login:
        raise HTTPException(status_code=401,detail="Invalid Email or Password")
    hash_check = bcrypt.checkpw(user_data.password.encode("utf-8"),existing_login["password"].encode("utf-8"))
    if not hash_check:
        raise HTTPException(status_code=401,detail="Invalid Email or Password")
    await db.users.update_one({"_id":existing_login["_id"]},{"$set":{"last_login_at":dt.datetime.now(dt.timezone.utc)}})
    return {"Message":"Login Successfull","login_email":user_data.email,"login_id":str(existing_login["_id"])}