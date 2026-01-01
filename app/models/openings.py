from pydantic import BaseModel
from typing import List, Optional
from datetime import date


class OpeningCreate(BaseModel):
    title: str
    description: str
    required_skills: List[str]

    # UI-driven fields
    expected_duration: str                 # "Jan 2024 - May 2024"
    target_years: List[str] = []            # ["3rd", "4th"]
    min_cgpa: Optional[float] = None        # 8.0
    deadline: date                           # "31 Dec 2023"


class OpeningUpdate(BaseModel):
    """All fields optional for partial updates."""
    title: Optional[str] = None
    description: Optional[str] = None
    required_skills: Optional[List[str]] = None
    expected_duration: Optional[str] = None
    target_years: Optional[List[str]] = None
    min_cgpa: Optional[float] = None
    deadline: Optional[date] = None
    status: Optional[str] = None  # "Active" or "Closed"
