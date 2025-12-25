from pydantic import BaseModel, validator
from typing import List, Optional

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
    designation: Optional[str] = None       # UI: Dropdown "Assistant Professor"
    office_hours: Optional[str] = None      # UI: "Mon, Wed, Fri..."
    cabin_block: Optional[str] = None       # UI: "B"
    cabin_floor: Optional[int] = None       # UI: "2"
    cabin_number: Optional[str] = None      # UI: "B-205"
    qualifications: List[str] = []          # UI: Tags "PhD in AI", etc.
    domain_interests: List[str] = []        # UI: "Artificial Intelligence", "Robotics"

    @validator('domain_interests')
    def validate_interests_limit(cls, v):
        if len(v) > 15:
            raise ValueError(f'Maximum 15 research interests allowed. You have {len(v)}.')
        return v