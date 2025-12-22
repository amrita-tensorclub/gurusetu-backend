import uuid
from neo4j import Session
from app.core.database import Neo4jDriver
from app.core.security import hash_password,verify_password,create_access_token

driver=Neo4jDriver()

def register_user(data):
    with driver.session() as session:
        result= session.run(
            "MATCH (u:User {email:$email}) RETURN u",
            email=data.email
        )

        if result.single():
            raise ValueError("Email already registered")
        
        user_id=str(uuid.uuid4())
        password_hash=hash_password(data.password)

        labels = ":User:" + ("Student" if data.role == "student" else "Faculty")

        session.run(
            f"""
            CREATE (u{labels} {{
                user_id: $user_id,
                email: $email,
                password_hash: $password_hash,
                role: $role,
                name: $name,
                roll_no: $roll_no,
                employee_id: $employee_id,
                is_active: true
            }})
            """,
            user_id=user_id,
            email=data.email,
            password_hash=password_hash,
            role=data.role,
            name=data.name,
            roll_no=data.roll_no,
            employee_id=data.employee_id
        )

        return user_id

def authenticate_user(email:str,password:str):
    with driver.session() as session:
        record=session.run(
            "MATCH (u:user {email:$email}) RETURN u",
            email=email
        ).single()

        if not record:
            return None
        
        user=record["u"]

        if not verify_password(password,user["password_hash"]):
            return None
        
        token=create_access_token(
            user_id=user["user_id"],
            role=user["role"]
        )
        return token