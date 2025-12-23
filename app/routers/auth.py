from fastapi import APIRouter
from app.models.auth import UserRegister, UserLogin, Token
from app.services.auth_service import register_user, login_user

router = APIRouter()

@router.post("/register")
def register(user: UserRegister):
    return register_user(user)

@router.post("/login", response_model=Token)
def login(user: UserLogin):
    return login_user(user)