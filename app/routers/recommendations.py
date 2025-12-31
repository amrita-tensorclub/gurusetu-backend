from fastapi import APIRouter, Depends, HTTPException, Query
from app.core.security import get_current_user
from app.services.rag_service import (
    recommend_students_for_faculty,
    recommend_students_for_opening,
    recommend_faculty_for_student,
    recommend_openings_for_student,
    semantic_search_students,
    semantic_search_faculty
)

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])

# --------------------------------------------------------------------------
# 1. FACULTY ENDPOINTS (GRAPH-BASED RECOMMENDATIONS)
# --------------------------------------------------------------------------

@router.get("/faculty/students")
def get_student_recommendations_for_dashboard(
    limit: int = 10,
    current_user: dict = Depends(get_current_user)
):
    """
    Get recommended students for the logged-in Faculty member.
    Logic: Shared interests & skills (graph-based)
    """
    if current_user["role"].lower() != "faculty":
        raise HTTPException(
            status_code=403,
            detail="Only faculty can access this endpoint"
        )

    return recommend_students_for_faculty(
        faculty_id=current_user["user_id"],
        limit=limit
    )


@router.get("/openings/{opening_id}/students")
def get_candidates_for_opening(
    opening_id: str,
    limit: int = 10,
    current_user: dict = Depends(get_current_user)
):
    """
    Get recommended students for a SPECIFIC opening.
    Logic: Skill match + CGPA + batch constraints
    """
    if current_user["role"].lower() != "faculty":
        raise HTTPException(
            status_code=403,
            detail="Only faculty can view student recommendations"
        )

    return recommend_students_for_opening(
        opening_id=opening_id,
        limit=limit
    )


# --------------------------------------------------------------------------
# 2. STUDENT ENDPOINTS (GRAPH-BASED RECOMMENDATIONS)
# --------------------------------------------------------------------------

@router.get("/student/mentors")
def get_faculty_mentors(
    limit: int = 10,
    current_user: dict = Depends(get_current_user)
):
    """
    Get recommended Faculty mentors for the logged-in Student.
    Logic: Shared interests (graph-based)
    """
    if current_user["role"].lower() != "student":
        raise HTTPException(
            status_code=403,
            detail="Only students can access faculty recommendations"
        )

    return recommend_faculty_for_student(
        student_id=current_user["user_id"],
        limit=limit
    )


@router.get("/student/openings")
def get_opening_recommendations(
    limit: int = 10,
    current_user: dict = Depends(get_current_user)
):
    """
    Get recommended research openings for the logged-in Student.
    Logic: Skill overlap + constraints
    """
    if current_user["role"].lower() != "student":
        raise HTTPException(
            status_code=403,
            detail="Only students can access opening recommendations"
        )

    return recommend_openings_for_student(
        student_id=current_user["user_id"],
        limit=limit
    )


# --------------------------------------------------------------------------
# 3. SEMANTIC SEARCH ENDPOINTS (VECTOR-BASED)
# --------------------------------------------------------------------------

@router.get("/search/students")
def semantic_student_search(
    q: str = Query(..., description="Search query"),
    limit: int = 5,
    current_user: dict = Depends(get_current_user)
):
    """
    Semantic search for students using vector similarity.
    Example queries:
    - "machine learning and NLP"
    - "python backend developer"
    """
    return semantic_search_students(q, limit)


@router.get("/search/faculty")
def semantic_faculty_search(
    q: str = Query(..., description="Search query"),
    limit: int = 5,
    current_user: dict = Depends(get_current_user)
):
    """
    Semantic search for faculty using research profile embeddings.
    Example queries:
    - "computer networks security"
    - "deep learning researcher"
    """
    return semantic_search_faculty(q, limit)
