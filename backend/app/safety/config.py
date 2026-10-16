"""
Safety Scoring & Routing Configuration
All weights and risk parameters are configurable design assumptions.
Supports time-aware environmental safety (day vs night) and transparent
distinction between estimated infrastructure safety and unknown crime data.
"""

from typing import Dict, Any, Optional

# Road type base risk weights
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
    "pedestrian": 5.0,
    "footway": 8.0,
    "path": 8.0,
    "steps": 8.0,
    "track": 8.0,
    "unknown": 5.0
}

# Road hierarchy lighting defaults (higher is better lit)
ROAD_LIGHTING_DEFAULTS = {
    "motorway": 0.85,
    "trunk": 0.85,
    "primary": 0.80,
    "primary_link": 0.75,
    "secondary": 0.70,
    "secondary_link": 0.65,
    "tertiary": 0.60,
    "tertiary_link": 0.55,
    "residential": 0.45,
    "living_street": 0.40,
    "service": 0.30,
    "unclassified": 0.40,
    "footway": 0.25,
    "pedestrian": 0.50,
    "path": 0.20,
    "steps": 0.25,
    "track": 0.15,
    "unknown": 0.40
}

# Lighting Configuration:
# Day: Natural sunlight mitigates lighting deficiency
DAY_LIGHTING_MAX_RISK = 12.0
# Night: Streetlights and thoroughfare illumination are paramount
NIGHT_LIGHTING_MAX_RISK = 35.0

MAX_LIGHTING_LEVEL = 1.0
DEFAULT_LIGHTING_LEVEL = 0.5
LIGHTING_MAX_RISK = 30.0

# Crowd / Activity Proxy Configuration
CROWD_MAX_RISK = 20.0
MAX_CROWD_DENSITY = 0.05

# Activity categories considered for natural surveillance and foot traffic
ACTIVITY_CATEGORIES = [
    "restaurant",
    "cafe",
    "shop",
    "supermarket",
    "mall",
    "bank",
    "bus_stop",
    "clinic",
    "atm",
    "hotel"
]

EDUCATIONAL_CATEGORIES = [
    "college",
    "school",
    "university"
]

# Isolation Risk thresholds (Time-aware)
def calculate_isolation_risk(activity_count: int, is_night: bool = False) -> float:
    """
    Computes environmental isolation risk based on nearby active venues.
    After dark, isolation risk is amplified as streets empty out.
    """
    if is_night:
        if activity_count == 0:
            return 22.0
        elif activity_count <= 2:
            return 12.0
        elif activity_count <= 4:
            return 6.0
        else:
            return 0.0
    else:
        if activity_count == 0:
            return 14.0
        elif activity_count <= 2:
            return 8.0
        elif activity_count <= 4:
            return 4.0
        else:
            return 0.0

# Liquor & Bar Risk
LIQUOR_RISK_PER_COUNT = 2.0
MAX_LIQUOR_RISK = 10.0
BAR_RISK_PER_COUNT = 1.5
MAX_BAR_RISK = 8.0

# Nighttime alcohol risk multiplier
NIGHT_ALCOHOL_MULTIPLIER = 1.8

# Emergency Safe Haven Bonuses
MAX_EMERGENCY_BONUS = 18.0
POLICE_BONUS_MAX = 10.0
POLICE_BONUS_SCALE = 120.0

HOSPITAL_BONUS_MAX = 5.0
HOSPITAL_BONUS_SCALE = 200.0

PHARMACY_BONUS_MAX = 4.0
PHARMACY_BONUS_SCALE = 150.0

# Missing Crime Data Handling
CRIME_DATA_STATUS_UNKNOWN = "unknown"
MISSING_CRIME_DATA_DISCLAIMER = (
    "Safety score is an estimated environmental index based on OSM road lighting hierarchy, "
    "natural surveillance, foot traffic, and verified emergency facilities. Missing police "
    "crime records are treated as unknown risk rather than zero risk."
)

# Safety Levels & Thresholds
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

# Comprehensive Safety Computation for Road Segments
def calculate_segment_safety(
    road_type: str,
    lighting_score: float,
    d_police: float,
    d_hospital: float,
    d_pharmacy: float,
    d_pharmacy_24h: float,
    commercial_count: int,
    educational_count: int,
    bar_count: int,
    liquor_count: int,
    is_night: bool = False
) -> Dict[str, Any]:
    """
    Computes time-aware safety score and individual factor breakdowns.
    Reduces activity benefit of closed schools/colleges at night.
    Increases relative importance of lighting and isolation after dark.
    Uses verified 24-hour pharmacies at night.
    """
    # 1. Effective Activity Count
    # During day: schools & colleges contribute significantly to footfall and surveillance
    # At night: schools & colleges are closed; activity benefit drops to zero
    effective_activity = commercial_count + (0 if is_night else educational_count)

    # 2. Lighting Risk
    l_scale = NIGHT_LIGHTING_MAX_RISK if is_night else DAY_LIGHTING_MAX_RISK
    lighting_risk = l_scale * (1.0 - max(0.0, min(1.0, lighting_score)))

    # 3. Isolation Risk
    isolation_risk = calculate_isolation_risk(effective_activity, is_night=is_night)

    # 4. Alcohol Risk
    bar_mult = NIGHT_ALCOHOL_MULTIPLIER if is_night else 1.0
    bar_risk = min(MAX_BAR_RISK, BAR_RISK_PER_COUNT * bar_mult * bar_count)
    liquor_risk = min(MAX_LIQUOR_RISK, LIQUOR_RISK_PER_COUNT * bar_mult * liquor_count)

    # 5. Road Type Risk
    road_risk = ROAD_TYPE_RISK.get(road_type, 5.0)

    # 6. Emergency Safe Haven Bonuses
    police_bonus = max(0.0, POLICE_BONUS_MAX - (d_police / POLICE_BONUS_SCALE))
    hospital_bonus = max(0.0, HOSPITAL_BONUS_MAX - (d_hospital / HOSPITAL_BONUS_SCALE))

    # At night, only verified 24/7 pharmacies provide emergency safe haven bonus
    target_pharm_d = d_pharmacy_24h if is_night else min(d_pharmacy, d_pharmacy_24h)
    pharmacy_bonus = max(0.0, PHARMACY_BONUS_MAX - (target_pharm_d / PHARMACY_BONUS_SCALE))

    emergency_bonus = min(MAX_EMERGENCY_BONUS, police_bonus + hospital_bonus + pharmacy_bonus)

    # 7. Total Risk & Final Score
    total_risk = lighting_risk + isolation_risk + bar_risk + liquor_risk + road_risk
    raw_score = 100.0 - total_risk + emergency_bonus
    final_score = round(max(5.0, min(100.0, raw_score)), 1)

    return {
        "final_safety_score": final_score,
        "safety_level": get_safety_level(final_score),
        "is_night": is_night,
        "lighting_risk": round(lighting_risk, 1),
        "isolation_risk": round(isolation_risk, 1),
        "bar_risk": round(bar_risk, 1),
        "liquor_risk": round(liquor_risk, 1),
        "road_risk": round(road_risk, 1),
        "emergency_bonus": round(emergency_bonus, 1),
        "effective_activity": effective_activity,
        "crime_data_status": CRIME_DATA_STATUS_UNKNOWN
    }

# Routing Cost Modes & Descriptions
ROUTE_MODES = {
    "shortest": {
        "cost_type": "distance",
        "description": "Shortest physical road distance in kilometers"
    },
    "fastest": {
        "cost_type": "time",
        "description": "Shortest travel time prioritizing high-speed thoroughfares"
    },
    "safest": {
        "cost_type": "safety",
        "description": "Maximized safety route prioritizing well-lit avenues, active commercial zones, and emergency facilities"
    },
    "balanced": {
        "cost_type": "balanced",
        "description": "Medium route with enhanced safety — trading a small amount of time to bypass dark or isolated streets"
    }
}
