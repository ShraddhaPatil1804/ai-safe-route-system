from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class RouteSegment(BaseModel):
    road_id: int
    name: Optional[str] = None
    road_type: Optional[str] = None
    length_meters: float
    safety_score: float
    safety_level: str

class NavigationStep(BaseModel):
    step_number: int
    modifier: str  # 'depart', 'straight', 'left', 'right', 'slight_left', 'slight_right', 'sharp_left', 'sharp_right', 'uturn', 'arrive'
    instruction: str
    distance_meters: float
    distance_text: str
    duration_sec: int
    street_name: str
    safety_score: float
    safety_level: str
    coordinates: List[List[float]]

class RouteResponse(BaseModel):
    route_type: str
    distance_km: float
    estimated_time_minutes: int
    safety_score: float
    safety_level: str
    geometry: Dict[str, Any]  # GeoJSON LineString
    explanation: List[str]
    segments: Optional[List[RouteSegment]] = None
    steps: Optional[List[NavigationStep]] = None
    node_sequence: Optional[List[int]] = None

class RouteComparisonResponse(BaseModel):
    origin: Dict[str, float]
    destination: Dict[str, float]
    fastest: Optional[RouteResponse] = None
    safest: Optional[RouteResponse] = None
    balanced: Optional[RouteResponse] = None
