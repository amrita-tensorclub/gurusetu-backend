from pydantic import BaseModel, validator
from typing import List, Optional

# --- Shared Models ---
class WorkItem(BaseModel):
    title: str
    type: str
    year: str
    outcome: Optional[str] = ""
    collaborators: Optional[str] = ""

class PublicationItem(BaseModel):
    title: str
    year: str
    publisher: Optional[str] = ""
    link: Optional[str] = ""

class ProjectCreate(BaseModel):
    title: str
    description: str
    # Make sure this line exists
    duration: Optional[str] = "" 
    from_date: Optional[str] = ""
    to_date: Optional[str] = ""
    tools: List[str] = []

# --- Student Profile Model ---
class StudentProfileUpdate(BaseModel):
    name: Optional[str] = None
    profile_picture: Optional[str] = None
    phone: Optional[str] = None
    department: Optional[str] = None
    batch: Optional[str] = None
    bio: Optional[str] = None
    
    skills: List[str] = []
    interests: List[str] = []
    
    projects: List[ProjectCreate] = []
    publications: List[PublicationItem] = []

    @validator('skills')
    def validate_skills_limit(cls, v):
        if len(v) > 20:
            raise ValueError(f'Maximum 20 skills allowed. You have {len(v)}.')
        return v

# --- Faculty Profile Model ---
class FacultyProfileUpdate(BaseModel):
    name: Optional[str] = None
    profile_picture: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    designation: Optional[str] = None
    department: Optional[str] = None
    office_hours: Optional[str] = None
    
    cabin_block: Optional[str] = None
    cabin_floor: Optional[str] = None
    cabin_number: Optional[str] = None
    
    ug_details: List[str] = []
    pg_details: List[str] = []
    phd_details: List[str] = []
    
    domain_interests: List[str] = []
    previous_work: List[WorkItem] = []