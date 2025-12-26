from fastapi import APIRouter, Depends, HTTPException
from typing import List
from app.core.security import get_current_user
from app.services.rag_service import (
    recommend_students_for_faculty,
    recommend_students_for_opening,
    recommend_faculty_for_student,
    recommend_openings_for_student
)

router = APIRouter()

# --------------------------------------------------------------------------
# 1. FACULTY ENDPOINTS
# --------------------------------------------------------------------------

@router.get("/faculty/students")
def get_student_recommendations_for_dashboard(
    limit: int = 10,
    current_user: dict = Depends(get_current_user)
):
    """
    Get recommended students for the logged-in Faculty member.
    (General matching based on interests)
    """
    if current_user["role"].lower() != "faculty":
        raise HTTPException(
            status_code=403,
            detail="Only faculty can access this endpoint"
        )

    # Returns list with 'match_score' (percentage) and 'profile_picture'
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
    Get recommended students for a SPECIFIC Opening posted by the faculty.
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
# 2. STUDENT ENDPOINTS
# --------------------------------------------------------------------------

@router.get("/student/mentors")
def get_faculty_mentors(
    limit: int = 10,
    current_user: dict = Depends(get_current_user)
):
    """
    Get recommended Faculty mentors for the logged-in Student.
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
    Get recommended Research Openings for the logged-in Student.
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