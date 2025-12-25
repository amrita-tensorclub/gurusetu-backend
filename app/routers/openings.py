from fastapi import APIRouter, HTTPException, Depends
from app.models.openings import OpeningCreate
from app.core.database import db
import uuid

router = APIRouter()

@router.post("/")
@router.post("/")
def create_opening(
    opening: OpeningCreate,
    current_user: dict = Depends(get_current_user)
):
    if current_user["role"].lower() != "faculty":
        raise HTTPException(
            status_code=403,
            detail="Only faculty can create openings"
        )

    faculty_id = current_user["user_id"]
    session = db.get_session()
    opening_id = str(uuid.uuid4())

    try:
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
            deadline=opening.deadline
        )

        return {"message": "Opening created!", "opening_id": opening_id}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()
