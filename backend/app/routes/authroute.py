# Note : haydan pls yaar tu har ek comment ko dhyaan se padhna 
from fastapi import APIRouter, HTTPException, BackgroundTasks, Header
from app.models.user import User,UserLogin
from app.db import get_database
from app.core.security import PasswordHelper 
from app.utils.validators import Check_password
import bcrypt
from pymongo.errors import DuplicateKeyError
import datetime as dt
import logging
import uuid

from jose import jwt, JWTError
from app.core.config import settings

# Imports for OTP Verification Flow
from pydantic import BaseModel, EmailStr
from app.services.email_service import send_otp_email
from app.utils.helpers import generate_otp

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/users",
    tags=["Users"]
)

db = get_database()

class VerifyOTPRequest(BaseModel):
    email: EmailStr
    code: str

class FCMTokenUpdate(BaseModel):
    fcm_token: str

@router.post("/signup")
async def signup(user_data:User, background_tasks: BackgroundTasks):
    user_data.email = user_data.email.lower()
    Check_password(user_data.password)
    try:
        # Initialize the Full Model to generate all default values
        full_user = User(
            full_name=user_data.full_name,
            email=user_data.email,
            password=user_data.password,
            profile_pic_url=user_data.profile_pic_url
        )
        
        # Export & Mutate
        user_dict = full_user.model_dump()
        
        # Inject Secrets
        user_dict["_id"] = str(uuid.uuid4())
        user_dict["password"] = PasswordHelper.hash_password(user_data.password)
        user_dict["is_verified"] = False
        
        # Database Insert
        result = await db.users.insert_one(user_dict)
        
        # OTP logic
        otp_code = generate_otp()
        await db.otp_codes.delete_many({"email": user_dict["email"], "purpose": "signup"})
        await db.otp_codes.insert_one({
            "email": user_dict["email"],
            "otp": otp_code,
            "purpose": "signup",
            "created_at": dt.datetime.now(dt.timezone.utc)
        })
        
        # Asynchronously send the verification email
        background_tasks.add_task(send_otp_email, user_dict["email"], otp_code, "signup")
        
        return {"message": "Account created. Please check your email for the OTP."}
    except DuplicateKeyError:
        raise HTTPException(status_code=409, detail="User already exists, please login")
    except Exception as e:
        logger.error(f"System Error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error. Check Terminal or Error_Log!")
        
@router.post("/verify-otp")
async def verify_otp(data: VerifyOTPRequest):
    email_lower = data.email.lower()
    
    # Check OTP sandbox
    otp_record = await db.otp_codes.find_one({
        "email": email_lower,
        "otp": data.code,
        "purpose": "signup"
    })
    
    if not otp_record:
        raise HTTPException(
            status_code=400,
            detail="Incorrect or expired verification code."
        )
        
    # Delete verified OTP code
    await db.otp_codes.delete_one({"_id": otp_record["_id"]})
    
    # Mark user as verified
    user = await db.users.find_one({"email": email_lower})
    if not user:
        raise HTTPException(
            status_code=404,
            detail="User record not found."
        )
        
    await db.users.update_one(
        {"_id": user["_id"]},
        {"$set": {"is_verified": True}}
    )
    
    # JWT logic from old signup:
    token = {
        "sub": str(user["_id"]),
        "exp": dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    }
    encoded_jwt = jwt.encode(token, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    
    return {"message": "Account created successfully.", "access_token": encoded_jwt, "user_email": user["email"]}

@router.post("/login")
async def login(user_data:UserLogin, background_tasks: BackgroundTasks):
    user_data.email = user_data.email.lower()
    existing_login = await db.users.find_one({"email":user_data.email})
    if not existing_login:
        raise HTTPException(status_code=401,detail="Invalid Email or Password")
        
    if not existing_login.get("is_verified"):
        raise HTTPException(status_code=403, detail="Please verify your email first.")
        
    stored_password = existing_login.get("password")
    
    if not stored_password:
        raise HTTPException(status_code=401, detail="Invalid Email or Password (Legacy Account)")
        
    hash_check = bcrypt.checkpw(user_data.password.encode("utf-8"), stored_password.encode("utf-8"))
    if not hash_check:
        raise HTTPException(status_code=401,detail="Invalid Email or Password")
        
    # 2FA Check
    if existing_login.get("is_2fa_enabled", False):
        otp_code = generate_otp()
        await db.otp_codes.delete_many({"email": user_data.email, "purpose": "2fa_login"})
        await db.otp_codes.insert_one({
            "email": user_data.email,
            "otp": otp_code,
            "purpose": "2fa_login",
            "created_at": dt.datetime.now(dt.timezone.utc)
        })
        background_tasks.add_task(send_otp_email, user_data.email, otp_code, "2fa_login")
        return {"requires_2fa": True, "email": user_data.email, "message": "2FA OTP sent"}
        
    await db.users.update_one({"_id":existing_login["_id"]},{"$set":{"last_login_at":dt.datetime.now(dt.timezone.utc)}})
    
    token = {
        "sub": str(existing_login["_id"]),
        "exp": dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    }
    encoded_jwt = jwt.encode(token, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    
    return {"Message":"Login Successfull","login_email":user_data.email,"access_token":encoded_jwt}

@router.post("/login/verify-2fa")
async def verify_2fa(data: VerifyOTPRequest):
    email_lower = data.email.lower()
    
    # Check OTP sandbox
    otp_record = await db.otp_codes.find_one({
        "email": email_lower,
        "otp": data.code,
        "purpose": "2fa_login"
    })
    
    if not otp_record:
        raise HTTPException(
            status_code=400,
            detail="Incorrect or expired 2FA code."
        )
        
    # Delete OTP
    await db.otp_codes.delete_one({"_id": otp_record["_id"]})
    
    user = await db.users.find_one({"email": email_lower})
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
        
    # Set login timestamp
    await db.users.update_one(
        {"_id": user["_id"]},
        {"$set": {"last_login_at": dt.datetime.now(dt.timezone.utc)}}
    )
    
    # Generate Access Token
    token = {
        "sub": str(user["_id"]),
        "exp": dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    }
    encoded_jwt = jwt.encode(token, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    
    return {"Message": "Login Successfull", "login_email": email_lower, "access_token": encoded_jwt}


# ─────────────────────────────────────────────
# Phase 2 — FCM Token Registration Endpoint
# ─────────────────────────────────────────────
@router.patch("/update_fcm_token")
async def update_fcm_token(
    payload: FCMTokenUpdate,
    authorization: str = Header(..., description="Bearer <JWT>")
):
    # ── Extract & Validate JWT ──
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Invalid Authorization header format.")

    try:
        decoded = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = decoded.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Token payload missing 'sub'.")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token.")

    # ── Vault Update — store FCM token under android key ──
    result = await db.users.update_one(
        {"_id": user_id},
        {"$set": {"fcm_tokens.android": payload.fcm_token}}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found in database.")

    logger.info(f"FCM token saved for user {user_id}")
    return {"message": "FCM token registered successfully."}