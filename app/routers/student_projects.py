from fastapi import APIRouter, HTTPException, Depends
from app.core.security import get_current_user 
from app.models.project import StudentWorkCreate
from app.core.database import db
import uuid

router = APIRouter()

@router.post("/")
def add_student_project(
    work: StudentWorkCreate,
    current_user: dict = Depends(get_current_user)
):
    # 1. STRICT AUTHORIZATION: Only Students allowed
    if current_user["role"].lower() != "student":
        raise HTTPException(
            status_code=403, 
            detail="Only students can add to student portfolios"
        )

    # 2. OVERRIDE USER_ID: Security best practice
    # We ignore the user_id sent in JSON and use the secure Token ID instead.
    secure_user_id = current_user["user_id"]
    
    session = db.get_session()
    work_id = str(uuid.uuid4())

    try:
        additional_label = "Publication" if work.type.lower() == "publication" else "Project"
        rel_type = "AUTHORED" if work.type.lower() == "publication" else "COMPLETED"

        query = f"""
        MATCH (u:User {{user_id: $user_id}})

        CREATE (w:Work:{additional_label} {{
            id: $work_id,
            title: $title,
            description: $description,
            start_date: $start_date,
            end_date: $end_date,
            year: $year,
            collaborators: $collaborators,
            outcome: $outcome,
            type: $type
        }})

        MERGE (u)-[:{rel_type}]->(w)

        WITH w
        UNWIND $tools as tool_name
        MERGE (c:Concept {{name: toLower(tool_name)}})
        MERGE (w)-[:USED_TECH]->(c)
        """

        session.run(query,
            user_id=secure_user_id,  # <--- Using Secure ID
            work_id=work_id,
            title=work.title,
            description=work.description,
            start_date=work.start_date,
            end_date=work.end_date,
            year=work.year,
            collaborators=work.collaborators,
            outcome=work.outcome,
            type=work.type,
            tools=work.tools_used
        )
        return {"message": "Project added to student portfolio!", "id": work_id}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()