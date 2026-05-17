import uuid
import logging
import bcrypt
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from jose import jwt, JWTError

from app.db import get_database
from app.core.security import PasswordHelper
from app.core.config import settings

# Import schemas, services, and helpers following MSR
from app.models.auth_schemas import (
    SignupRequest,
    VerifySignupOTPRequest,
    LoginRequest,
    ForgotPasswordRequest,
    VerifyForgotOTPRequest,
    ResetPasswordRequest
)
from app.services.email_service import send_otp_email
from app.utils.helpers import generate_otp

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/auth",
    tags=["Auth OTP"]
)

db = get_database()

@router.post("/signup")
async def signup(user_data: SignupRequest, background_tasks: BackgroundTasks):
    email_lower = user_data.email.lower()
    
    # Check if verified user exists
    existing_user = await db.users.find_one({"email": email_lower})
    if existing_user:
        if existing_user.get("is_verified", False):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered. Please sign in."
            )
        else:
            # Update password/name for an existing but unverified user to prevent stuck states
            await db.users.update_one(
                {"_id": existing_user["_id"]},
                {"$set": {
                    "name": user_data.name,
                    "hashed_password": PasswordHelper.hash_password(user_data.password)
                }}
            )
    else:
        # Create unverified user
        new_user = {
            "_id": str(uuid.uuid4()),
            "name": user_data.name,
            "email": email_lower,
            "hashed_password": PasswordHelper.hash_password(user_data.password),
            "is_verified": False,
            "created_at": datetime.now(timezone.utc)
        }
        await db.users.insert_one(new_user)
    
    # Generate and save OTP
    otp_code = generate_otp()
    await db.otp_codes.delete_many({"email": email_lower, "purpose": "signup"})
    await db.otp_codes.insert_one({
        "email": email_lower,
        "otp": otp_code,
        "purpose": "signup",
        "created_at": datetime.now(timezone.utc)
    })
    
    # Dispatch non-blocking background email delivery
    background_tasks.add_task(send_otp_email, email_lower, otp_code, "signup")
    
    return {"message": "Signup registered. OTP verification email sent.", "email": email_lower}


@router.post("/verify-signup-otp")
async def verify_signup_otp(data: VerifySignupOTPRequest):
    email_lower = data.email.lower()
    
    # Check OTP in sandbox
    otp_record = await db.otp_codes.find_one({
        "email": email_lower,
        "otp": data.code,
        "purpose": "signup"
    })
    
    if not otp_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect or expired verification code."
        )
    
    # Delete verified OTP code
    await db.otp_codes.delete_one({"_id": otp_record["_id"]})
    
    # Mark user as verified
    user = await db.users.find_one({"email": email_lower})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User record not found."
        )
        
    await db.users.update_one(
        {"_id": user["_id"]},
        {"$set": {"is_verified": True}}
    )
    
    # Generate standard JWT Access Token
    token_payload = {
        "sub": str(user["_id"]),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    }
    encoded_jwt = jwt.encode(token_payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    
    return {"access_token": encoded_jwt, "token_type": "bearer", "user_email": email_lower}


@router.post("/resend-signup-otp")
async def resend_signup_otp(data: ForgotPasswordRequest, background_tasks: BackgroundTasks):
    email_lower = data.email.lower()
    
    user = await db.users.find_one({"email": email_lower})
    if not user:
        raise HTTPException(status_code=404, detail="User account not found.")
        
    if user.get("is_verified", False):
        raise HTTPException(status_code=400, detail="Account is already verified.")
        
    otp_code = generate_otp()
    await db.otp_codes.delete_many({"email": email_lower, "purpose": "signup"})
    await db.otp_codes.insert_one({
        "email": email_lower,
        "otp": otp_code,
        "purpose": "signup",
        "created_at": datetime.now(timezone.utc)
    })
    
    background_tasks.add_task(send_otp_email, email_lower, otp_code, "signup")
    return {"message": "Resent OTP successfully."}


@router.post("/login")
async def login(credentials: LoginRequest):
    email_lower = credentials.email.lower()
    
    user = await db.users.find_one({"email": email_lower})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )
        
    # Verify hashed password
    is_valid = bcrypt.checkpw(credentials.password.encode("utf-8"), user["hashed_password"].encode("utf-8")) if "hashed_password" in user else bcrypt.checkpw(credentials.password.encode("utf-8"), user["password"].encode("utf-8"))
    
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )
        
    # Check verification status
    if not user.get("is_verified", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your email is not verified. Please verify your email first."
        )
        
    # Set login timestamp
    await db.users.update_one(
        {"_id": user["_id"]},
        {"$set": {"last_login_at": datetime.now(timezone.utc)}}
    )
    
    # Generate Access Token
    token_payload = {
        "sub": str(user["_id"]),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    }
    encoded_jwt = jwt.encode(token_payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    
    return {"access_token": encoded_jwt, "token_type": "bearer", "user_email": email_lower}


@router.post("/forgot-password")
async def forgot_password(data: ForgotPasswordRequest, background_tasks: BackgroundTasks):
    email_lower = data.email.lower()
    
    user = await db.users.find_one({"email": email_lower})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No account associated with this email address."
        )
        
    # Generate and save OTP
    otp_code = generate_otp()
    await db.otp_codes.delete_many({"email": email_lower, "purpose": "reset"})
    await db.otp_codes.insert_one({
        "email": email_lower,
        "otp": otp_code,
        "purpose": "reset",
        "created_at": datetime.now(timezone.utc)
    })
    
    # Background send email
    background_tasks.add_task(send_otp_email, email_lower, otp_code, "reset")
    
    return {"message": "Verification code sent to your email.", "email": email_lower}


@router.post("/verify-forgot-otp")
async def verify_forgot_otp(data: VerifyForgotOTPRequest):
    email_lower = data.email.lower()
    
    # Check OTP sandbox
    otp_record = await db.otp_codes.find_one({
        "email": email_lower,
        "otp": data.code,
        "purpose": "reset"
    })
    
    if not otp_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect or expired reset code."
        )
        
    # Delete OTP
    await db.otp_codes.delete_one({"_id": otp_record["_id"]})
    
    # Generate short-lived temporary secure reset token
    reset_payload = {
        "sub": email_lower,
        "purpose": "reset_password",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=15)
    }
    reset_token = jwt.encode(reset_payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    
    return {"reset_token": reset_token}


@router.post("/reset-password")
async def reset_password(data: ResetPasswordRequest):
    try:
        # Decode reset_token
        payload = jwt.decode(data.reset_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("purpose") != "reset_password":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid token purpose."
            )
            
        email = payload.get("sub")
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid token data."
            )
            
        # Update user's password in MongoDB
        hashed_password = PasswordHelper.hash_password(data.password)
        
        # We update both hashed_password and password to support compatibility with both styles
        await db.users.update_one(
            {"email": email},
            {"$set": {
                "hashed_password": hashed_password,
                "password": hashed_password
            }}
        )
        
        return {"message": "Password updated successfully."}
        
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token has expired or is invalid. Please request a new code."
        )
