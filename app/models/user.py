from pydantic import BaseModel
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

class FacultyProfileUpdate(UserBase):
    designation: Optional[str] = None       # UI: Dropdown "Assistant Professor"
    office_hours: Optional[str] = None      # UI: "Mon, Wed, Fri..."
    cabin_block: Optional[str] = None       # UI: "B"
    cabin_floor: Optional[int] = None       # UI: "2"
    cabin_number: Optional[str] = None      # UI: "B-205"
    qualifications: List[str] = []          # UI: Tags "PhD in AI", etc.
    domain_interests: List[str] = []        # UI: "Artificial Intelligence", "Robotics"