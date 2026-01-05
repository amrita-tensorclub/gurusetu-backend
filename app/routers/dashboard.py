from typing import Optional, List
import uuid
from datetime import datetime, date

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
import numpy as np

from app.core.security import get_current_user
from app.core.database import db
from app.services.rag_service import semantic_search_students

# --- OPTIONAL AI IMPORT (Prevents crash if library missing) ---
try:
    from app.services.embedding import generate_embedding
except ImportError:
    print("WARNING: 'sentence_transformers' or 'app.services.embedding' not found. AI features disabled.")
    generate_embedding = None

# Initialize Router
router = APIRouter(tags=["Dashboard"])

# =========================================================
# DATA MODELS
# =========================================================

class ShortlistRequest(BaseModel):
    opening_id: str

# =========================================================
# HELPER FUNCTIONS
# =========================================================

def safe_date(date_obj):
    """
    Safely converts Neo4j/Python date objects to ISO string (YYYY-MM-DD).
    Handles None, Neo4j DateTime, and Python datetime objects.
    """
    if not date_obj:
        return "N/A"
    try:
        if hasattr(date_obj, 'isoformat'):
            return date_obj.isoformat().split('T')[0]
        return str(date_obj)
    except:
        return "N/A"

def cosine_similarity(vec_a, vec_b):
    """
    Calculates cosine similarity between two vectors.
    Returns float between 0.0 and 1.0.
    """
    if not vec_a or not vec_b:
        return 0.0
    try:
        a = np.array(vec_a)
        b = np.array(vec_b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))
    except Exception as e:
        print(f"Math Error in Cosine Similarity: {e}")
        return 0.0

def create_notification(tx, user_id, message, type="INFO", trigger_id=None, trigger_role=None):
    """
    Helper to create a notification node in Neo4j.
    Must be called within an active Neo4j transaction context.
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

# Location: backend/app/routers/dashboard.py

@router.get("/faculty/home")
def get_faculty_home(filter: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    if current_user["role"].lower() != "faculty":
        raise HTTPException(status_code=403, detail="Access denied")

    session = db.get_session()
    user_id = current_user["user_id"]
    
    try:
        # 1. FETCH FACULTY KEYWORDS (Optimized Query)
        user_query = """
        MATCH (f:User {user_id: $uid})
        OPTIONAL MATCH (n:Notification)-[:NOTIFIES]->(f) WHERE n.is_read = false
        OPTIONAL MATCH (f)-[:INTERESTED_IN|EXPERT_IN]->(concept:Concept)
        OPTIONAL MATCH (f)-[:POSTED]->(o:Opening)-[:REQUIRES]->(req:Concept)
        RETURN f.name as name, f.department as dept, f.profile_picture as pic, 
               count(DISTINCT n) as unread_count,
               collect(DISTINCT concept.name) + collect(DISTINCT req.name) as keywords
        """
        user_res = session.run(user_query, uid=user_id).single()
        
        faculty_keywords = [str(k).lower().strip() for k in user_res["keywords"] if k] if user_res else []

        # 2. FETCH STUDENTS (Removed AI Loop for Speed)
        # We perform exact keyword matching in the Graph to avoid CPU-heavy AI processing during GET
        students_query = """
        MATCH (s:Student)
        OPTIONAL MATCH (s)-[:HAS_SKILL|INTERESTED_IN]->(sk:Concept)
        WITH s, collect(DISTINCT toLower(sk.name)) as s_skills
        
        // Calculate Match Score based on shared keywords
        WITH s, s_skills, 
             size([x IN s_skills WHERE x IN $f_keywords]) as matches
        
        RETURN s.user_id as id, s.name as name, s.department as dept, 
               s.profile_picture as pic, s_skills as skills,
               matches
        ORDER BY matches DESC
        LIMIT 10
        """
        stu_results = session.run(students_query, f_keywords=faculty_keywords)
        
        recommended_students = []
        for s in stu_results:
            match_percent = (s["matches"] / len(faculty_keywords) * 100) if faculty_keywords else 0
            recommended_students.append({
                "student_id": s["id"],
                "name": s["name"],
                "department": s["dept"] or "General",
                "profile_picture": s["pic"],
                "matched_skills": s["skills"][:3],
                "match_score": f"{int(match_percent)}%"
            })

        # 3. FETCH COLLABORATIONS (Limit results)
        collab_query = """
        MATCH (f:User)-[:POSTED]->(o:Opening)
        WHERE f.user_id <> $uid AND o.collaboration_type IS NOT NULL
        RETURN f.user_id as fid, f.name as name, f.profile_picture as pic, 
               o.id as pid, o.title as title, o.collaboration_type as type
        ORDER BY o.created_at DESC LIMIT 5
        """
        collab_res = session.run(collab_query, uid=user_id)
        collaborations = [{"id": r["pid"], "faculty_name": r["name"], "project_title": r["title"]} for r in collab_res]

        return {
            "user_info": {"name": user_res["name"], "department": user_res["dept"], "pic": user_res["pic"]},
            "unread_count": user_res["unread_count"],
            "recommended_students": recommended_students,
            "faculty_collaborations": collaborations,
            "active_openings": [] # Fetch your own openings here
        }

    finally:
        session.close()

@router.get("/student/home")
def get_student_dashboard(current_user: dict = Depends(get_current_user)):
    if current_user["role"].lower() != "student":
        raise HTTPException(status_code=403, detail="Access denied")

    user_id = current_user["user_id"]
    session = db.get_session()
    
    # Defaults
    user_info = {}
    unread_count = 0
    recommended_final = []
    all_openings_data = []

    try:
        # =========================================================
        # 1. FETCH STUDENT (Skills + Interests)
        # =========================================================
        user_query = """
        MATCH (u:User {user_id: $user_id}) 
        OPTIONAL MATCH (n:Notification)-[:NOTIFIES]->(u) WHERE n.is_read = false
        OPTIONAL MATCH (u)-[:HAS_SKILL]->(s)
        OPTIONAL MATCH (u)-[:INTERESTED_IN]->(i)
        RETURN u.name as name, u.roll_no as roll_no,
               count(n) as unread_count, 
               collect(DISTINCT s.name) as skills, 
               collect(DISTINCT i.name) as interests
        """
        user_res = session.run(user_query, user_id=user_id).single()
        
        my_capabilities = set()
        
        if user_res:
            user_info = {"name": user_res["name"], "roll_no": user_res["roll_no"]}
            unread_count = user_res["unread_count"]
            
            # Normalize Skills
            if user_res["skills"]:
                for s in user_res["skills"]:
                    if s: my_capabilities.add(str(s).lower().strip())

            # Normalize Interests
            if user_res["interests"]:
                for i in user_res["interests"]:
                    if i: my_capabilities.add(str(i).lower().strip())

        # =========================================================
        # 2. FETCH OPENINGS & MATCH (Student Only)
        # =========================================================
        openings_query = """
        MATCH (o:Opening)
        WHERE o.collaboration_type IS NULL  // <--- FIX: Exclude Faculty Collaborations
        MATCH (f:User)-[:POSTED]->(o)
        OPTIONAL MATCH (o)-[:REQUIRES]->(req)
        WITH o, f, collect(req.name) as req_skills
        RETURN o.id as oid, o.title as title, o.description as desc, o.deadline as deadline,
               f.name as fname, f.department as fdept, f.profile_picture as fpic, 
               req_skills
        ORDER BY o.created_at DESC
        LIMIT 20
        """
        op_results = session.run(openings_query)
        
        scored_openings = []

        for r in op_results:
            # Normalize Job Requirements
            raw_reqs = [x for x in r["req_skills"] if x]
            normalized_reqs = [str(req).lower().strip() for req in raw_reqs]
            
            match_percentage = 0.0

            if normalized_reqs:
                matches_found = 0
                for req in normalized_reqs:
                    if req in my_capabilities:
                        matches_found += 1
                
                # Formula: (Matches / Requirements) * 100
                if len(normalized_reqs) > 0:
                    match_percentage = (matches_found / len(normalized_reqs)) * 100.0
            
            # Build Object
            opening_obj = {
                "opening_id": r["oid"],
                "title": r["title"],
                "faculty_name": r["fname"] or "Faculty",
                "department": r["fdept"] or "General",
                "faculty_pic": r["fpic"],
                "skills_required": raw_reqs[:3],
                "description": r["desc"],
                "deadline": safe_date(r["deadline"]),
                "match_score": f"{int(match_percentage)}%", 
                "raw_score": match_percentage
            }

            scored_openings.append(opening_obj)
            all_openings_data.append(opening_obj)

        # 3. FILTER RECOMMENDATIONS (Hide 0%)
        # Filter: Only keep jobs where score > 0
        filtered_recs = [op for op in scored_openings if op["raw_score"] > 0]
        
        # Sort: Highest score first
        filtered_recs.sort(key=lambda x: x["raw_score"], reverse=True)
        
        # Slice: Top 5 only
        recommended_final = filtered_recs[:5]

    except Exception as e:
        # Return safe defaults on error
        print(f"Error in student dashboard: {e}")
        return {
            "user_info": user_info,
            "unread_count": 0,
            "recommended_openings": [],
            "all_openings": []
        }
    finally:
        session.close()

    return {
        "user_info": user_info,
        "unread_count": unread_count,
        "recommended_openings": recommended_final,
        "all_openings": all_openings_data
    }

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
                {"label": "Home", "icon": "home", "route": "/dashboard/student"},
                {"label": "Profile", "icon": "person", "route": "/dashboard/student/profile"},
                {"label": "Track Openings", "icon": "folder", "route": "/dashboard/student/projects"},
                {"label": "Help & Support", "icon": "help", "route": "/dashboard/student/support"},
                {"label": "All Faculty", "icon": "group", "route": "/dashboard/student/all-faculty"},
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
                {"label": "Profile", "icon": "person", "route": "/dashboard/faculty/profile"},
                {"label": "My Openings", "icon": "folder", "route": "/dashboard/faculty/projects"},
                {"label": "All Students", "icon": "group", "route": "/dashboard/faculty/all-students"},
                {"label": "Faculty Collaborations", "icon": "link", "route": "/dashboard/faculty/collaborations"},
                {"label": "Help & Support", "icon": "help", "route": "/dashboard/faculty/support"},
                {"label": "Logout", "icon": "logout", "route": "/logout"}
            ]
        }
    finally:
        session.close()

# =========================================================
# 3. SEARCH & LISTS (FACULTY/STUDENTS/COLLABS)
# =========================================================

@router.get("/faculty/collaborations")
def get_collaborations(search: str = None, department: str = None, collab_type: str = None, current_user: dict = Depends(get_current_user)):
    session = db.get_session()
    try:
        query = """
        MATCH (f:User)-[:POSTED]->(o:Opening)
        WHERE o.collaboration_type IS NOT NULL
        """
        
        if search:
            query += " AND (toLower(o.title) CONTAINS toLower($search) OR toLower(f.name) CONTAINS toLower($search))"
        if department:
            query += " AND f.department CONTAINS $dept"
        if collab_type:
            query += " AND o.collaboration_type = $type"
            
        query += """
        OPTIONAL MATCH (o)-[:REQUIRES]->(c:Concept)
        WITH f, o, collect(c.name) as skills
        RETURN f.user_id as fid, f.name as fname, f.department as fdept, f.profile_picture as fpic,
               o.title as title, o.description as desc, o.collaboration_type as type, 
               skills as tags, o.id as pid
        ORDER BY o.created_at DESC
        """
        
        results = session.run(query, search=search, dept=department, type=collab_type)
        projects = []
        for r in results:
            projects.append({
                "faculty_id": r["fid"],
                "faculty_name": r["fname"],
                "department": r["fdept"] or "General",
                "faculty_pic": r["fpic"],
                "title": r["title"],
                "description": r["desc"],
                "collaboration_type": r["type"],
                "tags": r["tags"],
                "project_id": r["pid"]
            })
        return projects
    finally:
        session.close()

@router.get("/faculty/all-students")
def get_all_students(
    search: Optional[str] = None, 
    department: Optional[str] = None, 
    batch: Optional[str] = None, 
    current_user: dict = Depends(get_current_user)
):
    if current_user["role"].lower() != "faculty":
        raise HTTPException(status_code=403, detail="Access denied")

    # A. VECTOR SEARCH (If search term exists)
    if search:
        try:
            results = semantic_search_students(query=search, limit=20)
            
            # Local filtering for strict fields
            if department:
                results = [r for r in results if r.get('dept') == department]
            if batch:
                results = [r for r in results if r.get('batch') == batch]
                
            return results 
        except Exception as e:
            print(f"Vector search failed, falling back to standard: {e}")

    # B. STANDARD SEARCH (Fallback)
    session = db.get_session()
    try:
        query = "MATCH (s:Student) WHERE s.name IS NOT NULL"
        if search:
            query += " AND (toLower(s.name) CONTAINS toLower($search) OR EXISTS { MATCH (s)-[:HAS_SKILL]->(k:Concept) WHERE toLower(k.name) CONTAINS toLower($search) })"
        if department:
            query += " AND s.department = $dept"
        if batch:
            query += " AND s.batch = $batch"
            
        query += """
        OPTIONAL MATCH (s)-[:HAS_SKILL]->(k:Concept)
        RETURN s.user_id as id, s.name as name, s.department as dept, 
               s.batch as batch, s.profile_picture as pic,
               collect(DISTINCT k.name)[..3] as skills
        ORDER BY s.name ASC
        LIMIT 50
        """
        
        results = session.run(query, search=search, dept=department, batch=batch)
        students = []
        for r in results:
            students.append({
                "student_id": r["id"],
                "name": r["name"],
                "department": r["dept"],
                "batch": r["batch"],
                "profile_picture": r["pic"],
                "skills": r["skills"],
                "similarity_score": 0 
            })
        return students
    finally:
        session.close()

@router.get("/student/all-faculty")
def get_all_faculty(search: Optional[str] = None, department: Optional[str] = None, domain: Optional[str] = None, current_user: dict = Depends(get_current_user)):
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
# 4. PROJECTS / OPENINGS MANAGEMENT (FACULTY)
# =========================================================

@router.get("/faculty/projects")
def get_faculty_projects(current_user: dict = Depends(get_current_user)):
    if current_user["role"].lower() != "faculty":
        raise HTTPException(status_code=403, detail="Not authorized")
    
    session = db.get_session()
    try:
        query = """
        MATCH (u:User {user_id: $user_id})-[:POSTED]->(o:Opening)
        OPTIONAL MATCH (o)<-[:APPLIED_TO]-(s:User)
        OPTIONAL MATCH (o)<-[:INTERESTED_IN]-(f:User)
        
        WITH o, count(DISTINCT s) as applicant_count, count(DISTINCT f) as interest_count
        
        RETURN 
            o.id as id,
            o.title as title,
            o.status as status,
            o.domain as domain,
            toString(o.deadline) as deadline,
            toString(o.created_at) as posted_date,
            o.collaboration_type as collaboration_type,
            applicant_count,
            interest_count
        ORDER BY posted_date DESC
        """
        
        result = session.run(query, user_id=current_user["user_id"])
        projects = [dict(record) for record in result]
        
        stats = {
            "active_projects": len([p for p in projects if p.get("status") == "Active"]),
            "total_applicants": sum(p.get("applicant_count", 0) for p in projects),
            "total_shortlisted": 0 
        }

        return {"stats": stats, "projects": projects}
    except Exception as e:
        print(f"Error fetching projects: {str(e)}") 
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()

@router.get("/faculty/projects/{project_id}/applicants")
def get_project_applicants(project_id: str, current_user: dict = Depends(get_current_user)):
    session = db.get_session()
    try:
        query = """
        MATCH (o:Opening {id: $pid})<-[:APPLIED_TO]-(s:Student)
        WHERE NOT (o)-[:SHORTLISTED]->(s) 
          AND NOT (o)-[:REJECTED]->(s)
        RETURN s.user_id as id, s.name as name, s.roll_no as roll, s.department as dept, s.profile_picture as pic
        """
        results = session.run(query, pid=project_id)
        return [
            {
                "student_id": r["id"], 
                "name": r["name"], 
                "roll_no": r["roll"], 
                "department": r["dept"], 
                "profile_picture": r["pic"]
            } 
            for r in results
        ]
    finally:
        session.close()

@router.get("/faculty/projects/{project_id}/shortlisted")
def get_project_shortlisted(project_id: str, current_user: dict = Depends(get_current_user)):
    session = db.get_session()
    try:
        query = """
        MATCH (o:Opening {id: $pid})-[:SHORTLISTED]->(s:Student)
        RETURN s.user_id as id, s.name as name, s.roll_no as roll, s.department as dept, s.profile_picture as pic
        """
        results = session.run(query, pid=project_id)
        return [
            {
                "student_id": r["id"], 
                "name": r["name"], 
                "roll_no": r["roll"], 
                "department": r["dept"], 
                "profile_picture": r["pic"]
            } 
            for r in results
        ]
    finally:
        session.close()

# =========================================================
# 5. PROFILES & APPLICATIONS
# =========================================================

@router.get("/student/applications")
def get_student_applications(current_user: dict = Depends(get_current_user)):
    if current_user["role"].lower() != "student":
        raise HTTPException(status_code=403, detail="Access denied")
    
    session = db.get_session()
    try:
        query = """
        MATCH (s:Student {user_id: $uid})-[r:APPLIED_TO]->(o:Opening)
        OPTIONAL MATCH (f:User)-[:POSTED]->(o)
        RETURN o.id as id, o.title as title, 
               f.name as faculty_name, f.department as dept, f.profile_picture as pic,
               r.status as status, r.applied_at as applied_date
        ORDER BY r.applied_at DESC
        """
        results = session.run(query, uid=current_user["user_id"])
        
        applications = []
        for row in results:
            applications.append({
                "id": row["id"],
                "title": row["title"],
                "faculty_name": row["faculty_name"] or "Unknown Faculty",
                "department": row["dept"] or "General",
                "faculty_pic": row["pic"],
                "status": row["status"] or "Pending", 
                "applied_date": safe_date(row["applied_date"])
            })
        return applications
    finally:
        session.close()

@router.get("/faculty/student-profile/{student_id}")
def get_student_public_profile(student_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"].lower() != "faculty":
        raise HTTPException(status_code=403, detail="Access denied")

    session = db.get_session()
    try:
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

@router.get("/student/faculty-profile/{faculty_id}")
def get_faculty_public_profile(faculty_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"].lower() not in ["student", "faculty"]:
        raise HTTPException(status_code=403, detail="Access denied")

    session = db.get_session()
    try:
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

        response_data = {
            "info": {
                "name": profile["name"],
                "designation": profile["designation"],
                "department": profile["dept"],
                "email": profile["email"],
                "phone": profile["phone"] or "",
                "profile_picture": profile["pic"],
                "cabin_block": profile["block"] or "",
                "cabin_floor": profile["floor"] or "",
                "cabin_number": profile["cabin_no"] or "",
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

        work_query = """
        MATCH (f:User {user_id: $fid})-[:WORKED_ON|PUBLISHED|LED_PROJECT]->(w:Work)
        RETURN w.title as title, w.type as type, w.year as year, w.outcome as outcome, w.collaborators as collaborators
        ORDER BY w.year DESC
        LIMIT 20 
        """
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
# 6. ACTIONS & NOTIFICATIONS
# =========================================================

@router.post("/shortlist/{student_id}")
def shortlist_student(
    student_id: str, 
    request: ShortlistRequest,
    current_user: dict = Depends(get_current_user)
):
    session = db.get_session()
    try:
        query = """
        MATCH (o:Opening {id: $oid}), (s:Student {user_id: $sid})
        MERGE (o)-[:SHORTLISTED]->(s)
        """
        session.run(query, oid=request.opening_id, sid=student_id)
        return {"message": "Student shortlisted for opening"}
    finally:
        session.close()

@router.post("/express-interest/{project_id}")
def express_interest(project_id: str, current_user: dict = Depends(get_current_user)):
    session = db.get_session()
    user_id = current_user["user_id"]
    user_name = current_user.get("name", "A user")
    role = current_user["role"]

    try:
        # 1. Identify the Target (Opening OR Work)
        owner_query = """
        MATCH (owner:User)-[:POSTED|PUBLISHED|LED_PROJECT]->(node)
        WHERE (node:Opening OR node:Work) AND node.id = $pid
        RETURN owner.user_id as owner_id, node.title as title, labels(node) as labels
        """
        result = session.run(owner_query, pid=project_id).single()
        
        if not result:
            raise HTTPException(status_code=404, detail="Project or Opening not found")
            
        owner_id = result["owner_id"]
        project_title = result["title"]

        # 2. Check if already interested
        check_query = """
        MATCH (u:User {user_id: $uid})-[r:INTERESTED_IN]->(node)
        WHERE node.id = $pid
        RETURN r
        """
        if session.run(check_query, uid=user_id, pid=project_id).single():
            return {"message": "Already expressed interest"}

        # 3. Create Relationship
        connect_query = """
        MATCH (u:User {user_id: $uid})
        MATCH (node) WHERE (node:Opening OR node:Work) AND node.id = $pid
        MERGE (u)-[:INTERESTED_IN {date: datetime()}]->(node)
        """
        session.run(connect_query, uid=user_id, pid=project_id)

        # 4. Notify Owner
        msg = f"{user_name} ({role}) is interested in your collaboration: '{project_title}'"
        create_notification(session, owner_id, msg, "INTEREST", trigger_id=user_id, trigger_role=role)

        return {"message": "Interest expressed! The faculty has been notified."}
    except Exception as e:
        print(f"Error expressing interest: {e}")
        raise HTTPException(status_code=500, detail=str(e))
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
                "date": safe_date(r["date"]),
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