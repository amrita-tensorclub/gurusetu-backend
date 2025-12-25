from pydantic import BaseModel
from typing import Optional

class ApplicationCreate(BaseModel):
    """Student applies to opening - opening_id comes from path parameter"""
    pass  # All data comes from auth (user_id) and path (opening_id)

class ApplicationResponse(BaseModel):
    application_id: str
    opening_id: str
    opening_title: str
    faculty_name: str
    status: str
    applied_at: str
    match_score: Optional[int] = None

class ApplicationStatusUpdate(BaseModel):
    status: str  # "pending", "accepted", "rejected"

class ApplicantDetail(BaseModel):
    application_id: str
    student_id: str
    student_name: str
    student_dept: str
    student_batch: str
    student_cgpa: Optional[float]
    student_pic: Optional[str]
    status: str
    applied_at: str
    match_score: Optional[int] = None
    matched_skills: list[str] = []
