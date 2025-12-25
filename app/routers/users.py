from fastapi import APIRouter, HTTPException, Depends
from app.core.database import db
from app.core.security import get_current_user
from app.models.user import StudentProfileUpdate, FacultyProfileUpdate

router = APIRouter()

@router.put("/student/profile")
def update_student_profile(
    data: StudentProfileUpdate,
    current_user: dict = Depends(get_current_user),
):
    if current_user["role"].lower() != "student":
        raise HTTPException(
            status_code=403,
            detail="Only students can update student profiles",
        )

    user_id = current_user["user_id"]
    session = db.get_session()

    try:
        # Convert Pydantic models to a list of dicts for Cypher
        projects_data = [p.dict() for p in data.projects]

        query = """
        MATCH (u:User {user_id: $user_id})
        SET u.name = COALESCE($name, u.name),
            u.profile_picture = COALESCE($profile_picture, u.profile_picture),
            u.phone = $phone,
            u.department = $dept,
            u.batch = $batch,
            u.bio = $bio

        // 1. Clear old Skills & Interests relationships
        WITH u
        OPTIONAL MATCH (u)-[r:HAS_SKILL|INTERESTED_IN]->()
        DELETE r

        // 2. Clear old Projects (Detach and delete the Work nodes created by this student)
        WITH u
        OPTIONAL MATCH (u)-[:WORKED_ON]->(oldW:Work)
        DETACH DELETE oldW

        // 3. Add New Skills
        WITH u
        FOREACH (skill IN $skills |
            MERGE (s:Concept {name: toLower(skill)})
            MERGE (u)-[:HAS_SKILL]->(s)
        )

        // 4. Add New Interests
        WITH u
        FOREACH (interest IN $interests |
            MERGE (i:Concept {name: toLower(interest)})
            MERGE (u)-[:INTERESTED_IN]->(i)
        )

        // 5. Add New Projects
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

        result = session.run(
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
            projects=projects_data  # Pass the list of dicts here
        ).single()

        if not result:
            raise HTTPException(status_code=404, detail="User not found")

        return {"message": "Student profile updated successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


@router.put("/faculty/profile")
def update_faculty_profile(
    data: FacultyProfileUpdate,
    current_user: dict = Depends(get_current_user),
):
    if current_user["role"].lower() != "faculty":
        raise HTTPException(
            status_code=403,
            detail="Only faculty can update faculty profiles",
        )

    user_id = current_user["user_id"]
    session = db.get_session()

    try:
        query = """
        MATCH (u:User {user_id: $user_id})
        SET u.name = COALESCE($name, u.name),
            u.profile_picture = COALESCE($profile_picture, u.profile_picture),
            u.phone = $phone,
            u.department = $dept,
            u.bio = $bio,
            u.designation = $designation,
            u.office_hours = $office_hours,
            u.cabin_block = $cabin_block,
            u.cabin_floor = $cabin_floor,
            u.cabin_number = $cabin_number,
            u.qualifications = $qualifications

        WITH u
        OPTIONAL MATCH (u)-[r:INTERESTED_IN]->()
        DELETE r

        WITH u
        FOREACH (interest IN $domain_interests |
            MERGE (i:Concept {name: toLower(interest)})
            MERGE (u)-[:INTERESTED_IN]->(i)
        )

        RETURN u.user_id AS user_id
        """

        result = session.run(
            query,
            user_id=user_id,
            name=data.name,
            profile_picture=data.profile_picture,
            phone=data.phone,
            dept=data.department,
            bio=data.bio,
            designation=data.designation,
            office_hours=data.office_hours,
            cabin_block=data.cabin_block,
            cabin_floor=data.cabin_floor,
            cabin_number=data.cabin_number,
            qualifications=data.qualifications,
            domain_interests=data.domain_interests,
        ).single()

        if not result:
            raise HTTPException(status_code=404, detail="User not found")

        return {"message": "Faculty profile updated successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()