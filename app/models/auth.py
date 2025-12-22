from pydantic import BaseModel,EmailStr
from typing import Optional

class RegisterRequest(BaseModel):
    email:EmailStr
    password:str
    name:str
    role:str
    roll_no:Optional[str]=None
    employee_id:Optional[str]=None

class LoginRequest(BaseModel):
    email:EmailStr
    password:str

class TokenResponse(BaseModel):
    access_token:str
    token_type:str="Bearer"

