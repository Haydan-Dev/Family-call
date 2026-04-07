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
# delete ke liye hamme object id , db ke under docs ki banne waali id chahiye uss ke liye iss ko import karna hai
from bson import ObjectId
from bson.errors import InvalidId

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
# contact id wohi id hai jo save contact api 
# se db may contact ke save hone pe uss document ko di jaati hai 
async def delete_contact(contact_id:str,user_id:str = Depends(get_current_user_token)):
    try:
        valid_object_id = ObjectId(contact_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid Contact ID format")
    # contact exist karta hai yaa nahi ye dekhne ki zaruat nahi hai 
    # delete use karne pe agar exist karta hai to delete karega , agar contact exist nahi karta hai to error dega issi liye
    # hamme iss ko if else ke under daalna karna hoga
    delete_result = await db.contacts.delete_one({"_id":valid_object_id,"owner_id":user_id})
    if delete_result.deleted_count == 1:
        return {"Message":"Contact Deleted Successfully", "_id":str(valid_object_id), "user_id":user_id}
    else:
        raise HTTPException(status_code=404,detail="Contact Not Found")


# 3. contact ko find/search karne ki api
@router.get("/search_contact/{contact_nickname}")
async def search_contact(contact_nickname:str,user_id:str = Depends(get_current_user_token)):
    search_result = await db.contacts.find({"contact_nickname": {"$regex": contact_nickname, "$options": "i"},"owner_id":user_id}).to_list(length=100) # ye regx jo hai wo , no-casesensitivity ke liye use kiya hai mayne
    if len(search_result) > 0:
        for contacts in search_result:
            contacts["_id"] = str(contacts["_id"])
        total_contact_found = len(search_result)
        return {"number": total_contact_found,"Message":"Contact Found","contacts":search_result}
    else:
        return{"number": 0, "Message": "Contact Not Found", "contacts": []}