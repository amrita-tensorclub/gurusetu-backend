from fastapi import APIRouter, Depends, HTTPException
from app.services.rag_service import (
    recommend_faculty_for_student,
    recommend_students_for_opening,
)
from app.core.security import get_current_user

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])


@router.get("/faculty")
def get_faculty_recommendations(current_user=Depends(get_current_user)):
    """
    Student → Faculty recommendations
    """
    if current_user["role"].lower() != "student":
        raise HTTPException(status_code=403, detail="Only students can access this")

    return recommend_faculty_for_student(current_user["user_id"])


@router.get("/students/{opening_id}")
def get_student_recommendations(
    opening_id: str,
    current_user=Depends(get_current_user),
):
    """
    Faculty → Students for a specific opening
    """
    if current_user["role"].lower() != "faculty":
        raise HTTPException(status_code=403, detail="Only faculty can access this")

    return recommend_students_for_opening(opening_id)
