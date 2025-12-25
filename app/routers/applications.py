from fastapi import APIRouter, HTTPException, Depends
from app.core.security import get_current_user
from app.core.database import db
from app.models.application import ApplicationCreate, ApplicationResponse, ApplicationStatusUpdate, ApplicantDetail
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


@router.get("/my-applications", response_model=list[ApplicationResponse])
def get_my_applications(
    current_user: dict = Depends(get_current_user)
):
    """Student views their submitted applications"""
    if current_user["role"].lower() != "student":
        raise HTTPException(status_code=403, detail="Only students can view applications")

    student_id = current_user["user_id"]
    session = db.get_session()

    try:
        query = """
        MATCH (s:Student {user_id: $student_id})-[app:APPLIED]->(o:Opening)
        MATCH (f:Faculty)-[:POSTED]->(o)

        // Calculate match score
        MATCH (o)-[:REQUIRES]->(req:Concept)
        WITH s, o, f, app, collect(id(req)) AS required_ids, count(req) AS total_req

        OPTIONAL MATCH (s)-[:HAS_SKILL]->(skill:Concept)
        WHERE id(skill) IN required_ids
        WITH s, o, f, app, total_req, count(skill) AS matched_count

        WITH s, o, f, app,
             CASE WHEN total_req = 0 THEN 0
                  ELSE round((toFloat(matched_count) / total_req) * 100, 0)
             END AS match_score

        RETURN app.application_id as application_id,
               o.id as opening_id,
               o.title as opening_title,
               f.name as faculty_name,
               app.status as status,
               toString(app.applied_at) as applied_at,
               match_score
        ORDER BY app.applied_at DESC
        """

        result = session.run(query, student_id=student_id)
        return [record.data() for record in result]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


@router.get("/opening/{opening_id}/applicants", response_model=list[ApplicantDetail])
def get_applicants_for_opening(
    opening_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Faculty views applicants for their opening"""
    if current_user["role"].lower() != "faculty":
        raise HTTPException(status_code=403, detail="Only faculty can view applicants")

    faculty_id = current_user["user_id"]
    session = db.get_session()

    try:
        query = """
        MATCH (f:Faculty {user_id: $faculty_id})-[:POSTED]->(o:Opening {id: $opening_id})
        MATCH (s:Student)-[app:APPLIED]->(o)

        // Calculate match score
        MATCH (o)-[:REQUIRES]->(req:Concept)
        WITH s, o, app, collect(id(req)) AS required_ids, collect(req.name) AS required_names, count(req) AS total_req

        OPTIONAL MATCH (s)-[:HAS_SKILL]->(skill:Concept)
        WHERE id(skill) IN required_ids
        WITH s, app, total_req, required_names, collect(skill.name) AS matched_names, count(skill) AS matched_count

        WITH s, app, required_names, matched_names,
             CASE WHEN total_req = 0 THEN 0
                  ELSE round((toFloat(matched_count) / total_req) * 100, 0)
             END AS match_score

        RETURN app.application_id as application_id,
               s.user_id as student_id,
               s.name as student_name,
               s.department as student_dept,
               s.batch as student_batch,
               s.cgpa as student_cgpa,
               s.profile_picture as student_pic,
               app.status as status,
               toString(app.applied_at) as applied_at,
               match_score,
               matched_names as matched_skills
        ORDER BY match_score DESC, app.applied_at DESC
        """

        result = session.run(query, faculty_id=faculty_id, opening_id=opening_id)
        return [record.data() for record in result]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


@router.put("/status/{application_id}")
def update_application_status(
    application_id: str,
    update: ApplicationStatusUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Faculty updates application status (accept/reject)"""
    if current_user["role"].lower() != "faculty":
        raise HTTPException(status_code=403, detail="Only faculty can update status")

    faculty_id = current_user["user_id"]
    session = db.get_session()

    try:
        query = """
        MATCH (f:Faculty {user_id: $faculty_id})-[:POSTED]->(o:Opening)
        MATCH (s:Student)-[app:APPLIED {application_id: $application_id}]->(o)

        SET app.status = $status,
            app.updated_at = datetime()

        RETURN s.name as student_name,
               o.title as opening_title,
               app.status as status
        """

        result = session.run(
            query,
            faculty_id=faculty_id,
            application_id=application_id,
            status=update.status
        )

        record = result.single()
        if not record:
            raise HTTPException(status_code=404, detail="Application not found or unauthorized")

        return {
            "message": f"Application {update.status}",
            "student_name": record["student_name"],
            "opening_title": record["opening_title"],
            "status": record["status"]
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


@router.delete("/withdraw/{opening_id}")
def withdraw_application(
    opening_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Student withdraws their application"""
    if current_user["role"].lower() != "student":
        raise HTTPException(status_code=403, detail="Only students can withdraw")

    student_id = current_user["user_id"]
    session = db.get_session()

    try:
        query = """
        MATCH (s:Student {user_id: $student_id})-[app:APPLIED]->(o:Opening {id: $opening_id})

        WITH app, o.title as opening_title
        DELETE app

        RETURN opening_title
        """

        result = session.run(query, student_id=student_id, opening_id=opening_id)
        record = result.single()

        if not record:
            raise HTTPException(status_code=404, detail="Application not found")

        return {
            "message": "Application withdrawn successfully",
            "opening_title": record["opening_title"]
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()
