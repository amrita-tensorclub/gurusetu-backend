from fastapi import APIRouter
from app.models.auth import UserRegister, UserLogin, Token, UserVerifyIdentity, UserResetPassword
from app.services.auth_service import register_user, login_user, verify_identity, reset_password

router = APIRouter()

# REMOVED: response_model=Token (This prevents the Validation Error)
@router.post("/register")
def register(user: UserRegister):
    return register_user(user)

@router.post("/login", response_model=Token)
def login(user: UserLogin):
    return login_user(user)

@router.post("/verify-identity")
def verify_user_identity(data: UserVerifyIdentity):
    return verify_identity(data)

@router.post("/reset-password")
def reset_user_password(data: UserResetPassword):
    return reset_password(data)