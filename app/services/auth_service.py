import uuid
import logging

from fastapi import HTTPException
from app.core.database import db
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
)
from app.models.auth import UserRegister, UserLogin

logger = logging.getLogger(__name__)


def register_user(user: UserRegister):
    session = db.get_session()

    try:
        # 1. Check if email exists
        query_check = "MATCH (u:User {email: $email}) RETURN u"
        result = session.run(query_check, email=user.email).single()

        if result:
            raise HTTPException(status_code=400, detail="Email already registered")

        # 2. Hash password & generate ID
        hashed_pw = hash_password(user.password)
        user_id = str(uuid.uuid4())

        # 3. Validate role
        role_lower = user.role.lower()
        if role_lower == "student":
            role_label = "Student"
        elif role_lower == "faculty":
            role_label = "Faculty"
        else:
            raise HTTPException(
                status_code=400,
                detail="Invalid role. Must be 'student' or 'faculty'",
            )

        # 4. Create user node
        query_create = f"""
        CREATE (u:User:{role_label} {{
            user_id: $user_id,
            email: $email,
            password_hash: $password_hash,
            name: $name,
            role: $role,
            roll_no: $roll_no,
            employee_id: $employee_id,
            is_active: true
        }})
        RETURN u.user_id AS id
        """

        session.run(
            query_create,
            user_id=user_id,
            email=user.email,
            password_hash=hashed_pw,
            name=user.name,
            role=user.role,
            roll_no=user.roll_no,
            employee_id=user.employee_id,
        )

        return {"message": "User registered successfully", "user_id": user_id}

    except HTTPException:
        raise
    except Exception:
        logger.exception("Unexpected error during user registration")
        raise HTTPException(
            status_code=500,
            detail="Internal server error",
        )
    finally:
        session.close()


def login_user(user: UserLogin):
    session = db.get_session()

    try:
        query = "MATCH (u:User {email: $email}) RETURN u"
        result = session.run(query, email=user.email).single()

        if not result:
            raise HTTPException(status_code=400, detail="Invalid email or password")

        user_node = result["u"]

        if not verify_password(user.password, user_node["password_hash"]):
            raise HTTPException(status_code=400, detail="Invalid email or password")

        access_token = create_access_token(
            user_id=user_node["user_id"],
            role=user_node["role"],
        )

        return {"access_token": access_token, "token_type": "bearer"}

    except HTTPException:
        # Preserve expected validation/auth errors
        raise
    except Exception:
        # Log internal error but do NOT leak details
        logger.exception("Unexpected error during user login")
        raise HTTPException(
            status_code=500,
            detail="Internal server error",
        )
    finally:
        session.close()
