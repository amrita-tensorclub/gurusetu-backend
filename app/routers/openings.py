from fastapi import APIRouter, HTTPException, Depends
from app.models.openings import OpeningCreate
from app.core.database import db
import uuid

router = APIRouter()

@router.post("/")
def create_opening(opening: OpeningCreate):
    session = db.get_session()
    opening_id = str(uuid.uuid4())
    
    try:
        query = """
        MATCH (f:User {user_id: $faculty_id})
        
        CREATE (o:Opening {
            id: $opening_id,
            title: $title,
            description: $description,
            expected_duration: $expected_duration,  // Added
            target_years: $target_years,            // Added
            min_cgpa: $min_cgpa,                    // Added
            deadline: $deadline,                    // Added
            created_at: datetime()
        })
        
        MERGE (f)-[:POSTED]->(o)
        
        WITH o
        UNWIND $skills as skill_name
        MERGE (c:Concept {name: toLower(skill_name)})
        MERGE (o)-[:REQUIRES]->(c)
        
        RETURN o.id as id
        """
        
        session.run(query, 
            faculty_id=opening.faculty_id,
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