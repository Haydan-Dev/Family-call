#IMP imports :
# fastapi ke api router daala taaki routes and prefix and tags ko use kar sake 
from fastapi import APIRouter
#  Depend taaki Oaunthen2schema use karsake
from fastapi import Depends
# app folder se db.py file may se get_database() functio / method ko bulaya,
# taaki db ko access karsake iss file may 
from app.db import get_database
# contact.py model folder may se contact_user class ko bulaana padega 
from app.models.contacts import Contact_save,User_Contact
# abb may jwt token ko header se fetch karne and uss ko deocde karne waale function ko wo ,
# encoded code dilwaa ne waale function ko import karaha hoon
from app.core.security import get_current_user_token
# erro handling ke liye httpsException
from fastapi import HTTPException

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
async def save_contact(contact_data:Contact_save,user_id: str = Depends(get_current_user_token)):
    # Note abhi check nahi kiya hai ke contact already exist karna hai yaa nahi!!!!
    # abb check karna padega ke contact pehle se hi save hai yaa nahi hai.
    if_contact_exist = await db.contacts.find_one({"owner_id":user_id,"contact_email":contact_data.contact_email,"contact_nickname":contact_data.contact_nickname})
    if if_contact_exist:
        raise HTTPException(status_code=409,detail="Contact Already Exist")
    else:
        # AB DEKH ASLI MAGIC (Ameer Data Transformation):
        # 1. 'User_Contact' (Bada Model) ka object banaya.
        # 2. 'owner_id' jo token se aayi hai wo dali.
        # 3. '**contact_data.model_dump()' se baaki saara maal (email/nick) 'unpack' karke bhar diya.
        # Isse 'created_at' aur 'is_pinned' jaise default fields auto-generate ho jayenge.
        new_contact_obj = User_Contact(owner_id=user_id, **contact_data.model_dump())

        # Ab is pure 'Ameer' object ko Python Dictionary (JSON format) mein convert kiya DB mein daalne ke liye
        contact_info = new_contact_obj.model_dump() 

        # Idhar database ke 'contacts' collection mein pura bundle ek saath insert kiya
        save_result = await db.contacts.insert_one(contact_info)   
        
        # Save result se humne MongoDB ki automatically generated ID uthayi
        # Usko string mein convert kiya taaki frontend usko easily handle kar sake
        save_contact_id = str(save_result.inserted_id) 
        
        return {
            "Message": "Contact save Successfully",
            "data": save_contact_id
        }



# 2. contact ko delete karne ki api
@router.delete("/delete/{contact_id}")
async def delete_contact():
    pass

# 3. contact ko find/search karne ki api
@router.get("/search_contact/{nickname}")
async def search_contact():
    pass