from pydantic import BaseModel, EmailStr, Field

class SignupRequest(BaseModel):
    name: str = Field(..., min_length=2)
    email: EmailStr
    password: str = Field(..., min_length=8)

class VerifySignupOTPRequest(BaseModel):
    email: EmailStr
    code: str = Field(..., min_length=6, max_length=6)

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class VerifyForgotOTPRequest(BaseModel):
    email: EmailStr
    code: str = Field(..., min_length=6, max_length=6)

class ResetPasswordRequest(BaseModel):
    reset_token: str
    password: str = Field(..., min_length=8)

class Verify2FARequest(BaseModel):
    email: EmailStr
    code: str = Field(..., min_length=6, max_length=6)
