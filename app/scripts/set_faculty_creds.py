import sys
import os
from passlib.context import CryptContext

# Setup path to import from 'app'
sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))

from app.core.database import db

# Setup Password Hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def set_credentials():
    session = db.get_session()
    try:
        print("🔄 Fetching Faculty...")
        # Get all faculty nodes
        result = session.run("MATCH (f:Faculty) RETURN f.user_id as uid, f.name as name")
        
        faculty_list = [{"uid": r["uid"], "name": r["name"]} for r in result]

        print(f"found {len(faculty_list)} faculty members.\n")
        print(f"{'NAME':<30} | {'EMAIL (Login)':<35} | {'PASSWORD'}")
        print("-" * 80)

        for fac in faculty_list:
            name = fac['name']
            uid = fac['uid']
            
            # 1. Generate Cleaner Email (Fixing the leading dot issue)
            # Remove Dr. and extra spaces first
            temp_name = name.lower().replace("dr.", "").replace("dr ", "")
            temp_name = temp_name.strip() # Remove leading/trailing spaces
            
            # Replace remaining spaces with dots
            clean_name = temp_name.replace(" ", ".")
            
            # Remove double dots if any
            while ".." in clean_name:
                clean_name = clean_name.replace("..", ".")
            
            base_email = f"{clean_name}@gurusetu.edu"
            email = base_email
            
            # 2. Check for collisions (Is this email taken by SOMEONE ELSE?)
            counter = 1
            while True:
                check_query = """
                MATCH (u:User {email: $email})
                WHERE u.user_id <> $uid
                RETURN count(u) as exists
                """
                exists = session.run(check_query, email=email, uid=uid).single()["exists"]
                
                if exists == 0:
                    break # Email is free for this user!
                
                # Email taken, increment counter
                counter += 1
                email = f"{clean_name}{counter}@gurusetu.edu"

            # 3. Hash Password
            plain_password = "123456"
            hashed_password = pwd_context.hash(plain_password)

            # 4. Update the DB
            session.run("""
                MATCH (f:Faculty {user_id: $uid})
                SET f.email = $email,
                    f.password = $password
            """, uid=uid, email=email, password=hashed_password)

            print(f"{name:<30} | {email:<35} | {plain_password}")

        print("-" * 80)
        print("\n✅ SUCCESS! Credentials updated correctly.")

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    db.connect()
    set_credentials()
    db.close()