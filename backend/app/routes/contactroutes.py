#IMP imports :
# fastapi ke api router daala taaki routes and prefix and tags ko use kar sake 
from fastapi import APIRouter
#  Depend taaki Oaunthen2schema use karsake
from fastapi import Depends
# app folder se db.py file may se get_database() functio / method ko bulaya,
# taaki db ko access karsake iss file may 
from app.db import get_database
# contact.py model folder may se contact_user class ko bulaana padega 
from app.models.contacts import User_Contact
# abb may jwt token ko header se fetch karne and uss ko deocde karne waale function ko wo ,
# encoded code dilwaa ne waale function ko import karaha hoon
from app.core.security import get_current_user_token

# router may kuch prefix daala taaki api ko bar bar routes api may contact naa dena pade
router = APIRouter(
    prefix="/contacts",
    tags=["Contacts"]
)
# idhar database ko ek variable db may daala  
db = get_database()

# idhar se api banana shuru:
# 1. contact ko save karne ki api
@router.post("/save")
async def save_contact(contact_data:User_Contact,user_id: str = Depends(get_current_user_token)):
    pass

# 2. contact ko delete karne ki api
@router.delete("/delete/{contact_id}")
async def delete_contact():
    pass

# 3. contact ko find/search karne ki api
@router.get("/search_contact/{nickname}")
async def search_contact():
    pass