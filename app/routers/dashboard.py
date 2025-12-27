from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, List
from app.core.security import get_current_user
from app.core.database import db
import uuid
from datetime import datetime

# Optional: If you have the RAG service, keep this. 
# If not, the code below uses direct database queries as a fallback.
# from app.services.rag_service import recommend_students_for_faculty, recommend_openings_for_student

# --- FIX: Removed prefix="/dashboard" because it's already in main.py ---
router = APIRouter(tags=["Dashboard"]) 

# =========================================================
# HELPER FUNCTIONS
# =========================================================

def create_notification(tx, user_id, message, type="INFO", trigger_id=None, trigger_role=None):
    """
    Creates a notification node and links it to a user.
    """
    query = """
    MATCH (u:User {user_id: $user_id})
    CREATE (n:Notification {
        id: $nid,
        message: $message,
        type: $type,
        is_read: false,
        created_at: datetime(),
        trigger_id: $trigger_id,
        trigger_role: $trigger_role
    })
    CREATE (n)-[:NOTIFIES]->(u)
    """
    tx.run(query, 
           user_id=user_id, 
           nid=str(uuid.uuid4()), 
           message=message, 
           type=type,
           trigger_id=trigger_id,
           trigger_role=trigger_role
    )

# =========================================================
# 1. DASHBOARD HOME SCREENS
# =========================================================

@router.get("/faculty/home")
def get_faculty_home(current_user: dict = Depends(get_current_user)):
    """
    Faculty Dashboard Home: User Info, Recommended Students, Collab Preview
    """
    if current_user["role"].lower() != "faculty":
        raise HTTPException(status_code=403, detail="Access denied")

    session = db.get_session()
    user_id = current_user["user_id"]
    
    try:
        # A. User Info
        user_query = """
        MATCH (f:User {user_id: $uid, role: "faculty"})
        RETURN f.name as name, f.department as dept, f.profile_picture as pic
        """
        user_res = session.run(user_query, uid=user_id).single()
        
        user_info = {
            "name": user_res["name"] if user_res else current_user.get("name"),
            "department": user_res["dept"] if user_res else "General",
            "pic": user_res["pic"] if user_res else None
        }

        # B. Recommended Students (Graph-based matching)
        rec_query = """
        MATCH (f:User {user_id: $uid, role: "faculty"})
        OPTIONAL MATCH (f)-[:INTERESTED_IN]->(c:Concept)<-[:HAS_SKILL]-(s:Student)
        OPTIONAL MATCH (s)-[:HAS_SKILL]->(sk:Concept)
        WITH s, count(DISTINCT c) AS match_count, collect(DISTINCT sk.name)[0..3] AS skills
        WHERE s IS NOT NULL
        RETURN 
            s.user_id AS id,
            s.name AS name,
            s.department AS dept,
            s.batch AS batch,
            s.profile_picture AS pic,
            skills,
            match_count
        ORDER BY match_count DESC
        LIMIT 5
        """
        rec_results = session.run(rec_query, uid=user_id)
        
        recommended_students = []
        for r in rec_results:
            # Fetch top 3 skills for display
            skills_q = "MATCH (s:Student {user_id: $sid})-[:HAS_SKILL]->(k:Concept) RETURN k.name LIMIT 3"
            skills_res = session.run(skills_q, sid=r["id"])
            skills = [k["k.name"] for k in skills_res]

            recommended_students.append({
                "student_id": r["id"],
                "name": r["name"],
                "department": r["dept"],
                "batch": r["batch"],
                "profile_picture": r["pic"],
                "matched_skills": skills,
                "match_score": f"{min(99, 70 + (r['match_count'] * 5))}%" 
            })

        # C. Faculty Collaborations Preview
        collab_query = """
        MATCH (f:Faculty)-[:POSTED|LED_PROJECT]->(w:Work)
        WHERE f.user_id <> $uid AND w.collaboration_type IS NOT NULL
        RETURN f.user_id as fid, f.name as name, f.department as dept, f.profile_picture as pic,
               w.title as title, w.collaboration_type as type
        LIMIT 5
        """
        collab_results = session.run(collab_query, uid=user_id)
        
        collaborations = []
        for c in collab_results:
            collaborations.append({
                "faculty_id": c["fid"],
                "faculty_name": c["name"],
                "faculty_dept": c["dept"],
                "faculty_pic": c["pic"],
                "project_title": c["title"],
                "collaboration_type": c["type"]
            })

        return {
            "user_info": user_info,
            "recommended_students": recommended_students,
            "faculty_collaborations": collaborations
        }
    finally:
        session.close()


@router.get("/student/home")
def get_student_dashboard(current_user: dict = Depends(get_current_user)):
    """
    Student Dashboard Home: User Info, Recommended Openings, All Openings
    """
    if current_user["role"].lower() != "student":
        raise HTTPException(status_code=403, detail="Access denied")

    user_id = current_user["user_id"]
    session = db.get_session()
    
    try:
        # A. User Info
        user_query = "MATCH (u:User {user_id: $user_id}) RETURN u.name as name, u.roll_no as roll_no"
        user_res = session.run(user_query, user_id=user_id).single()
        
        user_info = {}
        if user_res:
            user_info = user_res.data()

        # B. Recommended Openings
        recs_query = """
        MATCH (s:Student {user_id: $uid})
        MATCH (o:Opening)-[:REQUIRES]->(c:Concept)<-[:HAS_SKILL]-(s)
        WITH o, count(c) as match_count
        MATCH (f:Faculty)-[:POSTED]->(o)
        RETURN o.id as oid, o.title as title, f.user_id as fid, f.name as fname, 
               f.department as fdept, f.profile_picture as fpic, match_count
        ORDER BY match_count DESC LIMIT 5
        """
        recs = session.run(recs_query, uid=user_id)
        
        recommended_openings = []
        for r in recs:
            # Get skills for opening
            skills_q = "MATCH (o:Opening {id: $oid})-[:REQUIRES]->(c:Concept) RETURN c.name"
            skills = [k["c.name"] for k in session.run(skills_q, oid=r["oid"])]

            recommended_openings.append({
                "opening_id": r["oid"],
                "title": r["title"],
                "faculty_id": r["fid"],
                "faculty_name": r["fname"],
                "department": r["fdept"],
                "faculty_pic": r["fpic"],
                "skills": skills[:3],
                "match_score": f"{min(99, 60 + (r['match_count'] * 10))}%"
            })

        # C. All Openings List
        all_query = """
        MATCH (f:Faculty)-[:POSTED]->(o:Opening)
        OPTIONAL MATCH (o)-[:REQUIRES]->(c:Concept)
        WITH o, f, collect(c.name) as skills
        RETURN o.id as id, o.title as title, f.user_id as fid, f.name as fname, f.department as fdept, skills
        ORDER BY o.created_at DESC 
        LIMIT 10
        """
        all_res = session.run(all_query)
        all_openings = []
        for r in all_res:
            all_openings.append({
                "opening_id": r["id"],
                "title": r["title"],
                "faculty_id": r["fid"],
                "faculty_name": r["fname"],
                "department": r["fdept"],
                "skills": r["skills"]
            })

        return {
            "user_info": user_info,
            "recommended_openings": recommended_openings,
            "all_openings": all_openings
        }
    finally:
        session.close()

# =========================================================
# 2. SIDE MENUS
# =========================================================

@router.get("/student/menu")
def get_student_side_menu(current_user: dict = Depends(get_current_user)):
    if current_user["role"].lower() != "student":
        raise HTTPException(status_code=403, detail="Access denied")

    user_id = current_user["user_id"]
    session = db.get_session()
    
    try:
        query = """
        MATCH (u:User {user_id: $user_id}) 
        RETURN u.name as name, u.roll_no as id, u.department as dept, u.profile_picture as pic
        """
        result = session.run(query, user_id=user_id).single()
        
        if not result:
            raise HTTPException(status_code=404, detail="User not found")

        return {
            "name": result["name"],
            "roll_no": result["id"],
            "department": result["dept"],
            "profile_picture": result["pic"],
            "menu_items": [
                {"label": "Home", "icon": "home", "route": "/student/home"},
                {"label": "Profile", "icon": "person", "route": "/student/profile"},
                {"label": "My Projects", "icon": "folder", "route": "/student/projects"},
                {"label": "Help & Support", "icon": "help", "route": "/support"},
                {"label": "All Faculty", "icon": "group", "route": "/student/all-faculty"},
                {"label": "Logout", "icon": "logout", "route": "/logout"}
            ]
        }
    finally:
        session.close()


@router.get("/faculty/menu")
def get_faculty_menu(current_user: dict = Depends(get_current_user)):
    if current_user["role"].lower() != "faculty":
        raise HTTPException(status_code=403, detail="Access denied")
        
    session = db.get_session()
    try:
        query = """
        MATCH (f:Faculty {user_id: $uid})
        RETURN f.name as name, f.employee_id as empid, f.department as dept, f.profile_picture as pic
        """
        res = session.run(query, uid=current_user["user_id"]).single()
        
        if not res:
            return {"name": "Faculty", "employee_id": "N/A", "department": "General", "profile_picture": None}
            
        return {
            "name": res["name"],
            "employee_id": res["empid"] or "N/A",
            "department": res["dept"] or "General",
            "profile_picture": res["pic"],
            "menu_items": [
                {"label": "Home", "icon": "home", "route": "/faculty/home"},
                {"label": "Profile", "icon": "person", "route": "/faculty/profile"},
                {"label": "My Projects", "icon": "folder", "route": "/faculty/projects"},
                {"label": "All Students", "icon": "group", "route": "/faculty/all-students"},
                {"label": "Faculty Collaborations", "icon": "link", "route": "/faculty/collaborations"},
                {"label": "Help & Support", "icon": "help", "route": "/support"},
                {"label": "Logout", "icon": "logout", "route": "/logout"}
            ]
        }
    finally:
        session.close()

# =========================================================
# 3. LISTS & SEARCH (Collaborations, All Students, All Faculty)
# =========================================================

@router.get("/faculty/collaborations")
def get_collaborations(search: str = None, department: str = None, collab_type: str = None, current_user: dict = Depends(get_current_user)):
    if current_user["role"].lower() != "faculty":
        raise HTTPException(status_code=403, detail="Access denied")
    
    session = db.get_session()
    try:
        query = """
        MATCH (f:Faculty)-[:POSTED|LED_PROJECT]->(w:Work)
        WHERE w.collaboration_type IS NOT NULL
        """
        
        # Search Filters
        if search:
            query += " AND (toLower(w.title) CONTAINS toLower($search) OR toLower(f.name) CONTAINS toLower($search))"
        if department:
            query += " AND f.department CONTAINS $dept"
        if collab_type:
            query += " AND w.collaboration_type = $type"
            
        query += """
        RETURN f.user_id as fid, f.name as fname, f.department as fdept,
               w.title as title, w.description as desc, w.collaboration_type as type, 
               w.tools_used as tags, w.id as pid
        ORDER BY w.id DESC
        """
        
        results = session.run(query, search=search, dept=department, type=collab_type)
        projects = []
        
        for r in results:
            projects.append({
                "faculty_id": r["fid"],
                "faculty_name": r["fname"],
                "department": r["fdept"],
                "title": r["title"],
                "description": r["desc"],
                "collaboration_type": r["type"],
                "tags": r.get("tags", []),
                "project_id": r["pid"]
            })
            
        return projects
    finally:
        session.close()


@router.get("/faculty/all-students")
def get_all_students(search: str = None, current_user: dict = Depends(get_current_user)):
    if current_user["role"].lower() != "faculty":
        raise HTTPException(status_code=403, detail="Access denied")

    session = db.get_session()
    try:
        query = "MATCH (s:Student) WHERE s.name IS NOT NULL"
        
        if search:
            query += """
            AND (
                toLower(s.name) CONTAINS toLower($search) 
                OR EXISTS {
                    MATCH (s)-[:HAS_SKILL]->(k:Concept)
                    WHERE toLower(k.name) CONTAINS toLower($search)
                }
            )
            """
            
        query += """
        OPTIONAL MATCH (s)-[:HAS_SKILL]->(k:Concept)
        RETURN s.user_id as id, s.name as name, s.department as dept, 
               s.batch as batch, s.profile_picture as pic,
               collect(DISTINCT k.name)[..3] as skills
        ORDER BY s.name ASC
        LIMIT 50
        """
        
        results = session.run(query, search=search)
        students = []
        for r in results:
            students.append({
                "student_id": r["id"],
                "name": r["name"],
                "department": r["dept"],
                "batch": r["batch"],
                "profile_picture": r["pic"],
                "skills": r["skills"]
            })
        return students
    finally:
        session.close()


@router.get("/student/all-faculty")
def get_all_faculty(
    search: Optional[str] = None,
    department: Optional[str] = None,
    domain: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    if current_user["role"].lower() != "student":
        raise HTTPException(status_code=403, detail="Access denied")

    session = db.get_session()
    
    try:
        query = "MATCH (f:Faculty) WHERE 1=1"
        
        if search:
            query += " AND (toLower(f.name) CONTAINS toLower($search) OR toLower(f.department) CONTAINS toLower($search))"
        if department:
            query += " AND f.department = $dept"
            
        query += """
        OPTIONAL MATCH (f)-[:INTERESTED_IN]->(c:Concept)
        WITH f, collect(c.name) as domains
        """
        
        if domain:
            query += " WHERE $domain IN domains"
            
        query += """
        RETURN f.user_id as id, f.name as name, f.department as dept, 
               f.profile_picture as pic, f.designation as designation,
               domains
        ORDER BY f.name ASC
        """
        
        res = session.run(query, search=search, dept=department, domain=domain)
        results = []
        for r in res:
            results.append({
                "faculty_id": r["id"],
                "name": r["name"],
                "department": r["dept"],
                "designation": r.get("designation", "Professor"),
                "profile_picture": r["pic"],
                "domains": r["domains"][:3],
                "status": "Available"
            })
            
        return results
    finally:
        session.close()

# =========================================================
# 4. PROFILE DETAILS
# =========================================================

@router.get("/faculty/student-profile/{student_id}")
def get_student_public_profile(student_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"].lower() != "faculty":
        raise HTTPException(status_code=403, detail="Access denied")

    session = db.get_session()
    
    try:
        # 1. Basic Info
        profile_query = """
        MATCH (s:Student {user_id: $sid})
        OPTIONAL MATCH (s)-[:HAS_SKILL]->(k:Concept)
        OPTIONAL MATCH (s)-[:INTERESTED_IN]->(i:Concept)
        RETURN s.name as name, s.roll_no as roll_no, s.department as dept, 
               s.batch as batch, s.bio as bio, s.email as email, s.phone as phone,
               s.profile_picture as pic,
               collect(DISTINCT k.name) as skills,
               collect(DISTINCT i.name) as interests
        """
        profile = session.run(profile_query, sid=student_id).single()
        
        if not profile:
            raise HTTPException(status_code=404, detail="Student not found")

        # 2. Projects
        proj_query = """
        MATCH (s:Student {user_id: $sid})-[:WORKED_ON]->(w:Work)
        RETURN w.title as title, w.description as desc, w.from_date as from_d, w.to_date as to_d, w.tools as tools
        ORDER BY w.id DESC
        """
        projects_res = session.run(proj_query, sid=student_id)
        projects = []
        for p in projects_res:
            projects.append({
                "title": p["title"],
                "description": p["desc"],
                "duration": f"{p['from_d']} - {p['to_d']}",
                "tools": p["tools"]
            })

        return {
            "info": {
                "name": profile["name"],
                "roll_no": profile["roll_no"],
                "department": profile["dept"],
                "batch": profile["batch"],
                "bio": profile["bio"] or "No bio added.",
                "email": profile["email"],
                "phone": profile["phone"],
                "profile_picture": profile["pic"],
                "skills": profile["skills"],
                "interests": profile["interests"]
            },
            "projects": projects
        }
    finally:
        session.close()


# ... imports ...

# ... (Keep imports)

@router.get("/student/faculty-profile/{faculty_id}")
def get_faculty_public_profile(faculty_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"].lower() not in ["student", "faculty"]:
        raise HTTPException(status_code=403, detail="Access denied")

    session = db.get_session()
    
    try:
        # Fetch individual qualification lists
        profile_query = """
        MATCH (f:User {user_id: $fid})
        OPTIONAL MATCH (f)-[:INTERESTED_IN]->(c:Concept)
        RETURN f.name as name, f.department as dept, f.designation as designation,
               f.email as email, f.phone as phone, f.profile_picture as pic,
               f.cabin_block as block, f.cabin_floor as floor, f.cabin_number as cabin_no,
               f.office_hours as office_hours, 
               f.ug_details as ug, f.pg_details as pg, f.phd_details as phd,
               collect(DISTINCT c.name) as interests
        """
        profile = session.run(profile_query, fid=faculty_id).single()
        
        if not profile:
            raise HTTPException(status_code=404, detail="Faculty not found")

        # Map backend fields to frontend JSON structure
        response_data = {
            "info": {
                "name": profile["name"],
                "designation": profile["designation"],
                "department": profile["dept"],
                "email": profile["email"],
                "phone": profile["phone"] or "",
                "profile_picture": profile["pic"],
                
                # Cabin Raw Data
                "cabin_block": profile["block"] or "",
                "cabin_floor": profile["floor"] or "",
                "cabin_number": profile["cabin_no"] or "",
                
                # Qualification Lists
                "ug_details": profile["ug"] or [],
                "pg_details": profile["pg"] or [],
                "phd_details": profile["phd"] or [],
                
                "interests": profile["interests"],
                "availability_status": "Available Now"
            },
            "schedule": profile["office_hours"] or "Mon-Fri 9AM-5PM",
            "openings": [],
            "previous_work": []
        }

        # ... (Keep Openings & Work queries as they were) ...
        # Fetch Openings
        openings_query = """
        MATCH (f:User {user_id: $fid})-[:POSTED]->(o:Opening)
        RETURN o.id as id, o.title as title, o.description as desc
        ORDER BY o.created_at DESC
        """
        openings = session.run(openings_query, fid=faculty_id)
        for o in openings:
            response_data["openings"].append({
                "id": o["id"],
                "title": o["title"],
                "type": "Project Opening",
                "description": o["desc"]
            })

# ... (inside get_faculty_public_profile) ...

        # Fetch Previous Work
        work_query = """
        MATCH (f:User {user_id: $fid})-[:WORKED_ON|PUBLISHED|LED_PROJECT]->(w:Work)
        RETURN w.title as title, w.type as type, w.year as year, w.outcome as outcome, w.collaborators as collaborators
        ORDER BY w.year DESC
        LIMIT 20 
        """
# ...
        works = session.run(work_query, fid=faculty_id)
        for w in works:
            response_data["previous_work"].append({
                "title": w["title"],
                "type": w["type"],
                "year": w["year"],
                "outcome": w["outcome"],
                "collaborators": w["collaborators"]
            })

        return response_data
    finally:
        session.close()
# =========================================================
# 5. ACTIONS & NOTIFICATIONS
# =========================================================

@router.post("/shortlist/{student_id}")
def shortlist_student(student_id: str, current_user: dict = Depends(get_current_user)):
    session = db.get_session()
    try:
        query = """
        MATCH (f:Faculty {user_id: $fid}), (s:Student {user_id: $sid})
        MERGE (f)-[:SHORTLISTED]->(s)
        """
        session.run(query, fid=current_user["user_id"], sid=student_id)
        return {"message": "Student shortlisted"}
    finally:
        session.close()


@router.post("/express-interest/{project_id}")
def express_interest(project_id: str, current_user: dict = Depends(get_current_user)):
    session = db.get_session()
    user_id = current_user["user_id"]
    user_name = current_user.get("name", "A user")
    role = current_user["role"]

    try:
        # Find Owner
        owner_query = """
        MATCH (owner:User)-[:PUBLISHED|LED_PROJECT|POSTED]->(w:Work {id: $pid})
        RETURN owner.user_id as owner_id, w.title as title
        """
        result = session.run(owner_query, pid=project_id).single()
        if not result:
            raise HTTPException(status_code=404, detail="Project not found")
            
        owner_id = result["owner_id"]
        project_title = result["title"]

        # Duplicate Check
        check_query = "MATCH (u:User {user_id: $uid})-[r:INTERESTED_IN]->(w:Work {id: $pid}) RETURN r"
        if session.run(check_query, uid=user_id, pid=project_id).single():
            return {"message": "Already expressed interest"}

        # Create Link
        connect_query = """
        MATCH (u:User {user_id: $uid}), (w:Work {id: $pid})
        MERGE (u)-[:INTERESTED_IN {date: datetime()}]->(w)
        """
        session.run(connect_query, uid=user_id, pid=project_id)

        # Notify Owner
        msg = f"{user_name} ({role}) is interested in '{project_title}'"
        session.write_transaction(create_notification, owner_id, msg, "INTEREST", trigger_id=user_id, trigger_role=role)

        return {"message": "Interest expressed!"}
    finally:
        session.close()


@router.get("/notifications")
def get_notifications(current_user: dict = Depends(get_current_user)):
    user_id = current_user["user_id"]
    session = db.get_session()
    try:
        query = """
        MATCH (n:Notification)-[:NOTIFIES]->(u:User {user_id: $uid})
        RETURN n.id as id, n.message as message, n.type as type, 
               n.is_read as is_read, n.created_at as date,
               n.trigger_id as trigger_id, n.trigger_role as trigger_role
        ORDER BY n.created_at DESC LIMIT 20
        """
        results = session.run(query, uid=user_id)
        notifs = []
        for r in results:
            notifs.append({
                "id": r["id"],
                "message": r["message"],
                "type": r["type"],
                "is_read": r["is_read"],
                "date": r["date"].isoformat() if r["date"] else "",
                "trigger_id": r["trigger_id"],
                "trigger_role": r["trigger_role"]
            })
        return notifs
    finally:
        session.close()


@router.put("/notifications/{notif_id}/read")
def mark_notification_read(notif_id: str, current_user: dict = Depends(get_current_user)):
    session = db.get_session()
    try:
        query = "MATCH (n:Notification {id: $nid})-[:NOTIFIES]->(u:User {user_id: $uid}) SET n.is_read = true"
        session.run(query, nid=notif_id, uid=current_user["user_id"])
        return {"message": "Marked as read"}
    finally:
        session.close()