from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from pydantic import BaseModel
from typing import List, Optional
from app.core.database import db
from app.core.security import get_current_user
import shutil
import uuid
import os
import json 
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
    outcome: Optional[str] = None
    collaborators: Optional[str] = None

class ProjectCreate(BaseModel):
    title: str
    description: str
    duration: Optional[str] = "" 
    from_date: Optional[str] = ""
    to_date: Optional[str] = ""
    tools: List[str] = []

class PublicationItem(BaseModel):
    title: str
    year: str
    publisher: Optional[str] = ""
    link: Optional[str] = ""

# --- Student Profile Model ---
class StudentProfileUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    department: Optional[str] = None
    batch: Optional[str] = None
    bio: Optional[str] = None
    profile_picture: Optional[str] = None
    
    skills: List[str] = []
    interests: List[str] = []
    projects: List[ProjectCreate] = []
    publications: List[PublicationItem] = [] 

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
    
    current_status: Optional[str] = None  
    status_source: Optional[str] = None   

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
        # Ensure this matches your actual server URL or localhost
        return {"url": f"http://127.0.0.1:8000/uploads/{unique_filename}"}
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
               w.to_date as to_date, w.tools as tools, w.duration as duration
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
                id: randomUUID(),
                title: proj.title, from_date: proj.from_date, to_date: proj.to_date,
                description: proj.description, tools: proj.tools, duration: proj.duration,
                type: "Student Project", created_at: datetime()
            })
            CREATE (u)-[:WORKED_ON]->(w)
        )

        // 5. Add Publications
        WITH u
        FOREACH (pub IN $publications |
            CREATE (w:Work {
                id: randomUUID(),
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

# --- ADDED: Get All Faculty List (Supports Map & Status) ---
@router.get("/faculty")
def get_all_faculty(search: Optional[str] = None, department: Optional[str] = None):
    session = db.get_session()
    try:
        # Fetch Faculty Nodes with Map Status
        query = """
        MATCH (f:Faculty)
        OPTIONAL MATCH (f)-[:LOCATED_AT]->(c:Cabin)
        WHERE ($search IS NULL OR toLower(f.name) CONTAINS toLower($search))
        AND ($dept IS NULL OR f.department = $dept)
        
        RETURN f.user_id as id, 
               f.name as name, 
               f.department as department, 
               f.designation as designation, 
               f.profile_picture as profile_picture,
               f.current_status as status, 
               f.status_source as status_source,
               c.code as cabin_number,
               c.coordinates as coordinates
        """
        
        result = session.run(query, search=search, dept=department)
        faculty_list = []
        
        for record in result:
            data = dict(record)
            # Safe JSON parse for coords
            if data['coordinates']:
                try:
                    data['coordinates'] = json.loads(data['coordinates'])
                except:
                    data['coordinates'] = None
            
            # Default fallback for status
            if not data['status']:
                data['status'] = 'Available'
                data['status_source'] = 'System'

            faculty_list.append(data)
                
        return faculty_list
    finally:
        session.close()

# --- D. Faculty Update (FIXED WITH MAP LOGIC) ---
@router.put("/faculty/profile")
def update_faculty_profile(
    data: FacultyProfileUpdate, 
    current_user: dict = Depends(get_current_user)
):
    if current_user["role"].lower() != "faculty":
        raise HTTPException(status_code=403, detail="Access denied")

    user_id = current_user["user_id"]
    session = db.get_session()

    try:
        work_data = [w.dict() for w in data.previous_work]

        # 1. Update Basic Text & Details
        query = """
        MATCH (f:User {user_id: $user_id})

        SET f.name = COALESCE($name, f.name),
            f.profile_picture = $profile_picture,
            f.email = $email,
            f.phone = $phone,
            f.designation = $designation,
            f.department = $dept,
            f.office_hours = $office_hours,
            f.cabin_block = $cabin_block,
            f.cabin_floor = $cabin_floor,
            f.cabin_number = $cabin_number,
            f.ug_details = $ug_details,
            f.pg_details = $pg_details,
            f.phd_details = $phd_details

        // Clear and Recreate Domain Interests
        WITH f
        OPTIONAL MATCH (f)-[r:INTERESTED_IN]->() DELETE r
        
        // Clear and Recreate Work
        WITH f
        OPTIONAL MATCH (f)-[:WORKED_ON]->(w:Work) DETACH DELETE w

        // Add Domains
        WITH f
        FOREACH (dom IN $domain_interests | 
            MERGE (c:Concept {name: toLower(dom)}) 
            MERGE (f)-[:INTERESTED_IN]->(c)
        )

        // Add Work
        WITH f
        FOREACH (item IN $previous_work |
            CREATE (w:Work {
                id: randomUUID(),
                title: item.title,
                type: item.type,
                year: item.year,
                outcome: item.outcome,
                collaborators: item.collaborators,
                created_at: datetime()
            })
            CREATE (f)-[:WORKED_ON]->(w)
        )

        RETURN f.user_id
        """

        session.run(
            query,
            user_id=user_id,
            name=data.name,
            profile_picture=data.profile_picture,
            email=data.email,
            phone=data.phone,
            designation=data.designation,
            dept=data.department,
            office_hours=data.office_hours,
            cabin_block=data.cabin_block,
            cabin_floor=data.cabin_floor,
            cabin_number=data.cabin_number,
            ug_details=data.ug_details,
            pg_details=data.pg_details,
            phd_details=data.phd_details,
            domain_interests=data.domain_interests,
            previous_work=work_data
        )

        # 2. CRITICAL: Update Map Relationship (The "Req")
        # This moves the pin on the map when you save the profile
        if data.cabin_number:
            map_query = """
            MATCH (f:Faculty {user_id: $uid})
            
            // Remove old map link
            OPTIONAL MATCH (f)-[r:LOCATED_AT]->(:Cabin)
            DELETE r
            
            // Find new cabin by code and link it
            WITH f
            MATCH (c:Cabin {code: $code})
            MERGE (f)-[:LOCATED_AT]->(c)
            """
            session.run(map_query, uid=user_id, code=data.cabin_number)

        return {"message": "Faculty profile updated successfully"}

    except Exception as e:
        print(f"Faculty Update Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()