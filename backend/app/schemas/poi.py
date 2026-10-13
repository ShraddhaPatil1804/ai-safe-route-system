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

    class Config:
        from_attributes = True

class POIFilterResponse(BaseModel):
    category: str
    count: int
    items: List[POIOut]
