from pydantic import BaseModel
from typing import Optional, List

class POIOut(BaseModel):
    id: int
    osm_id: Optional[int] = None
    name: Optional[str] = None
    category: str
    latitude: float
    longitude: float
    distance_meters: Optional[float] = None
    address: Optional[str] = None
    opening_hours: Optional[str] = None
    is_24_7: Optional[bool] = False
    is_emergency_safe_haven: Optional[bool] = False

    class Config:
        from_attributes = True

class POIFilterResponse(BaseModel):
    category: str
    count: int
    items: List[POIOut]
