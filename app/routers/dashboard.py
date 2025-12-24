from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from app.core.security import get_current_user
from app.core.database import db

# IMPORT THE NEW SERVICES
from app.services.rag_service import (
    recommend_students_for_faculty, 
    recommend_openings_for_student
)

router = APIRouter()

# ---------------------------------------------------------
# 1. FACULTY DASHBOARD (Landing Page)
# ---------------------------------------------------------
@router.get("/faculty/home")
def get_faculty_dashboard(current_user: dict = Depends(get_current_user)):
    """
    Returns data for the Faculty Home Screen.
    """
    if current_user["role"].lower() != "faculty":
        raise HTTPException(status_code=403, detail="Access denied")

    user_id = current_user["user_id"]
    session = db.get_session()
    
    response_data = {
        "user_info": {},
        "recommended_students": [],
        "faculty_collaborations": []
    }

    try:
        # A. User Info
        user_query = "MATCH (u:User {user_id: $user_id}) RETURN u.name as name, u.department as dept, u.profile_picture as pic"
        user_res = session.run(user_query, user_id=user_id).single()
        if user_res:
            response_data["user_info"] = user_res.data()

        # B. AI Recommendations (Using rag_service)
        # We fetch top 5 students matched to the faculty's interests
        recs = recommend_students_for_faculty(user_id, limit=5)
        for r in recs:
            response_data["recommended_students"].append({
                "student_id": r["student_id"],
                "name": r["name"],
                "department": r.get("dept", "N/A"),
                "batch": r.get("batch", "N/A"),
                "profile_picture": r.get("pic", ""),
                "matched_skills": r["common_concepts"],
                "match_score": f"{int(r['match_score'])}%"  # Format as "95%" for UI
            })

        # C. Collaborations (Recent posts from other faculty)
        collab_query = """
        MATCH (other:Faculty)-[:PUBLISHED|LED_PROJECT]->(w:Work)
        WHERE other.user_id <> $user_id AND w.collaboration_type IS NOT NULL
        RETURN other.name as faculty_name, other.department as faculty_dept,
               other.profile_picture as faculty_pic,
               w.title as title, w.collaboration_type as type
        ORDER BY w.id DESC LIMIT 3
        """
        collab_res = session.run(collab_query, user_id=user_id)
        for r in collab_res:
            response_data["faculty_collaborations"].append(r.data())

        return response_data
    finally:
        session.close()


# ---------------------------------------------------------
# 2. STUDENT DASHBOARD (Landing Page)
# ---------------------------------------------------------
# app/routers/dashboard.py

@router.get("/student/home")
def get_student_dashboard(current_user: dict = Depends(get_current_user)):
    """
    Returns data for the Student Home Screen.
    """
    if current_user["role"].lower() != "student":
        raise HTTPException(status_code=403, detail="Access denied")

    user_id = current_user["user_id"]
    session = db.get_session()
    
    response_data = {
        "user_info": {},
        "recommended_openings": [],
        "all_openings": []
    }

    try:
        # A. User Info
        user_query = "MATCH (u:User {user_id: $user_id}) RETURN u.name as name, u.roll_no as roll_no"
        user_res = session.run(user_query, user_id=user_id).single()
        if user_res:
            response_data["user_info"] = user_res.data()

        # B. AI Recommendations (Using rag_service)
        # We fetch openings that match student skills
        recs = recommend_openings_for_student(user_id, limit=5)
        for r in recs:
            response_data["recommended_openings"].append({
                "opening_id": r["opening_id"],
                "title": r["title"],
                "faculty_name": r["faculty_name"],
                "department": r["faculty_dept"],
                "skills": r["skills"][:3], # Show top 3 required skills
                "match_score": f"{int(r['match_score'])}%" # Format as "92%" for UI
            })

        # --- C. FIXED QUERY FOR ALL OPENINGS ---
        all_query = """
        MATCH (f:Faculty)-[:POSTED]->(o:Opening)
        OPTIONAL MATCH (o)-[:REQUIRES]->(c:Concept)
        
        // FIX: Group by 'o' and 'f' first to preserve them for sorting
        WITH o, f, collect(c.name) as skills
        
        RETURN o.id as id, o.title as title, f.name as fname, f.department as fdept, skills
        ORDER BY o.created_at DESC 
        LIMIT 10
        """
        all_res = session.run(all_query)
        for r in all_res:
            response_data["all_openings"].append({
                "opening_id": r["id"],
                "title": r["title"],
                "faculty_name": r["fname"],
                "department": r["fdept"], # Make sure this key matches your UI model
                "skills": r["skills"]
            })

        return response_data
    finally:
        session.close()

# ---------------------------------------------------------
# 3. COLLABORATION HUB (Search)
# ---------------------------------------------------------
@router.get("/faculty/collaborations")
def search_collaborations(
    department: Optional[str] = None,
    collab_type: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    if current_user["role"].lower() != "faculty":
        raise HTTPException(status_code=403, detail="Access denied")
    
    session = db.get_session()
    results = []
    
    try:
        query = """
        MATCH (f:Faculty)-[:PUBLISHED|LED_PROJECT]->(w:Work)
        WHERE w.collaboration_type IS NOT NULL
        """
        
        if department:
            query += " AND f.department CONTAINS $dept"
        if collab_type:
            query += " AND w.collaboration_type = $type"
            
        query += """
        RETURN f.name as faculty_name, f.department as faculty_dept, 
               w.title as title, w.description as desc, w.collaboration_type as type, 
               w.tools_used as tags
        ORDER BY w.id DESC
        """
        
        result_proxy = session.run(query, dept=department, type=collab_type)
        for record in result_proxy:
            results.append({
                "faculty_name": record["faculty_name"],
                "department": record["faculty_dept"],
                "title": record["title"],
                "description": record["desc"],
                "collaboration_type": record["type"],
                "tags": record.get("tags", [])
            })
            
        return results
    finally:
        session.close()

# ---------------------------------------------------------
# 4. ACTIONS (Shortlist)
# ---------------------------------------------------------
@router.post("/shortlist/{student_id}")
def shortlist_student(student_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"].lower() != "faculty":
        raise HTTPException(status_code=403, detail="Access denied")

    session = db.get_session()
    faculty_id = current_user["user_id"]
    
    try:
        check_q = "MATCH (s:Student {user_id: $sid}) RETURN s"
        if not session.run(check_q, sid=student_id).single():
            raise HTTPException(status_code=404, detail="Student not found")

        query = """
        MATCH (f:Faculty {user_id: $fid}), (s:Student {user_id: $sid})
        MERGE (f)-[:SHORTLISTED]->(s)
        """
        session.run(query, fid=faculty_id, sid=student_id)
        return {"message": "Student shortlisted successfully"}
    finally:
        session.close()


# ... (keep existing imports) ...

# ---------------------------------------------------------
# 5. SIDE MENU (DRAWER) DATA
# ---------------------------------------------------------

@router.get("/student/menu")
def get_student_side_menu(current_user: dict = Depends(get_current_user)):
    """
    Fetches data for the Student Side Drawer (Header info).
    """
    if current_user["role"].lower() != "student":
        raise HTTPException(status_code=403, detail="Access denied")

    user_id = current_user["user_id"]
    session = db.get_session()
    
    try:
        # Fetch only what's needed for the red header card
        query = """
        MATCH (u:User {user_id: $user_id}) 
        RETURN u.name as name, u.roll_no as id, u.department as dept, u.profile_picture as pic
        """
        result = session.run(query, user_id=user_id).single()
        
        if not result:
            raise HTTPException(status_code=404, detail="User not found")

        return {
            "name": result["name"],
            "roll_no": result["id"],        # Matches "Roll No: AM.EN..."
            "department": result["dept"],   # Matches "Department: CSE"
            "profile_picture": result["pic"],
            "menu_items": [                 # Dynamic list for Frontend
                {"label": "Home", "icon": "home", "route": "/student/home"},
                {"label": "Profile", "icon": "person", "route": "/student/profile"},
                {"label": "My Projects", "icon": "folder", "route": "/student/projects"},
                {"label": "Help & Support", "icon": "help", "route": "/support"},
                {"label": "All Faculty", "icon": "group", "route": "/faculty-list"},
                {"label": "Logout", "icon": "logout", "route": "/logout"}
            ]
        }
    finally:
        session.close()


@router.get("/faculty/menu")
def get_faculty_side_menu(current_user: dict = Depends(get_current_user)):
    """
    Fetches data for the Faculty Side Drawer (Header info).
    """
    if current_user["role"].lower() != "faculty":
        raise HTTPException(status_code=403, detail="Access denied")

    user_id = current_user["user_id"]
    session = db.get_session()
    
    try:
        # Fetch header info (Employee ID is stored as employee_id or just id depending on your setup)
        # Assuming you stored 'employee_id' during registration, or we use a generic ID field.
        # Let's assume we want to show the 'designation' if available too? 
        # The screenshot shows "Employee ID: FAC..." and "Department: CSE"
        
        query = """
        MATCH (u:User {user_id: $user_id}) 
        RETURN u.name as name, u.employee_id as id, u.department as dept, u.profile_picture as pic
        """
        result = session.run(query, user_id=user_id).single()
        
        if not result:
            raise HTTPException(status_code=404, detail="User not found")

        return {
            "name": result["name"],
            "employee_id": result["id"],      # Matches "Employee ID: FAC..."
            "department": result["dept"],
            "profile_picture": result["pic"],
            "menu_items": [
                {"label": "Home", "icon": "home", "route": "/faculty/home"},
                {"label": "Profile", "icon": "person", "route": "/faculty/profile"},
                {"label": "My Projects", "icon": "folder", "route": "/faculty/projects"},
                {"label": "Faculty Collaborations", "icon": "link", "route": "/faculty/collaborations"},
                {"label": "Help & Support", "icon": "help", "route": "/support"},
                {"label": "Logout", "icon": "logout", "route": "/logout"}
            ]
        }
    finally:
        session.close()