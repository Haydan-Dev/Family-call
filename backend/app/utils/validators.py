from fastapi  import HTTPException

import re
def Check_password(user_password):
    if len(user_password) <= 5 or len(user_password) >= 13:
        raise HTTPException(status_code=400,detail="Invalid-Password: \n Please Enter a Password contain atleast 6 and atmost 12 characters !")
    if not re.search( r"[A-Z]",user_password):
        raise HTTPException(status_code=400,detail="Invalid-Password: \n Please Enter a Password contain atleast 1 Uper Case character !")
    if not re.search( r"[a-z]",user_password):
        raise HTTPException(status_code=400,detail="Invalid-Password: \n Please Enter a Password contain atleast 1 Lower Case Character !")
    if not re.search( r"\d",user_password):
        raise HTTPException(status_code=400,detail="Invalid-Password: \n Please Enter a Password contain atleast 1 Digit !")
    if not re.search( r"[@$!%*?&]",user_password):
        raise HTTPException(status_code=400,detail="Invalid-Password: \n Please Enter a Password contain atleast 1 Special Character !")
    return user_password
