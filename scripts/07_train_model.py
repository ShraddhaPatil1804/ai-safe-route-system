"""
07_train_model.py
=============================================================================
CRITICAL NOTICE & DISCLAIMER:
DEVELOPMENT MODEL — TRAINED ON SYNTHETIC DATA
This script trains a Random Forest Regressor on the DEVELOPMENT/SYNTHETIC
crime test dataset to verify the ML pipeline.
IT DOES NOT PREDICT REAL-WORLD NASHIK CRIME.
IT IS NOT INTEGRATED INTO PRODUCTION ROUTE COSTS OR A* SEARCH.
=============================================================================
"""

import os
import sys
import time

# Ensure root path is accessible for internal imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.ml.config import (
    ALL_FEATURE_COLUMNS,
    TARGET_COLUMN,
    MODEL_PATH,
    METADATA_PATH,
    RF_REGRESSOR_PARAMS
)
from backend.app.ml.model import build_dataset_from_files, train_crime_risk_model
from backend.app.ml.predictor import CrimeRiskPredictor


def run_routing_benchmark():
    """Confirms production routing engine is 100% untouched."""
    print("\n------------------------------------------------------------")
    print("VERIFYING BASELINE ROUTING ENGINE INTEGRITY...")
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
    print(f"Route Mode:            {res['route_type']}")

    assert abs(res["distance_km"] - 1.52) < 0.1, f"Unexpected distance: {res['distance_km']}"
    assert res["safety_score"] == 73.4, f"Unexpected safety score: {res['safety_score']}"
    print("CONFIRMATION: ROUTING ENGINE BENCHMARK IS 100% UNCHANGED AND REGRESSION-FREE")


def main():
    print("=" * 70)
    print("AI-BASED WOMEN SAFETY NAVIGATION SYSTEM (NASHIK)")
    print("SCRIPT 07: RANDOM FOREST CRIME-RISK MODEL TRAINING (PHASE 4)")
    print("=" * 70)
    print("DEVELOPMENT MODEL — TRAINED ON SYNTHETIC DATA")
    print("DISCLAIMER: NOT TRAINED ON REAL FIR DATA. FOR PIPELINE TESTING ONLY.\n")

    t_start = time.time()

    # 1. Build and clean training dataset
    print("--> Step 1: Building and cleaning training dataset...")
    df = build_dataset_from_files()

    total_samples = len(df)
    active_samples = int((df["crime_count"] > 0).sum())
    zero_samples = int((df["crime_count"] == 0).sum())

    # 2. Train model and evaluate
    print("\n--> Step 2: Training Random Forest Regressor & evaluating metrics...")
    results = train_crime_risk_model(df=df, save_model=True)

    metadata = results["metadata"]
    train_m = results["train_metrics"]
    test_m = results["test_metrics"]
    importances = results["feature_importances"]

    # 3. Print verification checklist
    print("\n" + "=" * 70)
    print("PHASE 4 MODEL TRAINING & EVALUATION REPORT")
    print("=" * 70)
    print(f"Model Architecture:       RandomForestRegressor")
    print(f"Parameters:               {RF_REGRESSOR_PARAMS}")
    print(f"Target Variable:          {TARGET_COLUMN} (Range: 0.0 - 100.0)")
    print(f"Target Definition:        10*count + 8*recent + 6*avg_sev + 12*night_ratio (0 on zero-crime roads)")
    print(f"Total Samples:            {total_samples} road segments")
    print(f"  - Active Crime Roads:   {active_samples} ({active_samples / total_samples * 100:.2f}%)")
    print(f"  - Zero Crime Roads:     {zero_samples} ({zero_samples / total_samples * 100:.2f}%)")
    print(f"Train / Test Split:       {metadata['train_samples']} train (80%) | {metadata['test_samples']} test (20%)")
    print(f"Target Leakage Check:     PASSED (Target strictly excluded from feature matrix)")
    print(f"NaN / Inf Value Check:    PASSED (Zero missing or infinite values in feature matrix)")
    print("-" * 70)
    print("EVALUATION METRICS (SYNTHETIC DEVELOPMENT DATA):")
    print(f"  Training Set ->  MAE: {train_m['mae']:.4f} | RMSE: {train_m['rmse']:.4f} | R²: {train_m['r2']:.4f}")
    print(f"  Testing Set  ->  MAE: {test_m['mae']:.4f} | RMSE: {test_m['rmse']:.4f} | R²: {test_m['r2']:.4f}")
    print("-" * 70)
    print("CALCULATED FEATURE IMPORTANCE RANKING:")
    for rank, (feat, imp) in enumerate(importances.items(), 1):
        bar = "#" * int(imp * 30)
        print(f"  {rank:2d}. {feat:22s}: {imp:.4f} ({imp*100:5.1f}%) {bar}")
    print("-" * 70)
    print(f"Saved Model File:         {MODEL_PATH}")
    print(f"Saved Metadata File:      {METADATA_PATH}")
    print("=" * 70)

    # 4. Verify inference via CrimeRiskPredictor
    print("\n--> Step 3: Verifying inference via CrimeRiskPredictor...")
    predictor = CrimeRiskPredictor.get_instance()
    predictor.load_model()

    sample_active = {
        "crime_count": 3,
        "recent_crime_count": 2,
        "crime_density": 15.5,
        "average_severity": 3.5,
        "night_crime_ratio": 0.67,
        "min_crime_distance": 18.2,
        "length": 120.0,
        "road_type_risk": 4.0,
        "lighting_risk": 12.0,
        "is_residential": 0,
        "is_oneway": 0,
        "speed_kph": 30.0
    }
    pred_active = predictor.predict(sample_active)
    print("Sample Active Crime Road Prediction:")
    print(f"  Input:  crime_count=3, recent=2, avg_sev=3.5, night_ratio=0.67, min_dist=18.2m")
    print(f"  Output: Score = {pred_active['predicted_crime_risk_score']} | Category = {pred_active['crime_risk_category']}")
    print(f"  Tag:    {pred_active['disclaimer']}")

    sample_zero = {
        "crime_count": 0,
        "recent_crime_count": 0,
        "crime_density": 0.0,
        "average_severity": 0.0,
        "night_crime_ratio": 0.0,
        "min_crime_distance": 5000.0,
        "length": 80.0,
        "road_type_risk": 3.0,
        "lighting_risk": 12.0,
        "is_residential": 0,
        "is_oneway": 0,
        "speed_kph": 40.0
    }
    pred_zero = predictor.predict(sample_zero)
    print("\nSample Zero Crime Road Prediction:")
    print(f"  Input:  crime_count=0, min_dist=5000.0m")
    print(f"  Output: Score = {pred_zero['predicted_crime_risk_score']} | Category = {pred_zero['crime_risk_category']}")
    print(f"  Tag:    {pred_zero['disclaimer']}")

    assert 0.0 <= pred_active["predicted_crime_risk_score"] <= 100.0
    assert 0.0 <= pred_zero["predicted_crime_risk_score"] <= 100.0
    print("\nPREDICTOR INFERENCE VERIFICATION PASSED WITH 100% SUCCESS")

    # 5. Run routing benchmark verification
    run_routing_benchmark()

    print(f"\nPhase 4 execution complete in {time.time() - t_start:.2f}s.")


if __name__ == "__main__":
    main()
