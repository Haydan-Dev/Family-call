# Note : haydan pls yaar tu har ek comment ko dhyaan se padhna 

# IMP imports 
from fastapi import APIRouter
from app.models.user import User
from app.db import get_database
from core.security import PasswordHelper 
from utils.validators import Check_password
from fastapi import HTTPException

# router may kuch prefic daala taaki har api routes may bar bar user naa likhna pade mujhe
router = APIRouter(
    prefix="/user",
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
        # user ko success message ke liye frontend ko dene ke liye user waapis dena hiaa issi liye password ko idhar se delete karo,
        # wo db may safe hai 
        del user_dict["password"]
        # db json samjhta hai and python class and str issi liye id ko object se str bana na pada 
        # taaki python id ko samjh sake
        user_dict["_id"] = str(result.inserted_id)
        # frontend ko return may success message dikha ya and ho gaya
        return {"message": "Account created successfully." , "user_id":user_dict["_id"],"user_email":user_dict["email"]}
    except Exception as e:
        # agar exist karta haai to phir ye httpexception error dega 
        raise HTTPException(status_code = 409, detail = "user already exist, please login")