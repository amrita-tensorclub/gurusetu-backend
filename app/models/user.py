from pydantic import BaseModel, validator
from typing import List, Optional

# --- NEW: Model for a single Project ---
class StudentProject(BaseModel):
    title: str
    from_date: str  # e.g., "Jan 2024"
    to_date: str    # e.g., "May 2024"
    description: str
    tools: List[str] = []

# Base fields shared by everyone
class UserBase(BaseModel):
    name: Optional[str] = None              # UI: Editable Name
    profile_picture: Optional[str] = None   # UI: Camera Icon/Image
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
    office_hours: Optional[str] = None      
    cabin_block: Optional[str] = None       
    cabin_floor: Optional[int] = None       
    cabin_number: Optional[str] = None      
    qualifications: List[str] = []          
    domain_interests: List[str] = []        

    @validator('domain_interests')
    def validate_interests_limit(cls, v):
        if len(v) > 15:
            raise ValueError(f'Maximum 15 research interests allowed. You have {len(v)}.')
        return v