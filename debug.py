# # import requests
# # import json

# # # URL of your backend login
# # url = "http://127.0.0.1:8000/auth/login"

# # # Test Credentials (Faculty)
# # payload = {
# #     "email": "deepika.t@gurusetu.edu",
# #     "password": "123456",
# #     "role": "faculty"  # We are sending lowercase 'faculty'
# # }

# # print(f"🔄 Attempting Login for: {payload['email']}...")

# # try:
# #     response = requests.post(url, json=payload)
    
# #     print(f"\n🔢 Status Code: {response.status_code}")
# #     print(f"📄 Response Body: {response.text}")
    
# #     if response.status_code == 200:
# #         print("\n✅ LOGIN SUCCESS! The backend is working fine.")
# #         print("   If you still can't login from the browser, the Frontend is sending the wrong data.")
# #     else:
# #         print("\n❌ LOGIN FAILED.")
# #         print("   Look at the 'Response Body' above to see the missing field or error.")

# # except Exception as e:
# #     print(f"\n💥 Connection Error: {e}")
# #     print("   Make sure your backend (uvicorn) is running!")

# import sys
# import os
# from passlib.context import CryptContext

# # Setup path
# sys.path.append(os.path.join(os.path.dirname(__file__), "."))

# from app.core.database import db

# # Setup the same hasher
# pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# def check_new_user():
#     session = db.get_session()
    
#     # --- ENTER YOUR NEW EMAIL HERE ---
#     email = "j.uma@gurusetu.edu" 
#     # ---------------------------------
    
#     try:
#         print(f"🔍 Searching for: {email}...")
        
#         # 1. Check if node exists and get labels/properties
#         query = "MATCH (u:User {email: $email}) RETURN u, labels(u) as labels"
#         result = session.run(query, email=email).single()

#         if not result:
#             print("❌ ERROR: User NOT FOUND in Database!")
#             print("   Did the signup actually succeed? Check the 'User' table.")
#             return

#         node = result["u"]
#         labels = result["labels"]
        
#         print("\n✅ USER FOUND!")
#         print(f"   Labels: {labels}  <-- Should contain 'User' AND 'Faculty'")
#         print(f"   Name: {node.get('name')}")
#         print(f"   Role: {node.get('role')}  <-- Should be 'faculty' (lowercase)")
#         print(f"   Stored Password: {node.get('password')}")

#         # 2. Check Role Logic
#         if "Faculty" not in labels and node.get('role') == 'faculty':
#             print("⚠️ WARNING: Node has 'faculty' role but missing :Faculty label.")
#             print("   This might prevent you from appearing in the directory.")

#         if node.get('role') == 'Faculty':
#             print("⚠️ WARNING: Role is 'Faculty' (Capitalized). Login might expect 'faculty'.")

#     except Exception as e:
#         print(f"💥 Error: {e}")
#     finally:
#         session.close()

# if __name__ == "__main__":
#     db.connect()
#     check_new_user()
#     db.close()
import requests
import sys
import os
from passlib.context import CryptContext

# Setup path
sys.path.append(os.path.join(os.path.dirname(__file__), "."))
from app.core.database import db

# Setup Password Hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
URL = "http://127.0.0.1:8000/auth/login"

def fix_and_test():
    session = db.get_session()
    email = "j.uma@gurusetu.edu"
    password = "123456"
    
    try:
        print(f"🔧 RESETTING password for {email}...")
        
        # 1. Force Reset Password in DB
        hashed_pw = pwd_context.hash(password)
        query = """
        MATCH (u:User {email: $email})
        SET u.password = $pw, u.role = 'faculty' 
        RETURN u.name, u.role
        """
        # Note: We also force role to lowercase 'faculty' to match your output
        session.run(query, email=email, pw=hashed_pw)
        print("✅ Password reset in Neo4j.")

        # 2. Test Login Endpoint
        print(f"\n🚀 TESTING Login Endpoint: {URL}")
        
        payload = {
            "email": email,
            "password": password,
            "role": "faculty" # Trying lowercase first
        }
        
        print(f"   Sending: {payload}")
        response = requests.post(URL, json=payload)
        
        print(f"\n   Status: {response.status_code}")
        print(f"   Response: {response.text}")

        if response.status_code == 200:
            print("\n🎉 SUCCESS! Login is working.")
            print("   Go to your browser and use these exact credentials.")
        else:
            print("\n❌ FAILED via Python too.")
            print("   This means the bug is inside your 'app/routers/auth.py' file.")
            print("   Please paste your 'auth.py' code here so I can fix the logic.")

    except Exception as e:
        print(f"💥 Error: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    db.connect()
    fix_and_test()
    db.close()