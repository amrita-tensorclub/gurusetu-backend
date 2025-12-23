from pydantic import BaseModel
from typing import List, Optional

# Base fields shared by everyone
class UserBase(BaseModel):
    phone: Optional[str] = None
    department: Optional[str] = None
    bio: Optional[str] = None

class StudentProfileUpdate(BaseModel):
    phone: str
    department: str
    batch: int
    bio: str
    skills: list[str]
    interests: list[str]


class FacultyProfileUpdate(BaseModel):
    phone: str
    department: str
    bio: str
    designation: str
    office_hours: str
    cabin_block: str
    cabin_floor: int
    cabin_number: str
    qualifications: list[str]
