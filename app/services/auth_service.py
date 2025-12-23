import uuid

from fastapi import HTTPException
from app.core.database import db  # <--- Use OUR singleton DB
from app.core.security import hash_password, verify_password, create_access_token
from app.models.auth import UserRegister, UserLogin

def register_user(user: UserRegister):
    session = db.get_session()
    
    try:
        # 1. Check if email exists
        query_check = "MATCH (u:User {email: $email}) RETURN u"
        result = session.run(query_check, email=user.email).single()
        
        if result:
            raise HTTPException(status_code=400, detail="Email already registered")

        # 2. Hash Password & ID
        hashed_pw = hash_password(user.password)
        user_id = str(uuid.uuid4())
        
        # 3. Dynamic Label Logic (Friend's idea was good, let's keep it safe)
        role_label = "Student" if user.role.lower() == "student" else "Faculty"

        # 4. Create Node (Merged Logic: We add roll_no and employee_id now)
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
        RETURN u.user_id as id
        """
        
        session.run(query_create, 
            user_id=user_id, 
            email=user.email, 
            password_hash=hashed_pw, 
            name=user.name, 
            role=user.role,
            roll_no=user.roll_no,      # <--- Added
            employee_id=user.employee_id # <--- Added
        )
        
        return {"message": "User registered successfully", "user_id": user_id}

    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()

def login_user(user: UserLogin):
    session = db.get_session()
    
    try:
        # FIX: Friend used 'u:user' (lowercase). It MUST be 'u:User' (Capital)
        query = "MATCH (u:User {email: $email}) RETURN u"
        result = session.run(query, email=user.email).single()
        
        if not result:
            raise HTTPException(status_code=400, detail="Invalid email or password")
            
        user_node = result["u"]
        
        if not verify_password(user.password, user_node["password_hash"]):
            raise HTTPException(status_code=400, detail="Invalid email or password")
            
        # Generate Token
        access_token = create_access_token(
            user_id=user_node["user_id"], 
            role=user_node["role"]
        )
        
        return {"access_token": access_token, "token_type": "bearer"}
        
    finally:
        session.close()
