from pydantic import BaseModel
from typing import List, Optional

class OpeningCreate(BaseModel):
    faculty_id: str
    title: str
    description: str
    required_skills: List[str]
    
    # --- ADDED FIELDS FROM UI ---
    expected_duration: str          # UI: "Jan 2024 - May 2024"
    target_years: List[str] = []    # UI: Checkbox "3rd Year/4th Year" -> ["3rd", "4th"]
    min_cgpa: Optional[float] = None # UI: Checkbox "CGPA > 8.0" -> 8.0
    deadline: str                   # UI: "31 Dec 2023"