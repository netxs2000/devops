from pydantic import BaseModel
from typing import Optional
from datetime import date

class PulseSubmission(BaseModel):
    user_email: str
    score: int  # 1-5
    note: Optional[str] = None

class PulseStatus(BaseModel):
    submitted: bool
    message: Optional[str] = None
