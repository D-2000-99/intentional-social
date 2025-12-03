from pydantic import BaseModel, EmailStr, field_validator

class LoginRequest(BaseModel):
    username_or_email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class SendOTPRequest(BaseModel):
    email: EmailStr

class VerifyOTPRequest(BaseModel):
    email: EmailStr
    otp_code: str

class CompleteRegistrationRequest(BaseModel):
    email: EmailStr
    username: str
    password: str
    otp_code: str
    
    @field_validator('otp_code')
    @classmethod
    def validate_otp_code(cls, v: str) -> str:
        if not v or len(v) != 6 or not v.isdigit():
            raise ValueError('Verification code must be a 6-digit number')
        return v
