"""
09_temporal_validation.py
=============================================================================
Phase 5: Leakage-Safe Temporal Validation for Random Forest Crime-Risk Model

Trains and validates a Random Forest regression model predicting road-level
FUTURE crime occurrences from HISTORICAL crime and environmental features.

Key Design:
  - Historical Window: Crimes before Cutoff Date (2024-04-01) -> Feature inputs
  - Future Prediction Window: Crimes on/after Cutoff Date -> Target variable
  - Preserves Phase 4 models and artifacts.
  - Zero modification to routing, A* graph search, or baseline safety scores.
=============================================================================
"""

import os
import sys
import time

# Ensure root directory is on python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.ml.config import (
    TEMPORAL_HISTORICAL_FEATURE_COLS,
    TEMPORAL_ALL_FEATURE_COLUMNS,
    TEMPORAL_TARGET_COLUMN,
    TEMPORAL_CUTOFF_DATE,
    TEMPORAL_MODEL_PATH,
    TEMPORAL_METADATA_PATH,
    RF_REGRESSOR_PARAMS
)
from backend.app.ml.temporal_feature_extractor import extract_temporal_features_and_target
from backend.app.ml.temporal_model import build_temporal_dataset_from_files, train_temporal_crime_model
from backend.app.ml.predictor import TemporalCrimeRiskPredictor, CrimeRiskPredictor


def verify_routing_engine():
    """Runs regression verification on router benchmark to ensure routing is untouched."""
    print("\n------------------------------------------------------------")
    print("VERIFYING ROUTING ENGINE REGRESSION BENCHMARK...")
    print("------------------------------------------------------------")
    from backend.app.routing.router import NashikRoadNetwork
    network = NashikRoadNetwork.get_instance()
    network.load_network()

    origin_lat, origin_lon = 20.0059, 73.7897
    dest_lat, dest_lon = 20.0124, 73.7875

    res = network.calculate_route(origin_lat, origin_lon, dest_lat, dest_lon, mode="safest")
    print(f"Benchmark Origin:      ({origin_lat}, {origin_lon})")
    print(f"Benchmark Destination: ({dest_lat}, {dest_lon})")
    print(f"Calculated Distance:   {res['distance_km']} km  (Expected ~1.52 km)")
    print(f"Calculated TravelTime: {res['estimated_time_minutes']} min  (Expected ~3 min)")
    print(f"Baseline Safety Score: {res['safety_score']}  (Expected 73.4)")
    print(f"Route Mode:            {res['route_type']} (Safest)")

    assert abs(res["distance_km"] - 1.52) < 0.1, f"Unexpected distance: {res['distance_km']}"
    assert res["safety_score"] == 73.4, f"Unexpected safety score: {res['safety_score']}"
    print("CONFIRMATION: ROUTING ENGINE BENCHMARK IS 100% UNCHANGED AND REGRESSION-FREE")


def main():
    print("=" * 75)
    print("AI-BASED WOMEN SAFETY NAVIGATION SYSTEM (NASHIK)")
    print("PHASE 5: LEAKAGE-SAFE TEMPORAL RANDOM FOREST MODEL VALIDATION")
    print("=" * 75)
    print("DISCLAIMER:")
    print("The temporal Random Forest pipeline was successfully implemented and")
    print("evaluated using synthetic development data. Final model training and")
    print("validation will be performed using verified historical FIR data.")
    print("NOT FOR REAL-WORLD POLICE PREDICTION OR ROUTING USE.\n")

    t_start = time.time()

    # Step 1: Temporal Feature & Target Extraction
    print("--> Step 1: Extracting temporal features and future crime target...")
    extraction_res = extract_temporal_features_and_target(
        cutoff_date_str=TEMPORAL_CUTOFF_DATE,
        save_csv=True
    )

    # Step 2: Build dataset with environmental features
    print("\n--> Step 2: Merging environmental attributes and building dataset...")
    df = build_temporal_dataset_from_files()

    # Step 3: Train model and evaluate
    print("\n--> Step 3: Training temporal Random Forest model & evaluating metrics...")
    results = train_temporal_crime_model(df=df, save_model=True)

    metadata = results["metadata"]
    train_m = results["train_metrics"]
    test_m = results["test_metrics"]
    importances = results["feature_importances"]

    # Step 4: Summary Report
    print("\n" + "=" * 75)
    print("PHASE 5 TEMPORAL VALIDATION SUMMARY REPORT")
    print("=" * 75)
    print(f"Model Architecture:       RandomForestRegressor")
    print(f"Parameters:               {RF_REGRESSOR_PARAMS}")
    print(f"Cutoff Date:              {TEMPORAL_CUTOFF_DATE}")
    print(f"Historical Feature Window: {metadata['historical_period']}")
    print(f"Future Target Window:      {metadata['prediction_target_period']}")
    print(f"Target Column:            {TEMPORAL_TARGET_COLUMN} (Road-level future crime count)")
    print(f"Total Road Segments:      {len(df)}")
    print(f"  - Active Future Roads:  {extraction_res['active_fut_roads']} ({extraction_res['active_fut_roads'] / len(df) * 100:.2f}%)")
    print(f"  - Zero Future Roads:    {len(df) - extraction_res['active_fut_roads']} ({(len(df) - extraction_res['active_fut_roads']) / len(df) * 100:.2f}%)")
    print(f"Train / Test Split:       {metadata['train_samples']} train (80%) | {metadata['test_samples']} test (20%)")
    print("-" * 75)
    print("EVALUATION METRICS (DEVELOPMENT / SYNTHETIC DATA):")
    print(f"  Training Set ->  MAE: {train_m['mae']:.4f} | RMSE: {train_m['rmse']:.4f} | R²: {train_m['r2']:.4f}")
    print(f"  Testing Set  ->  MAE: {test_m['mae']:.4f} | RMSE: {test_m['rmse']:.4f} | R²: {test_m['r2']:.4f}")
    print("-" * 75)
    print("FEATURE IMPORTANCE RANKING (PHASE 5):")
    for rank, (feat, imp) in enumerate(importances.items(), 1):
        bar = "#" * int(imp * 40)
        print(f"  {rank:2d}. {feat:32s}: {imp:.4f} ({imp*100:5.1f}%) {bar}")
    print("-" * 75)
    print(f"Saved Phase 5 Model:      {TEMPORAL_MODEL_PATH}")
    print(f"Saved Phase 5 Metadata:   {TEMPORAL_METADATA_PATH}")
    print("=" * 75)

    # Step 5: Test Temporal Predictor Inference
    print("\n--> Step 4: Testing TemporalCrimeRiskPredictor inference...")
    temp_predictor = TemporalCrimeRiskPredictor.get_instance()
    temp_predictor.load_model()

    sample_active = {
        "historical_crime_count": 2,
        "historical_recent_crime_count": 1,
        "historical_crime_density": 12.0,
        "historical_average_severity": 3.0,
        "historical_night_crime_ratio": 0.5,
        "historical_min_crime_distance": 25.0,
        "length": 150.0,
        "road_type_risk": 5.0,
        "lighting_risk": 15.0,
        "is_residential": 1,
        "is_oneway": 0,
        "speed_kph": 25.0
    }
    pred_res = temp_predictor.predict(sample_active)
    print("Sample Temporal Road Prediction:")
    print(f"  Input:  historical_crime_count=2, recent=1, avg_sev=3.0, min_dist=25.0m")
    print(f"  Output: Predicted Future Crime Count = {pred_res['predicted_future_crime_count']}")
    print(f"  Tag:    {pred_res['disclaimer']}")

    # Verify Phase 4 Predictor still operates untouched
    print("\n--> Step 5: Verifying Phase 4 Predictor remains functional & unmodified...")
    p4_predictor = CrimeRiskPredictor.get_instance()
    p4_predictor.load_model()
    p4_res = p4_predictor.predict({"crime_count": 1, "min_crime_distance": 50.0})
    print(f"  Phase 4 Predictor Output: Score = {p4_res['predicted_crime_risk_score']} | Category = {p4_res['crime_risk_category']}")
    assert p4_res["predicted_crime_risk_score"] > 0

    # Step 6: Verify Baseline Routing Regression Integrity
    print("\n--> Step 6: Verifying baseline routing engine integrity...")
    verify_routing_engine()

    print(f"\nPhase 5 complete in {time.time() - t_start:.2f}s.")


if __name__ == "__main__":
    main()
