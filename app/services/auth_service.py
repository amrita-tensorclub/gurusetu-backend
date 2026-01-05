import uuid
import logging
from fastapi import HTTPException
from app.core.database import db
from app.core.security import hash_password, verify_password, create_access_token
from app.models.auth import UserRegister, UserLogin, UserVerifyIdentity, UserResetPassword
from app.services.embedding import generate_embedding

logger = logging.getLogger(__name__)

def register_user(user: UserRegister):
    session = db.get_session()
    try:
        clean_email = user.email.strip().lower()
        clean_password = user.password.strip()

        # Check existing
        result = session.run("MATCH (u:User {email: $email}) RETURN u", email=clean_email).single()
        if result: raise HTTPException(status_code=400, detail="Email already registered")

        hashed_pw = hash_password(clean_password)
        user_id = str(uuid.uuid4())
        
        # Safe inputs
        roll_no = user.roll_no.strip() if user.roll_no else None
        emp_id = user.employee_id.strip() if user.employee_id else None
        dept = user.department.strip() if user.department else "General"
        
        # ✅ FIX: Extract the profile picture from the request
        # (Default to None if not provided, or an empty string if you prefer)
        profile_pic = getattr(user, "profile_picture", None) 

        profile_text = f"{user.name} {user.role} {dept}"
        embedding = generate_embedding(profile_text)

        role_lower = user.role.lower()
        
        if role_lower == "student":
            query = """
            CREATE (u:User:Student {
                user_id: $uid, 
                email: $email, 
                password_hash: $pw, 
                name: $name,
                role: 'Student', 
                roll_no: $roll, 
                department: $dept, 
                profile_picture: $pic,  // <--- ADDED THIS FIELD
                embedding: $emb, 
                is_active: true
            }) RETURN u.user_id"""
            
            session.run(query, uid=user_id, email=clean_email, pw=hashed_pw, name=user.name, 
                        roll=roll_no, dept=dept, pic=profile_pic, emb=embedding)
        
        elif role_lower == "faculty":
            query = """
            CREATE (u:User:Faculty {
                user_id: $uid, 
                email: $email, 
                password_hash: $pw, 
                name: $name,
                role: 'Faculty', 
                employee_id: $empid, 
                department: $dept, 
                profile_picture: $pic,  // <--- ADDED THIS FIELD
                embedding: $emb, 
                is_active: true
            }) RETURN u.user_id"""
            
            session.run(query, uid=user_id, email=clean_email, pw=hashed_pw, name=user.name, 
                        empid=emp_id, dept=dept, pic=profile_pic, emb=embedding)

        return {"message": "User registered successfully", "user_id": user_id}

    except HTTPException: raise
    except Exception as e:
        logger.exception("Register Error")
        raise HTTPException(status_code=500, detail=str(e))
    finally: session.close()

def login_user(user: UserLogin):
    session = db.get_session()
    try:
        clean_email = user.email.strip().lower()
        result = session.run("MATCH (u:User {email: $email}) RETURN u", email=clean_email).single()
        
        if not result or not verify_password(user.password.strip(), result["u"].get("password_hash", "")):
            raise HTTPException(status_code=400, detail="Invalid email or password")
            
        u_role = result["u"].get("role", "student").lower()
        token = create_access_token(user_id=result["u"]["user_id"], role=u_role)
        
        return {"access_token": token, "token_type": "bearer", "role": u_role}
    finally: session.close()

# Keep these for your features
def verify_identity(data: UserVerifyIdentity):
    session = db.get_session()
    try:
        email = data.email.strip().lower()
        id_num = data.id_number.strip()
        query = "MATCH (u:User {email: $email}) WHERE u.roll_no = $id OR u.employee_id = $id RETURN u"
        if not session.run(query, email=email, id=id_num).single():
            raise HTTPException(status_code=400, detail="Verification Failed: Email and ID do not match.")
        return {"message": "Verified"}
    finally: session.close()

def reset_password(data: UserResetPassword):
    session = db.get_session()
    try:
        email = data.email.strip().lower()
        new_pw = hash_password(data.new_password.strip())
        session.run("MATCH (u:User {email: $email}) SET u.password_hash = $pw", email=email, pw=new_pw)
        return {"message": "Password updated"}
    finally: session.close()