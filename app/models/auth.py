from pydantic import BaseModel, EmailStr, validator
from typing import Optional

class UserRegister(BaseModel):
    email: EmailStr
    password: str
    name: str
    role: str
    roll_no: Optional[str] = None
    employee_id: Optional[str] = None
    department: Optional[str] = None

    # 1. Simple Password Validation (Length Only)
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 6:
            raise ValueError('Password must be at least 6 characters long')
        return v

    # REMOVED: The custom email validator is gone.
    # EmailStr (from pydantic) will still ensure it looks like "user@domain.com"

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str

# --- New Models for Forgot Password ---
class UserVerifyIdentity(BaseModel):
    email: EmailStr
    role: str
    id_number: str # Roll No or Employee ID

class UserResetPassword(BaseModel):
    email: EmailStr
    new_password: str
    
    @validator('new_password')
    def validate_new_password(cls, v):
        if len(v) < 6:
            raise ValueError('Password must be at least 6 characters long')
        return v