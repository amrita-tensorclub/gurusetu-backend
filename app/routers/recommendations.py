from fastapi import APIRouter, Depends
from app.core.security import get_current_user
from app.services.rag_service import (
    recommend_faculty_for_student,
    recommend_students_for_opening,
)

router = APIRouter(prefix="/recommendations")

@router.get("/faculty")
def faculty_recommendations(current_user=Depends(get_current_user)):
    return recommend_faculty_for_student(current_user["user_id"])


@router.get("/students/{opening_id}")
def student_recommendations(opening_id: str, current_user=Depends(get_current_user)):
    return recommend_students_for_opening(opening_id)
