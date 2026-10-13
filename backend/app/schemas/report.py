from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ReportCreate(BaseModel):
    report_type: str  # e.g., "Poor Lighting", "Isolated Area", "Suspicious Activity", "Harassment"
    description: Optional[str] = None
    severity: str     # e.g., "Low", "Medium", "High"
    latitude: float
    longitude: float

class ReportOut(BaseModel):
    id: int
    user_id: Optional[int] = None
    report_type: str
    description: Optional[str] = None
    severity: str
    status: str
    latitude: float
    longitude: float
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
