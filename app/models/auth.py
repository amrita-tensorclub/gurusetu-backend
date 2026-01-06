from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator
from typing import Optional
import re

class UserRegister(BaseModel):
    name: str
    email: EmailStr
    password: str = Field(..., min_length=6)
    role: str  # 'student' or 'faculty'
    department: Optional[str] = None
    
    # Specific IDs
    roll_no: Optional[str] = None
    employee_id: Optional[str] = None
    
    profile_picture: Optional[str] = None 

    # ✅ VALIDATOR: Enforce Email Domain based on Role
    @model_validator(mode='after')
    def validate_email_role_match(self):
        email = self.email.lower()
        role = self.role.lower()

        if role == "faculty":
            if not email.endswith("@cb.amrita.edu"):
                raise ValueError("Faculty email must end with @amrita.edu")
        
        elif role == "student":
            if not email.endswith("@cb.students.amrita.edu"):
                raise ValueError("Student email must end with @cb.students.amrita.edu")
        
        return self

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    role: str

class UserVerifyIdentity(BaseModel):
    email: EmailStr
    id_number: str
    role: str

class UserResetPassword(BaseModel):
    email: EmailStr
    new_password: str

    # ✅ FIX: Ensure password length check uses the correct validator
    @field_validator('new_password')
    def password_length(cls, v):
        if len(v) < 6:
            raise ValueError('Password must be at least 6 characters long')
        return v