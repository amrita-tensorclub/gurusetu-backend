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
    profile_data: FacultyProfileUpdate, 
    current_user: dict = Depends(get_current_user)
):
    if current_user["role"].lower() != "faculty":
        raise HTTPException(status_code=403, detail="Access denied")

    session = db.get_session()
    user_id = current_user["user_id"]

    try:
        # Convert Pydantic models to dicts
        work_data = [w.dict() for w in profile_data.previous_work]

        query = """
        MATCH (f:Faculty {user_id: $uid})
        
        // 1. Update Basic Fields
        SET f.name = COALESCE($name, f.name),
            f.phone = COALESCE($phone, f.phone),
            f.designation = COALESCE($designation, f.designation),
            f.department = COALESCE($dept, f.department),
            f.office_hours = COALESCE($oh, f.office_hours),
            f.cabin_block = COALESCE($cb, f.cabin_block),
            f.cabin_floor = COALESCE($cf, f.cabin_floor),
            f.cabin_number = COALESCE($cn, f.cabin_number),
            f.ug_details = $ug,
            f.pg_details = $pg,
            f.phd_details = $phd

        // 2. Update Domain Interests (Delete old -> Add new)
        WITH f
        OPTIONAL MATCH (f)-[r:INTERESTED_IN]->()
        DELETE r
        
        WITH f
        FOREACH (domain IN $domains | 
            MERGE (c:Concept {name: toLower(domain)})
            MERGE (f)-[:INTERESTED_IN]->(c)
        )

        // 3. FIX DUPLICATION: Aggressively delete ALL previous work relations
        // We look for WORKED_ON, PUBLISHED, or LED_PROJECT to catch everything.
        WITH f
        OPTIONAL MATCH (f)-[r:WORKED_ON|PUBLISHED|LED_PROJECT]->(oldW:Work)
        DETACH DELETE oldW

        // 4. Create New Work Nodes
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
            works=work_data
        )
        
        return {"status": "success", "message": "Research profile updated successfully"}
    except Exception as e:
        print(f"Error updating profile: {str(e)}") # Debug log
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()