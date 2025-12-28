from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from pydantic import BaseModel
from typing import List, Optional
from app.core.database import db
from app.core.security import get_current_user
import shutil
import uuid
import os
from datetime import datetime

router = APIRouter()

# ==========================================
# 1. MODELS
# ==========================================

# --- Shared Models ---
class WorkItem(BaseModel):
    title: str
    type: str
    year: str
    outcome: str
    collaborators: str

class ProjectCreate(BaseModel):
    title: str
    description: str
    from_date: str
    to_date: str
    tools: List[str]

# Added Publication Model
class PublicationItem(BaseModel):
    title: str
    year: str
    publisher: Optional[str] = ""
    link: Optional[str] = ""

# --- Student Profile Model ---
class StudentProfileUpdate(BaseModel):
    # Basic Info
    name: Optional[str] = None
    phone: Optional[str] = None
    department: Optional[str] = None
    batch: Optional[str] = None
    bio: Optional[str] = None
    profile_picture: Optional[str] = None
    
    # Experience Data
    skills: List[str] = []
    interests: List[str] = []
    projects: List[ProjectCreate] = []
    publications: List[PublicationItem] = [] # <--- Added this

# --- Faculty Profile Model ---
class FacultyProfileUpdate(BaseModel):
    name: Optional[str] = None
    profile_picture: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    designation: Optional[str] = None
    department: Optional[str] = None
    office_hours: Optional[str] = None
    cabin_block: Optional[str] = None
    cabin_floor: Optional[str] = None
    cabin_number: Optional[str] = None
    ug_details: List[str] = []
    pg_details: List[str] = []
    phd_details: List[str] = []
    domain_interests: List[str] = []
    previous_work: List[WorkItem] = []

# ==========================================
# 2. ROUTES
# ==========================================

# --- A. Upload Picture ---
@router.post("/upload-profile-picture")
async def upload_profile_picture(file: UploadFile = File(...)):
    try:
        os.makedirs("uploads", exist_ok=True)
        file_extension = file.filename.split(".")[-1]
        unique_filename = f"{uuid.uuid4()}.{file_extension}"
        file_path = f"uploads/{unique_filename}"
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        return {"url": f"http://localhost:8000/uploads/{unique_filename}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- B. GET Student Profile ---
@router.get("/student/profile/{user_id}")
def get_student_profile(user_id: str, current_user: dict = Depends(get_current_user)):
    session = db.get_session()
    try:
        # Fetch Basic Info
        query = """
        MATCH (u:User {user_id: $uid})
        OPTIONAL MATCH (u)-[:HAS_SKILL]->(s:Concept)
        OPTIONAL MATCH (u)-[:INTERESTED_IN]->(i:Concept)
        RETURN u, collect(DISTINCT s.name) as skills, collect(DISTINCT i.name) as interests
        """
        result = session.run(query, uid=user_id).single()
        
        if not result:
            raise HTTPException(status_code=404, detail="Student not found")
            
        user_data = dict(result["u"])
        user_data["skills"] = result["skills"]
        user_data["interests"] = result["interests"]

        # Fetch Projects
        proj_query = """
        MATCH (u:User {user_id: $uid})-[:WORKED_ON]->(w:Work {type: 'Student Project'})
        RETURN w.title as title, w.description as description, w.from_date as from_date, 
               w.to_date as to_date, w.tools as tools
        """
        projects = [dict(record) for record in session.run(proj_query, uid=user_id)]

        # Fetch Publications
        pub_query = """
        MATCH (u:User {user_id: $uid})-[:PUBLISHED]->(w:Work {type: 'Publication'})
        RETURN w.title as title, w.year as year, w.publisher as publisher, w.link as link
        """
        publications = [dict(record) for record in session.run(pub_query, uid=user_id)]
        
        return {**user_data, "projects": projects, "publications": publications}
    finally:
        session.close()

# --- C. UPDATE Student Profile ---
@router.put("/student/profile")
def update_student_profile(
    data: StudentProfileUpdate,
    current_user: dict = Depends(get_current_user),
):
    if current_user["role"].lower() != "student":
        raise HTTPException(status_code=403, detail="Access denied")

    user_id = current_user["user_id"]
    session = db.get_session()

    try:
        projects_data = [p.dict() for p in data.projects]
        publications_data = [p.dict() for p in data.publications]

        query = """
        MATCH (u:User {user_id: $user_id})
        
        // 1. Update Basic Info
        SET u.name = COALESCE($name, u.name),
            u.profile_picture = $profile_picture,
            u.phone = $phone,
            u.department = $dept,
            u.batch = $batch,
            u.bio = $bio

        // 2. Clean Old Relations
        WITH u
        OPTIONAL MATCH (u)-[r:HAS_SKILL|INTERESTED_IN]->() DELETE r
        WITH u
        OPTIONAL MATCH (u)-[:WORKED_ON]->(oldP:Work {type: 'Student Project'}) DETACH DELETE oldP
        WITH u
        OPTIONAL MATCH (u)-[:PUBLISHED]->(oldPub:Work {type: 'Publication'}) DETACH DELETE oldPub

        // 3. Add Skills & Interests
        WITH u
        FOREACH (skill IN $skills | MERGE (s:Concept {name: toLower(skill)}) MERGE (u)-[:HAS_SKILL]->(s))
        FOREACH (interest IN $interests | MERGE (i:Concept {name: toLower(interest)}) MERGE (u)-[:INTERESTED_IN]->(i))
        
        // 4. Add Projects
        WITH u
        FOREACH (proj IN $projects |
            CREATE (w:Work {
                id: apoc.create.uuid(),
                title: proj.title, from_date: proj.from_date, to_date: proj.to_date,
                description: proj.description, tools: proj.tools,
                type: "Student Project", created_at: datetime()
            })
            CREATE (u)-[:WORKED_ON]->(w)
        )

        // 5. Add Publications
        WITH u
        FOREACH (pub IN $publications |
            CREATE (w:Work {
                id: apoc.create.uuid(),
                title: pub.title, year: pub.year, publisher: pub.publisher, link: pub.link,
                type: "Publication", created_at: datetime()
            })
            CREATE (u)-[:PUBLISHED]->(w)
        )
        
        RETURN u.user_id
        """

        session.run(
            query,
            user_id=user_id,
            name=data.name,
            profile_picture=data.profile_picture,
            phone=data.phone,
            dept=data.department,
            batch=data.batch,
            bio=data.bio,
            skills=data.skills,
            interests=data.interests,
            projects=projects_data,
            publications=publications_data
        )
        return {"message": "Profile updated successfully"}
    except Exception as e:
        print(f"Update Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()

# --- D. Faculty Update ---
@router.put("/faculty/profile")
def update_faculty_profile(profile_data: FacultyProfileUpdate, current_user: dict = Depends(get_current_user)):
    # ... (Keep your working Faculty code here) ...
    # For brevity, reusing the logic you already have working
    if current_user["role"].lower() != "faculty":
        raise HTTPException(status_code=403, detail="Access denied")
    session = db.get_session()
    user_id = current_user["user_id"]
    try:
        session.run("MATCH (f:User {user_id: $uid})-[r:WORKED_ON|PUBLISHED|LED_PROJECT]->(w:Work) DETACH DELETE w", uid=user_id)
        # (Insert full faculty query here)
        return {"status": "success"}
    finally:
        session.close()