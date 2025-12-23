from fastapi import APIRouter, HTTPException
from app.models.user import StudentProfileUpdate, FacultyProfileUpdate
from app.core.database import db

router = APIRouter()

@router.put("/student/profile")
def update_student_profile(data: StudentProfileUpdate):
    session = db.get_session()
    try:
        # 1. Update text fields
        # 2. Clear old relationships to avoid duplicates
        # 3. Add Skills (HAS_SKILL) and Interests (INTERESTED_IN)
        query = """
        MATCH (u:User {user_id: $user_id})
        SET u.phone = $phone,
            u.department = $dept,
            u.batch = $batch,
            u.bio = $bio

        WITH u
        OPTIONAL MATCH (u)-[r:HAS_SKILL|INTERESTED_IN]->()
        DELETE r

        WITH u
        UNWIND $skills as skill
        MERGE (s:Concept {name: toLower(skill)})
        MERGE (u)-[:HAS_SKILL]->(s)

        WITH u
        UNWIND $interests as interest
        MERGE (i:Concept {name: toLower(interest)})
        MERGE (u)-[:INTERESTED_IN]->(i)
        """
        
        session.run(query, 
            user_id=data.user_id,
            phone=data.phone,
            dept=data.department,
            batch=data.batch,
            bio=data.bio,
            skills=data.skills,
            interests=data.interests
        )
        return {"message": "Student profile updated successfully!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()

@router.put("/faculty/profile")
def update_faculty_profile(data: FacultyProfileUpdate):
    session = db.get_session()
    try:
        query = """
        MATCH (u:User {user_id: $user_id})
        SET u.phone = $phone,
            u.department = $dept,
            u.bio = $bio,
            u.designation = $designation,
            u.office_hours = $office_hours,
            u.cabin_block = $cabin_block,
            u.cabin_floor = $cabin_floor,
            u.cabin_number = $cabin_number,
            u.qualifications = $qualifications
        """
        session.run(query,
            user_id=data.user_id,
            phone=data.phone,
            dept=data.department,
            bio=data.bio,
            designation=data.designation,
            office_hours=data.office_hours,
            cabin_block=data.cabin_block,
            cabin_floor=data.cabin_floor,
            cabin_number=data.cabin_number,
            qualifications=data.qualifications
        )
        return {"message": "Faculty profile updated successfully!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()