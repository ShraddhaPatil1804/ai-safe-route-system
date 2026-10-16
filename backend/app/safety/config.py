"""
Safety Scoring & Routing Configuration
All weights and risk parameters are configurable design assumptions.
"""

# Road type risk weights (Section 15)
ROAD_TYPE_RISK = {
    "motorway": 2.0,
    "trunk": 2.0,
    "primary": 2.0,
    "primary_link": 2.5,
    "secondary": 3.0,
    "secondary_link": 3.5,
    "tertiary": 4.0,
    "tertiary_link": 4.5,
    "residential": 6.0,
    "living_street": 6.0,
    "unclassified": 5.0,
    "service": 7.0,
    "pedestrian": 6.0,
    "footway": 8.0,
    "path": 8.0,
    "steps": 8.0,
    "track": 8.0,
    "unknown": 5.0
}

# Lighting Configuration (Section 10)
# LightingRisk = 30 * (1 - L)
MAX_LIGHTING_LEVEL = 1.0
DEFAULT_LIGHTING_LEVEL = 0.5  # Neutral default for unrecorded OSM lighting
LIGHTING_MAX_RISK = 30.0

# Crowd / Activity Proxy Configuration (Section 11)
# CrowdRisk = 20 * (1 - C)
CROWD_MAX_RISK = 20.0
# Reference maximum crowd density: 5 activity POIs per 100 meters (0.05 POIs/meter)
MAX_CROWD_DENSITY = 0.05

# Activity categories considered for crowd proxy
ACTIVITY_CATEGORIES = [
    "restaurant",
    "cafe",
    "supermarket",
    "mall",
    "bank",
    "bus_stop",
    "clinic",
    "atm",
    "hotel"
]

# Isolation Risk thresholds (Section 12)
def calculate_isolation_risk(activity_count: int) -> float:
    if activity_count == 0:
        return 15.0
    elif activity_count <= 2:
        return 10.0
    elif activity_count <= 5:
        return 5.0
    else:
        return 0.0

# Liquor & Bar Risk (Sections 13 & 14)
# LiquorRisk = min(10, 2 * LiquorShopCount)
LIQUOR_RISK_PER_COUNT = 2.0
MAX_LIQUOR_RISK = 10.0

# BarRisk = min(8, 1.5 * BarCount)
BAR_RISK_PER_COUNT = 1.5
MAX_BAR_RISK = 8.0

# Emergency Bonus (Section 16)
# PoliceScore = max(0, 10 - DistanceToPolice / 100)
# HospitalScore = max(0, 5 - DistanceToHospital / 200)
# PharmacyScore = max(0, 3 - DistanceToPharmacy / 200)
# EmergencyBonus = min(15, PoliceScore + HospitalScore + PharmacyScore)
MAX_EMERGENCY_BONUS = 15.0
POLICE_BONUS_MAX = 10.0
POLICE_BONUS_SCALE = 100.0

HOSPITAL_BONUS_MAX = 5.0
HOSPITAL_BONUS_SCALE = 200.0

PHARMACY_BONUS_MAX = 3.0
PHARMACY_BONUS_SCALE = 200.0

# Safety Levels (Section 17)
def get_safety_level(score: float) -> str:
    if score >= 80.0:
        return "Very Safe"
    elif score >= 65.0:
        return "Safe"
    elif score >= 50.0:
        return "Moderate"
    elif score >= 35.0:
        return "Risky"
    else:
        return "High Risk"

# Routing Cost Modes & Weights
ROUTE_MODES = {
    "fastest": {
        "distance_weight": 0.0,
        "time_weight": 1.0,
        "safety_weight": 0.0,
        "description": "Shortest travel time prioritizing high-speed thoroughfares"
    },
    "balanced": {
        "distance_weight": 0.0,
        "time_weight": 1.0,
        "safety_weight": 1.5,
        "description": "Medium route with enhanced safety — safer than fastest, trading a small amount of time to avoid dark or isolated roads"
    },
    "safest": {
        "distance_weight": 0.0,
        "time_weight": 0.8,
        "safety_weight": 5.0,
        "description": "Maximized safety route prioritizing well-lit avenues, active commercial zones, and emergency facilities"
    }
}

