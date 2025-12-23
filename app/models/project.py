from pydantic import BaseModel
from typing import List, Optional

class StudentWorkCreate(BaseModel):
    user_id: str
    title: str          # e.g. "Efficient Energy Management..."
    type: str           # "Project" or "Publication"
    year: str           # e.g. "2023"
    collaborators: str  # e.g. "Dr. A. Sharma, Mr. P. Verma"
    outcome: str        # "Published in IEEE IoT Journal..."
    tools_used: List[str] = [] # Optional: Technical tools if applicable