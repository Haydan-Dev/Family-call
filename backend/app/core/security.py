import bcrypt
from jose import jwt, JWTError
from fastapi import HTTPException, Depends 
from fastapi.security import OAuth2PasswordBearer
from app.core.config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/users/login")

class PasswordHelper:
    @staticmethod
    def hash_password(passwordhashing):
        password_hash = passwordhashing.encode('utf-8')
        password_salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(password_hash, password_salt)
        return  hashed_password.decode('utf-8')

def get_current_user_token(jwt_token: str = Depends(oauth2_scheme)):
    print("\n--- 🛡️ BOUNCER START 🛡️ ---")
    
    try:
        payload = jwt.decode(jwt_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid Token: Missing User ID")
        print(f"✅ SUCCESS: Token Decoded! User ID: {user_id}")
        return user_id

    except JWTError as e:
        print(f"🔥 CRITICAL DECODE ERROR: {str(e)}")
        raise HTTPException(status_code=401, detail=f"Invalid Token: {str(e)}")
    except Exception as e:
        print(f"🔥 CRITICAL SERVER ERROR: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal authentication error")