from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class CrimeRiskFactors(BaseModel):
    crime_count: int
    recent_crime_count: int
    crime_density: float
    average_severity: float
    night_crime_ratio: float
    min_crime_distance_meters: float

class RoadCrimeRiskResponse(BaseModel):
    road_id: int
    road_name: Optional[str] = None
    road_type: Optional[str] = None
    predicted_crime_risk: str  # 'Low', 'Medium', 'High'
    predicted_risk_prob: float # Class probability for highest-risk or assigned category
    is_development_dataset: bool = True
    data_disclaimer: str = "ML Crime Risk layer currently running on DEVELOPMENT/SYNTHETIC test dataset. Real FIR data will be integrated when available."
    crime_factors: CrimeRiskFactors
    environmental_factors: Optional[Dict[str, Any]] = None

class ModelMetadataResponse(BaseModel):
    model_name: str
    model_type: str
    dataset_type: str
    dataset_disclaimer: str
    model_trained: bool
    feature_names: List[str]
    feature_importances: Dict[str, float]
    classes: List[str]
    metrics: Optional[Dict[str, Any]] = None
