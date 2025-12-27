from pydantic import BaseModel, validator
from typing import List, Optional

# --- NEW: Model for a single Project ---
class StudentProject(BaseModel):
    title: str
    from_date: str  # e.g., "Jan 2024"
    to_date: str    # e.g., "May 2024"
    description: str
    tools: List[str] = []

# --- Shared Models ---
class WorkItem(BaseModel):
    title: str
    type: str
    year: str
    outcome: Optional[str] = None
    collaborators: Optional[str] = None

# Base fields shared by everyone
class UserBase(BaseModel):
    name: Optional[str] = None
    profile_picture: Optional[str] = None
    phone: Optional[str] = None 
    department: Optional[str] = None
    bio: Optional[str] = None
    
class StudentProfileUpdate(UserBase):
    batch: Optional[str] = None
    skills: List[str] = []
    interests: List[str] = []
    projects: List[StudentProject] = []  # <--- ADDED THIS FIELD

    @validator('skills')
    def validate_skills_limit(cls, v):
        if len(v) > 20:
            raise ValueError(f'Maximum 20 skills allowed. You have {len(v)}.')
        return v

    @validator('interests')
    def validate_interests_limit(cls, v):
        if len(v) > 20:
            raise ValueError(f'Maximum 20 interests allowed. You have {len(v)}.')
        return v

class FacultyProfileUpdate(UserBase):
    designation: Optional[str] = None
    email: Optional[str] = None
    office_hours: Optional[str] = None
    
    # Cabin Details
    cabin_block: Optional[str] = None
    cabin_floor: Optional[str] = None 
    cabin_number: Optional[str] = None
    
    # Qualifications - These specific lists were missing or misnamed before
    ug_details: List[str] = [] 
    pg_details: List[str] = []
    phd_details: List[str] = []

    # Research
    domain_interests: List[str] = []
    previous_work: List[WorkItem] = []