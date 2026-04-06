# imports
import bcrypt  # Password ko encrypt karne aur usme 'salt' (namak) milane ke liye taaki db hack hone pe bhi password safe rahe.
import jwt     # PyJWT library: JWT token (VIP Lifaafa) banane (encode) aur kholne (decode) ka asali cryptography engine.
import os      # Operating System library: Tere system aur .env file se hidden variables (jaise SECRET_KEY) bahar nikalne ke liye.

from dotenv import load_dotenv  # .env file (jahan tere secrets chhupe hain) ko Python ki memory mein load karne ka switch.

from fastapi import HTTPException, Depends 
# HTTPException: Jab token galat ho ya hacker aaye, toh seedha 401 (Unauthorized) ki laat (error) marne ka hathiyaar.
# Depends: FastAPI ka jadoo (Dependency Injection)! Ek function (Scanner) ka result nikal kar automatically doosre function (Bouncer) mein daalne ke liye.

from fastapi.security import OAuth2PasswordBearer
# FastAPI ka inbuilt Metal Detector: Jo frontend ke Request Header mein ghusega, "Bearer" shabd ko kaatega aur sirf asli token nikalega.

# The Scanner: FastAPI ka inbuilt Metal Detector. 
# Ye Header se "Bearer" token nikalega aur Swagger UI mein Lock 🔒 button banayega.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/users/login")

# Khufiya Chaabi: .env file se apna SECRET_KEY nikal rahe hain token kholne ke liye
load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")

class PasswordHelper:
    @staticmethod
    def hash_password(passwordhashing):
        # Plain password ko uthao, salt dalo, aur usko encrypt karke aisi string banao jo koi hack na kar sake
        password_hash = passwordhashing.encode('utf-8')
        password_salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(password_hash, password_salt)
        return  hashed_password.decode('utf-8')


# The Bouncer: Asli gatekeeper jo har protected route ke aage khada hoga!
# Depends(oauth2_scheme) -> Ye scanner ko command de raha hai ki jaa token leke aa!
def get_current_user_token(jwt_token: str = Depends(oauth2_scheme)):
    try:
        # Lifaafa kholne ki koshish (Decoding)
        payload =  jwt.decode(jwt_token, SECRET_KEY, algorithms=["HS256"])
        
        # Agar lifaafa sahi se khul gaya, toh uske andar se user ki ID ('sub') return kar do
        return payload.get("sub")
        
    except jwt.ExpiredSignatureError:
        # Pata chala token 7 din purana hai! Seedha 401 ki laat maar ke bhagao.
        raise HTTPException(status_code=401, detail="Token Expired")
        
    except jwt.InvalidTokenError:
        # Hacker ne token badalne ki koshish ki hai! Nakli token pe 401 ki laat.
        raise HTTPException(status_code=401, detail="Invalid Token")