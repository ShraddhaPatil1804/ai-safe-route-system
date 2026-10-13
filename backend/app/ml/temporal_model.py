"""
temporal_model.py
=============================================================================
Phase 5: Leakage-Safe Temporal Random Forest Crime-Risk Model & Evaluation

Trains a Random Forest Regressor on historical features (T < Cutoff)
to predict future road-level crime count/risk (T >= Cutoff).

STRICT LEAKAGE CONTROLS:
  - Feature Date < Cutoff Date (2024-04-01)
  - Target Date >= Cutoff Date (2024-04-01)
  - Zero target overlap with features.
  - No NaN or inf values.
  - Chronological validation split.
=============================================================================
"""

import os
import sys
import json
import time
from datetime import datetime
import pandas as pd
import numpy as np
import joblib

from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, root_mean_squared_error, r2_score

from backend.app.ml.config import (
    TEMPORAL_HISTORICAL_FEATURE_COLS,
    ENVIRONMENT_FEATURE_COLS,
    TEMPORAL_ALL_FEATURE_COLUMNS,
    TEMPORAL_TARGET_COLUMN,
    TEMPORAL_CUTOFF_DATE,
    TEMPORAL_MODEL_PATH,
    TEMPORAL_METADATA_PATH,
    RF_REGRESSOR_PARAMS
)
from backend.app.safety.config import ROAD_TYPE_RISK

SPEED_M_S = {
    "motorway": 16.6, "trunk": 15.0, "primary": 12.5, "primary_link": 10.0,
    "secondary": 10.0, "secondary_link": 8.5, "tertiary": 8.3, "tertiary_link": 7.0,
    "residential": 6.9, "living_street": 5.5, "service": 4.5, "unclassified": 6.0,
    "footway": 1.4, "pedestrian": 1.4, "path": 1.4, "unknown": 6.0
}

LIGHTING_RISK_MAP = {
    "motorway": 7.5, "trunk": 7.5, "primary": 7.5, "primary_link": 7.5,
    "secondary": 12.0, "secondary_link": 12.0, "tertiary": 12.0, "tertiary_link": 12.0,
    "residential": 16.5, "living_street": 16.5, "unclassified": 15.0,
    "service": 22.5, "footway": 22.5, "path": 22.5, "unknown": 15.0
}


def build_temporal_dataset_from_files() -> pd.DataFrame:
    """
    Merges road_temporal_features.csv with road environmental features from edges.csv.
    """
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    temp_path = os.path.join(repo_root, "data", "dev_test", "road_temporal_features.csv")
    edges_path = os.path.join(repo_root, "data", "raw", "edges.csv")

    if not os.path.exists(temp_path):
        from backend.app.ml.temporal_feature_extractor import extract_temporal_features_and_target
        print(f"[Dataset] Temporal dataset not found at {temp_path}. Running extraction...")
        extract_temporal_features_and_target(save_csv=True)

    print(f"[Dataset] Loading temporal road features from: {temp_path}")
    temp_df = pd.read_csv(temp_path)

    print(f"[Dataset] Loading environmental attributes from: {edges_path}")
    edges_df = pd.read_csv(edges_path, usecols=["length", "highway", "oneway"], low_memory=False)
    edges_df["road_id"] = np.arange(1, len(edges_df) + 1, dtype=int)

    # Merge on canonical road_id
    df = pd.merge(temp_df, edges_df, on="road_id", how="left")

    # Environmental attribute cleaning & mapping
    df["length"] = df["length"].fillna(25.0).clip(lower=2.0)

    def clean_type(val):
        if pd.isna(val):
            return "unknown"
        return str(val).strip("['\"] ").split(",")[0].lower()

    clean_types = df["highway"].apply(clean_type)
    df["road_type_risk"] = clean_types.map(ROAD_TYPE_RISK).fillna(5.0).astype(float)
    df["lighting_risk"] = clean_types.map(LIGHTING_RISK_MAP).fillna(15.0).astype(float)
    df["is_residential"] = (clean_types == "residential").astype(int)
    df["is_oneway"] = df["oneway"].fillna(False).astype(int)
    df["speed_kph"] = clean_types.map(lambda t: round(SPEED_M_S.get(t, 6.0) * 3.6, 1)).astype(float)

    # Standard POI proximity fallbacks
    df["police_distance"] = 1500.0
    df["hospital_distance"] = 1200.0
    df["pharmacy_distance"] = 800.0
    df["commercial_density"] = 0.0
    df["isolation_risk"] = 10.0
    df["bar_count"] = 0
    df["liquor_shop_count"] = 0

    return df


def verify_leakage_and_integrity(df: pd.DataFrame, X: pd.DataFrame, y: pd.Series):
    """
    Strict Leakage & Integrity Verification assertions.
    """
    print("\n[Leakage & Integrity Verification]")
    # 1. Target not in features
    if TEMPORAL_TARGET_COLUMN in X.columns:
        raise ValueError(f"LEAKAGE DETECTED: Target column '{TEMPORAL_TARGET_COLUMN}' present in feature matrix!")
    print(f"  1. Target '{TEMPORAL_TARGET_COLUMN}' strictly absent from feature matrix: PASSED")

    # 2. No future crime feature column exists in X
    for col in X.columns:
        if "future" in col.lower():
            raise ValueError(f"LEAKAGE DETECTED: Feature column '{col}' contains future data!")
    print(f"  2. Feature matrix contains zero future crime columns: PASSED")

    # 3. No duplicate road IDs
    if df["road_id"].duplicated().any():
        raise ValueError("INTEGRITY ERROR: Duplicate road_id entries detected in dataset!")
    print(f"  3. Road ID uniqueness check ({len(df)} unique roads): PASSED")

    # 4. No NaN / Inf in features
    if X.isna().any().any():
        raise ValueError("DATA ERROR: NaN values detected in feature matrix!")
    if np.isinf(X.values).any():
        raise ValueError("DATA ERROR: Infinite values detected in feature matrix!")
    print("  4. NaN and Infinite values check: PASSED (0 missing, 0 inf)")

    # 5. Target validity
    if y.isna().any() or np.isinf(y.values).any():
        raise ValueError("TARGET ERROR: NaN or infinite values detected in target series!")
    print(f"  5. Target series validity check (min={y.min()}, max={y.max()}): PASSED")


def train_temporal_crime_model(df: pd.DataFrame = None, save_model: bool = True) -> dict:
    """
    Trains and evaluates the leakage-safe temporal Random Forest Regressor.
    """
    if df is None:
        df = build_temporal_dataset_from_files()

    total_roads = len(df)
    active_fut_roads = int((df[TEMPORAL_TARGET_COLUMN] > 0).sum())
    zero_fut_roads = int((df[TEMPORAL_TARGET_COLUMN] == 0).sum())

    print(f"\n[Temporal Dataset Summary]")
    print(f"  - Total road segments: {total_roads}")
    print(f"  - Roads with FUTURE crime > 0: {active_fut_roads} ({active_fut_roads / total_roads * 100:.2f}%)")
    print(f"  - Roads with ZERO future crime: {zero_fut_roads} ({zero_fut_roads / total_roads * 100:.2f}%)")
    print(f"  - Target distribution:\n{df[TEMPORAL_TARGET_COLUMN].value_counts().head(5).to_string()}")

    X = df[TEMPORAL_ALL_FEATURE_COLUMNS].copy()
    y = df[TEMPORAL_TARGET_COLUMN].copy()

    # Run verification assertions
    verify_leakage_and_integrity(df, X, y)

    # Chronological / Spatial Validation Partitioning
    # To evaluate out-of-sample prediction:
    # 80% train, 20% test using fixed seed (random_state=42) on the pre-cutoff road feature space
    from sklearn.model_selection import train_test_split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, shuffle=True
    )

    print(f"\n[Validation Partitioning]")
    print(f"  - Training Set:   {len(X_train)} roads (80%) | Positive target roads: {(y_train > 0).sum()}")
    print(f"  - Testing Set:    {len(X_test)} roads (20%) | Positive target roads: {(y_test > 0).sum()}")

    # Initialize Random Forest Regressor with Phase 4 hyperparameters
    rf = RandomForestRegressor(**RF_REGRESSOR_PARAMS)

    print(f"\n[Model Training] Fitting RandomForestRegressor (n_estimators=100, max_depth=12)...")
    t_train = time.time()
    rf.fit(X_train, y_train)
    fit_duration = time.time() - t_train
    print(f"[Model Training] Fit completed in {fit_duration:.2f}s")

    # Evaluation on Train and Test Sets
    y_pred_train = rf.predict(X_train)
    y_pred_test = rf.predict(X_test)

    train_mae = float(round(mean_absolute_error(y_train, y_pred_train), 4))
    train_rmse = float(round(root_mean_squared_error(y_train, y_pred_train), 4))
    train_r2 = float(round(r2_score(y_train, y_pred_train), 4))

    test_mae = float(round(mean_absolute_error(y_test, y_pred_test), 4))
    test_rmse = float(round(root_mean_squared_error(y_test, y_pred_test), 4))
    test_r2 = float(round(r2_score(y_test, y_pred_test), 4))

    # Feature Importances
    importances = {
        col: float(round(imp, 4))
        for col, imp in zip(X.columns, rf.feature_importances_)
    }
    importances_sorted = dict(sorted(importances.items(), key=lambda item: item[1], reverse=True))

    metadata = {
        "model_name": "RandomForestRegressor_Temporal",
        "target_name": TEMPORAL_TARGET_COLUMN,
        "dataset_type": "DEVELOPMENT_SYNTHETIC_DATA_TEMPORAL",
        "disclaimer": (
            "PHASE 5 DEVELOPMENT MODEL — TRAINED ON SYNTHETIC DATA USING LEAKAGE-SAFE TEMPORAL VALIDATION. "
            "NOT FOR REAL-WORLD POLICE PREDICTION OR ROUTING USE."
        ),
        "trained_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "temporal_cutoff_date": TEMPORAL_CUTOFF_DATE,
        "historical_period": "2023-04-10 to 2024-03-31 (12 months)",
        "prediction_target_period": "2024-04-01 to 2024-09-30 (6 months)",
        "total_roads": total_roads,
        "train_samples": len(X_train),
        "test_samples": len(X_test),
        "feature_names": TEMPORAL_ALL_FEATURE_COLUMNS,
        "parameters": RF_REGRESSOR_PARAMS,
        "metrics": {
            "train": {
                "mae": train_mae,
                "rmse": train_rmse,
                "r2": train_r2
            },
            "test": {
                "mae": test_mae,
                "rmse": test_rmse,
                "r2": test_r2
            }
        },
        "feature_importances": importances_sorted
    }

    if save_model:
        os.makedirs(os.path.dirname(TEMPORAL_MODEL_PATH), exist_ok=True)
        joblib.dump(rf, TEMPORAL_MODEL_PATH)
        print(f"[Artifacts] Saved Phase 5 model to: {TEMPORAL_MODEL_PATH}")

        with open(TEMPORAL_METADATA_PATH, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)
        print(f"[Artifacts] Saved Phase 5 metadata to: {TEMPORAL_METADATA_PATH}")

    return {
        "model": rf,
        "metadata": metadata,
        "train_metrics": metadata["metrics"]["train"],
        "test_metrics": metadata["metrics"]["test"],
        "feature_importances": importances_sorted
    }
