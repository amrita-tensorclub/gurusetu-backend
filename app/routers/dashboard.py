from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from app.core.security import get_current_user
from app.core.database import db
from app.services.rag_service import recommend_students_for_faculty
router = APIRouter()

@router.get("/faculty/home")
def get_faculty_dashboard(current_user: dict = Depends(get_current_user)):
    """
    Fetches data for the main Faculty Dashboard.
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
        # A. Get User Info
        user_query = "MATCH (u:User {user_id: $user_id}) RETURN u.name as name, u.department as dept, u.profile_picture as pic"
        user_res = session.run(user_query, user_id=user_id).single()
        if user_res:
            response_data["user_info"] = {
                "name": user_res["name"], 
                "department": user_res["dept"],
                "profile_picture": user_res["pic"]
            }

        # --- B. GET AI RECOMMENDATIONS (Replaced Manual Query) ---
        # We now call the RAG Service directly
        ai_recommendations = recommend_students_for_faculty(user_id, limit=5)
        
        # Map the AI result to your Dashboard format
        for student in ai_recommendations:
            response_data["recommended_students"].append({
                "student_id": student["student_id"],
                "name": student["name"],
                "department": student.get("dept", "N/A"),
                "batch": student.get("batch", "N/A"),
                "profile_picture": student.get("pic", ""),
                "matched_skills": student["matched_skills"],
                "match_score": f"{student['match_score']}%"
            })
        # ---------------------------------------------------------

        # C. Get Recent Collaborations (From other Faculty)
        collab_query = """
        MATCH (other:Faculty)-[:PUBLISHED|LED_PROJECT]->(w:Work)
        WHERE other.user_id <> $user_id AND w.collaboration_type IS NOT NULL
        RETURN other.name as faculty_name, other.department as faculty_dept, other.profile_picture as faculty_pic,
               w.title as title, w.collaboration_type as type
        ORDER BY w.id DESC
        LIMIT 3
        """
        collab_res = session.run(collab_query, user_id=user_id)
        for record in collab_res:
            response_data["faculty_collaborations"].append({
                "faculty_name": record["faculty_name"],
                "faculty_dept": record["faculty_dept"],
                "faculty_pic": record["faculty_pic"],
                "project_title": record["title"],
                "collaboration_type": record["type"]
            })
            
        return response_data

    finally:
        session.close()


# --- 2. COLLABORATION HUB (Search & Filter) ---
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
        # Dynamic Filter Query
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


# --- 3. SHORTLIST STUDENT ACTION ---
@router.post("/shortlist/{student_id}")
def shortlist_student(student_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"].lower() != "faculty":
        raise HTTPException(status_code=403, detail="Access denied")

    session = db.get_session()
    faculty_id = current_user["user_id"]
    
    try:
        # Check if student exists
        check_q = "MATCH (s:Student {user_id: $sid}) RETURN s"
        if not session.run(check_q, sid=student_id).single():
            raise HTTPException(status_code=404, detail="Student not found")

        # Create Relationship
        query = """
        MATCH (f:Faculty {user_id: $fid}), (s:Student {user_id: $sid})
        MERGE (f)-[:SHORTLISTED]->(s)
        """
        session.run(query, fid=faculty_id, sid=student_id)
        return {"message": "Student shortlisted successfully"}
    finally:
        session.close()