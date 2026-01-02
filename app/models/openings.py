from pydantic import BaseModel
from typing import List, Optional
from datetime import date

class OpeningCreate(BaseModel):
    title: str
    description: str
    required_skills: List[str]
    
    # UI-driven fields
    expected_duration: str
    target_years: List[str] = []
    min_cgpa: Optional[float] = None
    deadline: date
    
    # --- THIS FIELD IS MANDATORY FOR COLLABORATIONS ---
    collaboration_type: Optional[str] = None