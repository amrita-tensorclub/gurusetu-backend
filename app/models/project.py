from pydantic import BaseModel
from typing import List, Optional

class StudentWorkCreate(BaseModel):
    title: str
    type: str             # "Project" or "Publication"
    
    # --- New Fields matching UI ---
    description: str      # "Brief Description (200 chars)"
    start_date: str       # "Jan 2024"
    end_date: str         # "May 2024"
    # ------------------------------

    year: Optional[str] = None
    collaborators: Optional[str] = None
    outcome: Optional[str] = None
    tools_used: List[str] = []
    
# --- NEW FIELD FOR FACULTY DASHBOARD ---
    # Example values: "Seeking Co-PI", "Joint Research", "Open for Students"
    collaboration_type: Optional[str] = None