from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from app.core.database import db
from app.core.security import get_current_user
from app.models.user import StudentProfileUpdate, FacultyProfileUpdate
import shutil
import uuid
from datetime import datetime

router = APIRouter()

# ---------------------------------------------------------
# 1. PROFILE PICTURE UPLOAD
# ---------------------------------------------------------
@router.post("/upload-profile-picture")
async def upload_profile_picture(file: UploadFile = File(...)):
    try:
        file_extension = file.filename.split(".")[-1]
        unique_filename = f"{uuid.uuid4()}.{file_extension}"
        file_path = f"uploads/{unique_filename}"
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        return {"url": f"http://localhost:8000/uploads/{unique_filename}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image upload failed: {str(e)}")

# ---------------------------------------------------------
# 2. STUDENT PROFILE UPDATE
# ---------------------------------------------------------
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

        query = """
        MATCH (u:User {user_id: $user_id})
        SET u.name = COALESCE($name, u.name),
            u.profile_picture = $profile_picture,
            u.phone = $phone,
            u.department = $dept,
            u.batch = $batch,
            u.bio = $bio

        // Clean Skills/Interests
        WITH u
        OPTIONAL MATCH (u)-[r:HAS_SKILL|INTERESTED_IN]->()
        DELETE r

        // Clean Old Projects
        WITH u
        OPTIONAL MATCH (u)-[:WORKED_ON]->(oldW:Work)
        DETACH DELETE oldW

        // Add New Data
        WITH u
        FOREACH (skill IN $skills | MERGE (s:Concept {name: toLower(skill)}) MERGE (u)-[:HAS_SKILL]->(s))
        FOREACH (interest IN $interests | MERGE (i:Concept {name: toLower(interest)}) MERGE (u)-[:INTERESTED_IN]->(i))
        
        WITH u
        FOREACH (proj IN $projects |
            CREATE (w:Work {
                title: proj.title,
                from_date: proj.from_date,
                to_date: proj.to_date,
                description: proj.description,
                tools: proj.tools,
                type: "Student Project"
            })
            CREATE (u)-[:WORKED_ON]->(w)
        )
        RETURN u.user_id AS user_id
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
            projects=projects_data
        )
        return {"message": "Student profile updated successfully"}
    finally:
        session.close()

# ---------------------------------------------------------
# 3. FACULTY PROFILE UPDATE (CRASH FIX)
# ---------------------------------------------------------
@router.put("/faculty/profile")
def update_faculty_profile(
    profile_data: FacultyProfileUpdate, 
    current_user: dict = Depends(get_current_user)
):
    if current_user["role"].lower() != "faculty":
        raise HTTPException(status_code=403, detail="Access denied")

    session = db.get_session()
    user_id = current_user["user_id"]

    # 1. Deduplicate Incoming Data
    unique_works = []
    seen_keys = set()
    for w in profile_data.previous_work:
        clean_title = w.title.strip()
        key = (clean_title.lower(), w.year)
        if key not in seen_keys and clean_title != "":
            unique_works.append(w.dict())
            seen_keys.add(key)
            
    print(f"Cleaned Data: Reduced {len(profile_data.previous_work)} items to {len(unique_works)} unique items.")

    try:
        # 2. EMERGENCY CLEANUP: Delete old duplicates in batches
        # This prevents the "ServiceUnavailable" timeout error
        cleanup_query = """
        MATCH (f:User {user_id: $uid})-[r:WORKED_ON|PUBLISHED|LED_PROJECT]->(w:Work)
        CALL {
            WITH w
            DETACH DELETE w
        } IN TRANSACTIONS OF 1000 ROWS
        """
        session.run(cleanup_query, uid=user_id)

        # 3. Update Profile & Add Fresh Data
        query = """
        MATCH (f:User {user_id: $uid})
        
        SET f.name = COALESCE($name, f.name),
            f.profile_picture = $pic,
            f.email = $email,
            f.phone = COALESCE($phone, f.phone),
            f.designation = COALESCE($designation, f.designation),
            f.department = COALESCE($dept, f.department),
            f.office_hours = COALESCE($oh, f.office_hours),
            f.cabin_block = $cb,
            f.cabin_floor = $cf,
            f.cabin_number = $cn,
            f.ug_details = $ug,
            f.pg_details = $pg,
            f.phd_details = $phd

        // Refresh Interests
        WITH f
        OPTIONAL MATCH (f)-[r:INTERESTED_IN]->()
        DELETE r
        WITH f
        FOREACH (domain IN $domains | 
            MERGE (c:Concept {name: toLower(domain)})
            MERGE (f)-[:INTERESTED_IN]->(c)
        )

        // Add Clean Work
        WITH f
        FOREACH (w IN $works | 
            CREATE (newW:Work {
                title: w.title,
                type: w.type,
                year: w.year,
                outcome: w.outcome,
                collaborators: w.collaborators,
                created_at: datetime()
            })
            CREATE (f)-[:WORKED_ON]->(newW)
        )

        RETURN f.user_id as id
        """

        session.run(query, 
            uid=user_id,
            name=profile_data.name,
            pic=profile_data.profile_picture,
            email=profile_data.email,
            phone=profile_data.phone,
            designation=profile_data.designation,
            dept=profile_data.department,
            oh=profile_data.office_hours,
            cb=profile_data.cabin_block,
            cf=profile_data.cabin_floor,
            cn=profile_data.cabin_number,
            ug=profile_data.ug_details,
            pg=profile_data.pg_details,
            phd=profile_data.phd_details,
            domains=profile_data.domain_interests,
            works=unique_works
        )
        
        return {"status": "success", "message": "Profile saved successfully"}
    except Exception as e:
        print(f"Error saving profile: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()