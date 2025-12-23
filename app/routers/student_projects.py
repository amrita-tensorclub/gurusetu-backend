from fastapi import APIRouter, HTTPException, Depends
from app.core.auth_utils import get_current_user
from app.models.project import StudentWorkCreate
from app.core.database import db
import uuid

router = APIRouter()

@router.post("/")
def add_student_work(
    work: StudentWorkCreate,
    current_user: dict = Depends(get_current_user)
):
    session = db.get_session()
    work_id = str(uuid.uuid4())

    # Validate user_id from token vs body
    if hasattr(work, "user_id") and work.user_id != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="user_id in body does not match authenticated user")

    try:
        # Graph Logic:
        # 1. Create a Node labeled :Work (and :Project or :Publication)
        # 2. Link Student -> [:AUTHORED|:COMPLETED] -> Work
        # 3. Link Work -> [:USED_TECH] -> Concepts (if tools provided)

        # Determine specific label based on type
        additional_label = "Publication" if work.type.lower() == "publication" else "Project"
        rel_type = "AUTHORED" if work.type.lower() == "publication" else "COMPLETED"

        query = f"""
        MATCH (u:User {{user_id: $user_id}})

        CREATE (w:Work:{additional_label} {{
            id: $work_id,
            title: $title,
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
            user_id=current_user["user_id"],
            work_id=work_id,
            title=work.title,
            year=work.year,
            collaborators=work.collaborators,
            outcome=work.outcome,
            type=work.type,
            tools=work.tools_used
        )
        return {"message": f"{work.type} added to portfolio!", "id": work_id}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()