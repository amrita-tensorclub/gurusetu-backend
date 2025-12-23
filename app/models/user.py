from pydantic import BaseModel
from typing import List, Optional

# Base fields shared by everyone
class UserBase(BaseModel):
    phone: Optional[str] = None
    department: Optional[str] = None
    bio: Optional[str] = None

# Fields specific to Students (Batch, Skills, Interests)
class StudentProfileUpdate(UserBase):
    user_id: str
    batch: Optional[str] = None       # e.g., "2022-2026"
    skills: List[str] = []            # e.g., "Python", "React" (What they KNOW)
    interests: List[str] = []         # e.g., "IoT", "Blockchain" (What they want to LEARN)

# Fields specific to Faculty (Cabin, Office Hours, Qualifications)
class FacultyProfileUpdate(UserBase):
    user_id: str
    designation: Optional[str] = None # e.g., "Assistant Professor"
    office_hours: Optional[str] = None
    cabin_block: Optional[str] = None
    cabin_floor: Optional[str] = None
    cabin_number: Optional[str] = None
    qualifications: List[str] = []    # e.g., ["PhD in AI", "M.Tech"]