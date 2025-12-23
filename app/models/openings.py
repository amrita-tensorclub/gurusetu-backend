from pydantic import BaseModel
from typing import List

class OpeningCreate(BaseModel):
    faculty_id: str  
    title: str
    description: str
    required_skills: List[str]  