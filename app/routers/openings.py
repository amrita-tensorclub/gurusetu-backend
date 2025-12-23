from fastapi import APIRouter, HTTPException
from app.models.openings import OpeningCreate
from app.core.database import db
import uuid

router = APIRouter()

@router.post("/")
def create_opening(opening: OpeningCreate):
    session = db.get_session()
    opening_id = str(uuid.uuid4())
    
    try:
        # 1. Match Faculty
        # 2. Create Opening Node
        # 3. Link Faculty -> Opening
        # 4. Link Opening -> Skills (Concepts)
        query = """
        MATCH (f:User:Faculty {user_id: $faculty_id})
         
         # 4. Link Opening -> Skills (Concepts)
         query = """
         MATCH (f:User:Faculty {user_id: $faculty_id})
         
         CREATE (o:Opening {
            id: $opening_id,
            title: $title,
            description: $description,
            created_at: datetime()
        })
        
        MERGE (f)-[:POSTED]->(o)
        
        WITH o
        UNWIND $skills as skill_name
        MERGE (c:Concept {name: toLower(skill_name)})
        MERGE (o)-[:REQUIRES]->(c)
        
        RETURN o.id as id
        """
        
        result = session.run(query, 
            faculty_id=opening.faculty_id,
            opening_id=opening_id,
            title=opening.title,
            description=opening.description,
            skills=opening.required_skills
        )
        
        if result.peek() is None:
            raise HTTPException(status_code=404, detail="Faculty not found")

        return {"message": "Opening created and linked to Graph!", "opening_id": opening_id}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()