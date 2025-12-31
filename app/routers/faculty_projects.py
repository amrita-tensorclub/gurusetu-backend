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

@router.get("/my-projects")
def get_my_projects(current_user: dict = Depends(get_current_user)):
    """
    Fetches Openings with APPLICANT count and SHORTLISTED count.
    """
    if current_user["role"].lower() != "faculty":
        raise HTTPException(status_code=403, detail="Access denied")

    user_id = current_user["user_id"]
    session = db.get_session()

    try:
        # UPDATED QUERY: Counts both Applicants and Shortlisted
        query = """
        MATCH (f:Faculty {user_id: $uid})-[:POSTED]->(o:Opening)
        
        // Count Applicants (INTERESTED_IN)
        OPTIONAL MATCH (s:Student)-[:INTERESTED_IN]->(o)
        WITH f, o, count(s) as applicant_count

        // Count Shortlisted (SHORTLISTED)
        OPTIONAL MATCH (o)-[:SHORTLISTED]->(s_short:Student)
        WITH f, o, applicant_count, count(s_short) as shortlisted_count

        // Get Domains
        OPTIONAL MATCH (o)-[:REQUIRES]->(c:Concept)
        WITH f, o, applicant_count, shortlisted_count, collect(c.name) as domains

        RETURN o.id as id, 
               o.title as title, 
               o.created_at as posted_date,
               o.status as status, 
               domains,
               applicant_count,
               shortlisted_count
        ORDER BY o.created_at DESC
        """

        results = session.run(query, uid=user_id)
        
        projects = []
        stats = {
            "active_projects": 0,
            "total_applicants": 0,
            "total_shortlisted": 0
        }

        for r in results:
            status = r["status"] if r["status"] else "Active"
            domain_label = r["domains"][0] if r["domains"] else "General"

            projects.append({
                "id": r["id"],
                "title": r["title"],
                "status": status,
                "domain": domain_label,
                "posted_date": r["posted_date"].isoformat().split('T')[0] if r["posted_date"] else "N/A",
                "applicant_count": r["applicant_count"],
                "shortlisted_count": r["shortlisted_count"] # <--- Added this
            })

            if status == "Active":
                stats["active_projects"] += 1
            stats["total_applicants"] += r["applicant_count"]
            stats["total_shortlisted"] += r["shortlisted_count"]

        return {
            "stats": stats,
            "projects": projects
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


# @router.get("/my-projects/{project_id}/applicants")
# def get_project_applicants(project_id: str, current_user: dict = Depends(get_current_user)):
#     """ Get students who expressed interest """
#     if current_user["role"].lower() != "faculty":
#         raise HTTPException(status_code=403, detail="Access denied")

#     session = db.get_session()
#     try:
#         query = """
#         MATCH (o:Opening {id: $pid})
#         MATCH (s:Student)-[r:INTERESTED_IN]->(o)
#         RETURN s.user_id as id, s.name as name, s.roll_no as roll_no, 
#                s.department as dept, s.profile_picture as pic
#         ORDER BY r.date DESC
#         """
#         results = session.run(query, pid=project_id)
#         return [{"student_id": r["id"], "name": r["name"], "roll_no": r["roll_no"], 
#                  "department": r["dept"], "profile_picture": r["pic"]} for r in results]
#     finally:
#         session.close()


@router.get("/my-projects/{project_id}/shortlisted")
def get_project_shortlisted(project_id: str, current_user: dict = Depends(get_current_user)):
    """ Get students who have been shortlisted """
    if current_user["role"].lower() != "faculty":
        raise HTTPException(status_code=403, detail="Access denied")

    session = db.get_session()
    try:
        # Query looks for the SHORTLISTED relationship
        query = """
        MATCH (o:Opening {id: $pid})-[r:SHORTLISTED]->(s:Student)
        RETURN s.user_id as id, s.name as name, s.roll_no as roll_no, 
               s.department as dept, s.profile_picture as pic
        """
        results = session.run(query, pid=project_id)
        return [{"student_id": r["id"], "name": r["name"], "roll_no": r["roll_no"], 
                 "department": r["dept"], "profile_picture": r["pic"]} for r in results]
    finally:
        session.close()


@router.get("/my-projects/{project_id}/applicants")
def get_project_applicants(project_id: str, current_user: dict = Depends(get_current_user)):
    """
    Fetches the list of students who applied to a specific project.
    """
    if current_user["role"].lower() != "faculty":
        raise HTTPException(status_code=403, detail="Access denied")

    session = db.get_session()

    try:
        query = """
        MATCH (o:Opening {id: $pid})
        MATCH (s:Student)-[r:INTERESTED_IN]->(o)
        RETURN s.user_id as id, 
               s.name as name, 
               s.roll_no as roll_no, 
               s.department as dept, 
               s.profile_picture as pic,
               r.date as applied_date
        ORDER BY r.date DESC
        """
        
        results = session.run(query, pid=project_id)
        applicants = []
        
        for r in results:
            applicants.append({
                "student_id": r["id"],
                "name": r["name"],
                "roll_no": r["roll_no"],
                "department": r["dept"],
                "profile_picture": r["pic"],
                "applied_date": r["applied_date"].isoformat().split('T')[0] if r["applied_date"] else "Recent"
            })
            
        return applicants

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()
