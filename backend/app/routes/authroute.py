# Note : haydan pls yaar tu har ek comment ko dhyaan se padhna 
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

from jose import jwt
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/users",
    tags=["Users"]
)

db = get_database()

@router.post("/signup")
async def signup(user_data:User):
    user_data.email = user_data.email.lower()
    user_dict = user_data.model_dump()
    Check_password(user_dict["password"])
    try:
        user_dict["password"] = PasswordHelper.hash_password(user_dict["password"]) 
        result = await db.users.insert_one(user_dict)
        user_dict["_id"] = str(result.inserted_id)
        
        token = {
            "sub": str(user_dict["_id"]),
            "exp": dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        }
        encoded_jwt = jwt.encode(token, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        
        return {"message": "Account created successfully.", "access_token": encoded_jwt, "user_email": user_dict["email"]}
    except DuplicateKeyError:
        raise HTTPException(status_code=409, detail="User already exists, please login")
    except Exception as e:
        logger.error(f"System Error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error. Check Terminal or Error_Log!")
        
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
    
    token = {
        "sub": str(existing_login["_id"]),
        "exp": dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    }
    encoded_jwt = jwt.encode(token, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    
    return {"Message":"Login Successfull","login_email":user_data.email,"access_token":encoded_jwt}