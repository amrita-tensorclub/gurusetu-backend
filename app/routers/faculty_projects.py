from fastapi import APIRouter, HTTPException, Depends
from app.core.security import get_current_user
from app.models.project import StudentWorkCreate  # (Recommended rename later)
from app.core.database import db
import uuid

router = APIRouter()


@router.post("/")
def add_faculty_research(
    work: StudentWorkCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    Adds a faculty research work (Project or Publication) to the graph.
    """

    # -------------------------------------------------
    # 1. STRICT AUTHORIZATION
    # -------------------------------------------------
    if current_user["role"].lower() != "faculty":
        raise HTTPException(
            status_code=403,
            detail="Only faculty can add research works"
        )

    secure_user_id = current_user["user_id"]
    session = db.get_session()
    work_id = str(uuid.uuid4())

    # -------------------------------------------------
    # 2. STRICT TYPE VALIDATION (SECURITY FIX)
    # -------------------------------------------------
    work_type = work.type.lower()
    if work_type not in ["publication", "project"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid work type. Must be 'publication' or 'project'"
        )

    label = "Publication" if work_type == "publication" else "Project"
    rel_type = "PUBLISHED" if work_type == "publication" else "LED_PROJECT"

    # Ensure tools list is safe
    tools = work.tools_used or []

    try:
        # -------------------------------------------------
        # 3. DUPLICATE CHECK (PREVENT SAME TITLE RE-ENTRY)
        # -------------------------------------------------
        duplicate_query = """
        MATCH (u:User {user_id: $user_id})-[:PUBLISHED|LED_PROJECT]->(w:Work)
        WHERE toLower(w.title) = toLower($title)
        RETURN w LIMIT 1
        """
        duplicate = session.run(
            duplicate_query,
            user_id=secure_user_id,
            title=work.title
        ).single()

        if duplicate:
            raise HTTPException(
                status_code=409,
                detail="A research work with the same title already exists"
            )

        # -------------------------------------------------
        # 4. CREATE WORK + RELATIONSHIPS
        # -------------------------------------------------
        query = f"""
        MATCH (u:User {{user_id: $user_id}})

        CREATE (w:Work:{label} {{
            id: $work_id,
            title: $title,
            description: $description,
            start_date: $start_date,
            end_date: $end_date,
            year: $year,
            collaborators: $collaborators,
            outcome: $outcome,
            type: $type,
            collaboration_type: $collaboration_type,
            created_at: datetime()
        }})

        MERGE (u)-[:{rel_type}]->(w)

        WITH w
        UNWIND $tools AS tool_name
        MERGE (c:Concept {{name: toLower(tool_name)}})
        MERGE (w)-[:USED_TECH]->(c)
        """

        session.run(
            query,
            user_id=secure_user_id,
            work_id=work_id,
            title=work.title,
            description=work.description,
            start_date=work.start_date,
            end_date=work.end_date,
            year=work.year,
            collaborators=work.collaborators,
            outcome=work.outcome,
            type=work.type,
            collaboration_type=work.collaboration_type,
            tools=tools
        )

        return {
            "message": "Research added successfully to faculty profile",
            "work_id": work_id,
            "work_type": work_type
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to add research: {str(e)}"
        )

    finally:
        session.close()
