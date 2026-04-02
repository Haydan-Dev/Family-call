from fastapi import APIRouter
from app.models.user import User
from app.db import get_database
from core.security import PasswordHelper

router = APIRouter(
    prefix="/user",
    tags=["Users"]
)
db = get_database()

# post method for creating user
@router.post("/")
async def create_user(user_data:User):
    # Step 1: Pydantic ko Dictionary banao (IntelliSense se .model_dump() use kar)
    user_dict = user_data.model_dump()
    # password hashing
    passwordhashing =  PasswordHelper.hash_password(user_data.password)
    # password hashing ko uss real db.password may save karna 
    user_dict["password"] = passwordhashing
    # Step 2: Database mein insert kar
    db.users.insert_one(user_dict)
    # Step 3: Success message return kar de
    user_dict["_id"] = str(user_dict["_id"])
    return {"Message":"User Saved", "data":user_dict}


# get method for display the post method data 
@router.get("/")
def display_data():
    db.users.find_one()

