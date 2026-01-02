from fastapi import APIRouter, HTTPException, Depends
from app.models.openings import OpeningCreate
from app.core.database import db
from app.core.security import get_current_user
import uuid

router = APIRouter(tags=["Openings"])

@router.post("/")
def create_opening(
    opening: OpeningCreate,
    current_user: dict = Depends(get_current_user)
):
    if current_user["role"].lower() != "faculty":
        raise HTTPException(status_code=403, detail="Access denied")

    faculty_id = current_user["user_id"]
    session = db.get_session()
    opening_id = str(uuid.uuid4())

    try:
        # UPDATED QUERY: Saves 'collaboration_type' to the Opening node
        query = """
        MATCH (f:User {user_id: $faculty_id})

        CREATE (o:Opening {
            id: $opening_id,
            title: $title,
            description: $description,
            expected_duration: $expected_duration,
            target_years: $target_years,
            min_cgpa: $min_cgpa,
            deadline: $deadline,
            collaboration_type: $collab_type,  // <--- SAVING TO DB
            status: 'Active',
            created_at: datetime()
        })

        MERGE (f)-[:POSTED]->(o)

        WITH o
        UNWIND $skills AS skill_name
        MERGE (c:Concept {name: toLower(skill_name)})
        MERGE (o)-[:REQUIRES]->(c)

        RETURN o.id AS id
        """

        session.run(
            query,
            faculty_id=faculty_id,
            opening_id=opening_id,
            title=opening.title,
            description=opening.description,
            skills=opening.required_skills,
            expected_duration=opening.expected_duration,
            target_years=opening.target_years,
            min_cgpa=opening.min_cgpa,
            deadline=str(opening.deadline),
            collab_type=opening.collaboration_type  # <--- PASSING THE VALUE
        )

        return {"message": "Opening created!", "opening_id": opening_id}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()

# --- ADD DELETE ENDPOINT TO FIX DELETION ISSUE ---
@router.delete("/{opening_id}")
def delete_opening(opening_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"].lower() != "faculty":
        raise HTTPException(status_code=403, detail="Access denied")

    session = db.get_session()
    try:
        query = """
        MATCH (f:User {user_id: $uid})-[:POSTED]->(o:Opening {id: $oid})
        DETACH DELETE o
        RETURN count(o) as deleted
        """
        result = session.run(query, uid=current_user["user_id"], oid=opening_id).single()
        
        if not result or result["deleted"] == 0:
            raise HTTPException(status_code=404, detail="Opening not found")
            
        return {"message": "Deleted successfully"}
    finally:
        session.close()