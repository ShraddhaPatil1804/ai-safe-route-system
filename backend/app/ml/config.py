import os

# Geographic bounds for Nashik City development/testing
NASHIK_BOUNDS = {
    "min_lat": 19.90,
    "max_lat": 20.08,
    "min_lon": 73.70,
    "max_lon": 73.88,
}

# PostGIS spatial matching corridor and feature extraction parameters
CRIME_ROAD_BUFFER_METERS = 75.0      # Spatial corridor buffer around road geometry (can be tuned to 50m or 100m)
RECENT_CRIME_WINDOW_DAYS = 365       # 12-month temporal window for recent_crime_count
DEFAULT_NO_CRIME_DISTANCE = 5000.0   # Safe default distance (meters) when no crime exists within corridor

# Crime categories and severity weights (1.0 to 8.0)
CRIME_CATEGORIES = {
    "Harassment / Eve Teasing": 2.5,
    "Stalking": 3.0,
    "Phone / Bag Snatching": 2.0,
    "Theft": 1.5,
    "Verbal Abuse / Intimidation": 2.0,
    "Assault": 4.5,
    "Physical Molestation": 5.0,
    "Robbery": 4.0,
    "Other": 2.0,
}

# Feature lists used for Random Forest training and inference
CRIME_FEATURE_COLS = [
    "crime_count",
    "recent_crime_count",
    "crime_density",
    "average_severity",
    "night_crime_ratio",
    "min_crime_distance",
]

ENVIRONMENT_FEATURE_COLS = [
    "length",
    "road_type_risk",
    "lighting_risk",
    "is_residential",
    "is_oneway",
    "speed_kph",
    "police_distance",
    "hospital_distance",
    "pharmacy_distance",
    "commercial_density",
    "isolation_risk",
    "bar_count",
    "liquor_shop_count",
]

ALL_FEATURE_COLUMNS = CRIME_FEATURE_COLS + ENVIRONMENT_FEATURE_COLS

# Target Column Name (Development Test Target)
TARGET_COLUMN = "development_crime_risk_score"

# Risk Categories based on predicted continuous score [0.0 - 100.0]
CLASS_LABELS = {0: "Low", 1: "Medium", 2: "High"}
LABEL_TO_CLASS = {"Low": 0, "Medium": 1, "High": 2}

def get_crime_risk_category(score: float) -> str:
    if score < 30.0:
        return "Low"
    elif score < 60.0:
        return "Medium"
    else:
        return "High"


# Paths for saved model artifacts
SAVED_MODEL_DIR = os.path.join(os.path.dirname(__file__), "saved_models")
MODEL_PATH = os.path.join(SAVED_MODEL_DIR, "rf_crime_model.joblib")
METADATA_PATH = os.path.join(SAVED_MODEL_DIR, "model_metadata.json")

# Random Forest Regressor Hyperparameters
RF_REGRESSOR_PARAMS = {
    "n_estimators": 100,
    "max_depth": 12,
    "min_samples_split": 5,
    "min_samples_leaf": 2,
    "random_state": 42,
    "n_jobs": -1
}

# =============================================================================
# PHASE 5: TEMPORAL VALIDATION CONFIGURATION
# =============================================================================
TEMPORAL_CUTOFF_DATE = "2024-04-01 00:00:00"
TEMPORAL_RECENT_DAYS = 90  # Historical recent crime window prior to cutoff

TEMPORAL_HISTORICAL_FEATURE_COLS = [
    "historical_crime_count",
    "historical_recent_crime_count",
    "historical_crime_density",
    "historical_average_severity",
    "historical_night_crime_ratio",
    "historical_min_crime_distance",
]

TEMPORAL_ALL_FEATURE_COLUMNS = TEMPORAL_HISTORICAL_FEATURE_COLS + ENVIRONMENT_FEATURE_COLS

TEMPORAL_TARGET_COLUMN = "future_crime_count"

TEMPORAL_MODEL_PATH = os.path.join(SAVED_MODEL_DIR, "rf_crime_model_temporal_dev.joblib")
TEMPORAL_METADATA_PATH = os.path.join(SAVED_MODEL_DIR, "model_metadata_temporal_dev.json")

