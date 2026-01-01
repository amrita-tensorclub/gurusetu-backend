from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
# We import models from the file you renamed to 'user.py' (singular)
from app.models.user import StudentProfileUpdate, FacultyProfileUpdate
from app.core.database import db
from app.core.security import get_current_user
import shutil
import uuid
import os
from datetime import datetime

router = APIRouter()

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
        # Update this IP if your network changes
        return {"url": f"http://10.169.201.42:8000/uploads/{unique_filename}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- B. GET Student Profile ---
@router.get("/student/profile/{user_id}")
def get_student_profile(user_id: str, current_user: dict = Depends(get_current_user)):
    session = db.get_session()
    try:
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
        RETURN w.title as title, w.description as description, 
               w.duration as duration, w.from_date as from_date, w.to_date as to_date, 
               w.tools as tools
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
        
        SET u.name = COALESCE($name, u.name),
            u.profile_picture = $profile_picture,
            u.phone = $phone,
            u.department = $dept,
            u.batch = $batch,
            u.bio = $bio

        WITH u
        OPTIONAL MATCH (u)-[r:HAS_SKILL|INTERESTED_IN]->() DELETE r
        WITH u
        OPTIONAL MATCH (u)-[:WORKED_ON]->(oldP:Work {type: 'Student Project'}) DETACH DELETE oldP
        WITH u
        OPTIONAL MATCH (u)-[:PUBLISHED]->(oldPub:Work {type: 'Publication'}) DETACH DELETE oldPub

        WITH u
        FOREACH (skill IN $skills | 
            MERGE (s:Concept {name: toLower(skill)}) 
            MERGE (u)-[:HAS_SKILL]->(s)
        )
        FOREACH (interest IN $interests | 
            MERGE (i:Concept {name: toLower(interest)}) 
            MERGE (u)-[:INTERESTED_IN]->(i)
        )
        
        WITH u
        FOREACH (proj IN $projects |
            CREATE (w:Work {
                id: randomUUID(),
                title: proj.title, 
                description: proj.description, 
                duration: proj.duration,
                from_date: proj.from_date, 
                to_date: proj.to_date,
                tools: proj.tools,
                type: "Student Project", 
                created_at: datetime()
            })
            CREATE (u)-[:WORKED_ON]->(w)
        )

        WITH u
        FOREACH (pub IN $publications |
            CREATE (w:Work {
                id: randomUUID(),
                title: pub.title, 
                year: pub.year, 
                publisher: pub.publisher, 
                link: pub.link,
                type: "Publication", 
                created_at: datetime()
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
        print(f"Student Update Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()

# --- D. UPDATE Faculty Profile ---
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

        WITH f
        OPTIONAL MATCH (f)-[r:INTERESTED_IN]->() DELETE r
        WITH f
        OPTIONAL MATCH (f)-[:WORKED_ON]->(w:Work) DETACH DELETE w

        WITH f
        FOREACH (dom IN $domain_interests | 
            MERGE (c:Concept {name: toLower(dom)}) 
            MERGE (f)-[:INTERESTED_IN]->(c)
        )

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

        return {"message": "Faculty profile updated successfully"}

    except Exception as e:
        print(f"Faculty Update Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()