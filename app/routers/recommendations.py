from fastapi import APIRouter, Depends, HTTPException
from app.core.security import get_current_user
from app.services.rag_service import recommend_students_for_faculty
from app.services.rag_service import recommend_students_for_opening
from app.services.rag_service import recommend_faculty_for_student

router = APIRouter()


@router.get("/faculty/students")
def faculty_dashboard_recommendations(
    current_user=Depends(get_current_user),
):
    if current_user["role"].lower() != "faculty":
        raise HTTPException(
            status_code=403,
            detail="Only faculty can access this endpoint"
        )

    return recommend_students_for_faculty(
        faculty_id=current_user["user_id"]
    )



@router.get("/openings/{opening_id}/students")
def opening_student_recommendations(
    opening_id: str,
    current_user=Depends(get_current_user),
):
    if current_user["role"].lower() != "faculty":
        raise HTTPException(
            status_code=403,
            detail="Only faculty can view student recommendations"
        )

    return recommend_students_for_opening(
        opening_id=opening_id,
        faculty_id=current_user["user_id"],
    )

@router.get("/recommendations/faculty")
def student_recommend_faculty(
    current_user: dict = Depends(get_current_user),
):
    if current_user["role"].lower() != "student":
        raise HTTPException(
            status_code=403,
            detail="Only students can access faculty recommendations",
        )

    return recommend_faculty_for_student(
        student_id=current_user["user_id"]
    )
