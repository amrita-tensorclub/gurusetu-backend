from pydantic import BaseModel
from typing import List, Optional

class OpeningCreate(BaseModel):
    title: str
    description: str
    required_skills: List[str]

    # UI-driven fields
    expected_duration: str                 # "Jan 2024 - May 2024"
    target_years: List[str] = []            # ["3rd", "4th"]
    min_cgpa: Optional[float] = None        # 8.0
    deadline: str                           # "31 Dec 2023"
