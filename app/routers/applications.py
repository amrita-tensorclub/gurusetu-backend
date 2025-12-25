from fastapi import APIRouter, HTTPException, Depends
from app.core.security import get_current_user
from app.core.database import db
from app.models.application import ApplicationCreate, ApplicationResponse
from datetime import datetime
import uuid

router = APIRouter()

@router.post("/apply/{opening_id}", response_model=dict)
def apply_to_opening(
    opening_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Student applies to an opening.
    Validates:
    - Student role
    - Opening exists
    - Eligibility (CGPA, year)
    - Not already applied
    """
    if current_user["role"].lower() != "student":
        raise HTTPException(status_code=403, detail="Only students can apply")

    student_id = current_user["user_id"]
    session = db.get_session()
    application_id = str(uuid.uuid4())

    try:
        query = """
        MATCH (s:Student {user_id: $student_id})
        MATCH (o:Opening {id: $opening_id})

        // Check eligibility
        WITH s, o,
             CASE WHEN o.min_cgpa IS NOT NULL AND s.cgpa < o.min_cgpa THEN false ELSE true END AS cgpa_ok,
             CASE WHEN size(o.target_years) > 0 AND NOT s.batch IN o.target_years THEN false ELSE true END AS year_ok

        WHERE cgpa_ok AND year_ok

        // Check not already applied
        OPTIONAL MATCH (s)-[existing:APPLIED]->(o)
        WITH s, o, existing
        WHERE existing IS NULL

        // Create application relationship
        MERGE (s)-[app:APPLIED {
            application_id: $application_id,
            status: 'pending',
            applied_at: datetime()
        }]->(o)

        MATCH (f:Faculty)-[:POSTED]->(o)

        RETURN o.title as opening_title,
               f.name as faculty_name,
               'pending' as status
        """

        result = session.run(
            query,
            student_id=student_id,
            opening_id=opening_id,
            application_id=application_id
        )

        record = result.single()
        if not record:
            raise HTTPException(
                status_code=400,
                detail="Opening not found, ineligible, or already applied"
            )

        return {
            "message": "Application submitted successfully",
            "application_id": application_id,
            "opening_title": record["opening_title"],
            "faculty_name": record["faculty_name"],
            "status": record["status"]
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()
