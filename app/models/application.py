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
