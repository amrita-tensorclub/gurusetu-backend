from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from app.core.database import db
from app.core.security import get_current_user
from datetime import datetime, date
import uuid
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# --- Model for Status Update ---


class ApplicationStatusUpdate(BaseModel):
    opening_id: str
    student_id: str
    status: str  # "Shortlisted" or "Rejected"


@router.delete("/withdraw/{opening_id}")
def withdraw_application(opening_id: str, current_user: dict = Depends(get_current_user)):
    """Withdraw a pending application. Only pending applications can be withdrawn."""
    if current_user["role"].lower() != "student":
        raise HTTPException(
            status_code=403, detail="Only students can withdraw applications")

    user_id = current_user["user_id"]
    session = db.get_session()

    try:
        # Check if application exists and is pending
        check_query = """
        MATCH (u:User {user_id: $uid})-[r:APPLIED_TO]->(o:Opening {id: $oid})
        RETURN r.status AS status
        """
        result = session.run(check_query, uid=user_id, oid=opening_id).single()

        if not result:
            raise HTTPException(
                status_code=404, detail="Application not found")

        if result["status"].lower() != "pending":
            raise HTTPException(
                status_code=400,
                detail=f"Cannot withdraw application with status '{result['status']}'"
            )

        # Delete the application relationship
        withdraw_query = """
        MATCH (u:User {user_id: $uid})-[r:APPLIED_TO]->(o:Opening {id: $oid})
        DELETE r
        RETURN o.title AS title
        """
        delete_result = session.run(
            withdraw_query, uid=user_id, oid=opening_id).single()

        return {"message": f"Application for '{delete_result['title']}' withdrawn successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Withdraw error: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to withdraw application")
    finally:
        session.close()


@router.post("/apply/{opening_id}")
def apply_to_opening(opening_id: str, current_user: dict = Depends(get_current_user)):
    # 1. Check Role
    if current_user["role"].lower() != "student":
        raise HTTPException(status_code=403, detail="Only students can apply")

    user_id = current_user["user_id"]
    session = db.get_session()

    try:
        # 2. Check if Opening Exists & Get Faculty ID + Deadline
        check_query = """
        MATCH (f:User)-[:POSTED]->(o) 
        WHERE o.id = $oid
        RETURN o, f, o.deadline AS deadline, o.status AS status
        """
        result = session.run(check_query, oid=opening_id).single()

        if not result or not result["o"]:
            raise HTTPException(status_code=404, detail="Opening not found")

        # 2b. Check if opening is closed
        if result["status"] and result["status"].lower() == "closed":
            raise HTTPException(
                status_code=400, detail="This opening is closed and no longer accepting applications")

        # 2c. Check deadline
        deadline = result["deadline"]
        if deadline:
            # Handle both date and datetime objects from Neo4j
            if hasattr(deadline, 'to_native'):
                deadline = deadline.to_native()
            if isinstance(deadline, datetime):
                deadline = deadline.date()
            if deadline < date.today():
                raise HTTPException(
                    status_code=400, detail="Application deadline has passed")

        # 3. Check if Already Applied
        exists_query = """
        MATCH (u:User {user_id: $uid})-[r:APPLIED_TO]->(o)
        WHERE o.id = $oid
        RETURN r
        """
        if session.run(exists_query, uid=user_id, oid=opening_id).single():
            raise HTTPException(
                status_code=400, detail="You have already applied to this project")

        # 4. Create Application & Notification
        # FIX 2: Changed [:HAS_NOTIFICATION] to [:NOTIFIES] and reversed direction
        # to match your dashboard.py fetch logic: MATCH (n)-[:NOTIFIES]->(u)
        apply_query = """
        MATCH (u:User {user_id: $uid})
        MATCH (f:User)-[:POSTED]->(o)
        WHERE o.id = $oid
        
        // A. Create Application
        CREATE (u)-[:APPLIED_TO {
            application_id: $app_id,
            applied_at: datetime(),
            status: 'Pending'
        }]->(o)
        
        // B. Create Notification for Faculty
        WITH u, o, f
        CREATE (n:Notification {
            id: $notif_id,
            message: u.name + " applied for " + o.title,
            type: "Application",
            is_read: false,
            created_at: datetime(),
            trigger_id: u.user_id,
            trigger_role: "student"
        })
        CREATE (n)-[:NOTIFIES]->(f)
        
        RETURN u.user_id
        """

        session.run(apply_query, uid=user_id, oid=opening_id,
                    app_id=str(uuid.uuid4()), notif_id=str(uuid.uuid4()))

        return {"message": "Application submitted successfully"}

    except Exception as e:
        print(f"Application Error: {e}")
        raise HTTPException(
            status_code=500, detail="Server error processing application")
    finally:
        session.close()


@router.put("/status")
def update_application_status(
    data: ApplicationStatusUpdate,
    current_user: dict = Depends(get_current_user)
):
    if current_user["role"].lower() != "faculty":
        raise HTTPException(status_code=403, detail="Access denied")

    session = db.get_session()
    try:
        # Logic: Update status, manage relations, and notify student
        cypher = """
        MATCH (o:Opening {id: $oid})
        MATCH (s:Student {user_id: $sid})
        MATCH (s)-[r:APPLIED_TO]->(o)
        
        // Update Status
        SET r.status = $status
        
        // Handle Logic based on status
        WITH o, s, r
        CALL apoc.do.case([
            $status = 'Shortlisted', 'MERGE (o)-[:SHORTLISTED]->(s) RETURN true',
            $status = 'Rejected',    'OPTIONAL MATCH (o)-[sl:SHORTLISTED]->(s) DELETE sl RETURN true'
        ], 'RETURN false', {o:o, s:s}) YIELD value

        // Notify Student
        // FIX 3: Ensure this uses [:NOTIFIES] as well
        WITH s, o
        CREATE (n:Notification {
            id: $notif_id,
            message: "Your application for " + o.title + " has been " + $status,
            type: "StatusUpdate",
            is_read: false,
            created_at: datetime(),
            trigger_id: o.id,
            trigger_role: "faculty"
        })
        CREATE (n)-[:NOTIFIES]->(s)
        
        RETURN s.user_id
        """

        session.run(
            cypher,
            oid=data.opening_id,
            sid=data.student_id,
            status=data.status,
            notif_id=str(uuid.uuid4())
        )

        return {"message": f"Applicant marked as {data.status}"}

    except Exception as e:
        print(f"Status Update Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to update status")
    finally:
        session.close()
