"""
model.py
=============================================================================
Random Forest Crime-Risk Model Training & Evaluation Engine

DISCLAIMER:
This model is trained on a clearly labelled SYNTHETIC DEVELOPMENT/TEST DATASET.
It is built strictly to verify the ML engineering infrastructure and pipeline.
IT IS NOT TRAINED ON REAL POLICE FIR DATA.
NO REAL-WORLD CRIME PREDICTION ACCURACY IS CLAIMED OR IMPLIED.
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
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, root_mean_squared_error, r2_score

from backend.app.ml.config import (
    ALL_FEATURE_COLUMNS,
    TARGET_COLUMN,
    SAVED_MODEL_DIR,
    MODEL_PATH,
    METADATA_PATH,
    RF_REGRESSOR_PARAMS,
    DEFAULT_NO_CRIME_DISTANCE
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


def build_dataset_from_files() -> pd.DataFrame:
    """
    Builds the clean road-level training dataset by merging road_crime_features.csv
    with road environmental attributes from edges.csv.
    """
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    rc_path = os.path.join(repo_root, "data", "dev_test", "road_crime_features.csv")
    edges_path = os.path.join(repo_root, "data", "raw", "edges.csv")

    if not os.path.exists(rc_path):
        raise FileNotFoundError(f"Missing road_crime_features.csv at {rc_path}. Run 06_feature_engineering.py first.")

    print(f"[Dataset] Loading road crime features from: {rc_path}")
    rc_df = pd.read_csv(rc_path)

    print(f"[Dataset] Loading road environmental attributes from: {edges_path}")
    edges_df = pd.read_csv(edges_path, usecols=["length", "highway", "oneway"], low_memory=False)
    edges_df["road_id"] = np.arange(1, len(edges_df) + 1, dtype=int)

    # Merge on canonical road_id
    df = pd.merge(rc_df, edges_df, on="road_id", how="left")

    # Data cleaning & imputation
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

    # Defaults for POI proximity (aligned with router CSV fallback)
    df["police_distance"] = 1500.0
    df["hospital_distance"] = 1200.0
    df["pharmacy_distance"] = 800.0
    df["commercial_density"] = 0.0
    df["isolation_risk"] = 10.0
    df["bar_count"] = 0
    df["liquor_shop_count"] = 0

    # Ensure no NaN or inf in numeric features
    df["crime_count"] = df["crime_count"].fillna(0).astype(int)
    df["recent_crime_count"] = df["recent_crime_count"].fillna(0).astype(int)
    df["crime_density"] = df["crime_density"].fillna(0.0).astype(float)
    df["average_severity"] = df["average_severity"].fillna(0.0).astype(float)
    df["night_crime_ratio"] = df["night_crime_ratio"].fillna(0.0).astype(float)
    df["min_crime_distance"] = df["min_crime_distance"].fillna(DEFAULT_NO_CRIME_DISTANCE).astype(float)

    # =========================================================================
    # TASK 2: DEFINE THE DEVELOPMENT TARGET CAREFULLY
    # =========================================================================
    # Target: `development_crime_risk_score` (continuous scale 0.0 to 100.0)
    # Reflects the compound hazard load of incident volume, recency, severity,
    # and nocturnal vulnerability on the road.
    # Roads with zero crimes: target is exactly 0.0.
    # Roads with crimes: score ranges smoothly up to 100.0.
    # =========================================================================
    target_raw = np.where(
        df["crime_count"] > 0,
        10.0 * df["crime_count"] + 8.0 * df["recent_crime_count"] + 6.0 * df["average_severity"] + 12.0 * df["night_crime_ratio"],
        0.0
    )
    df[TARGET_COLUMN] = np.round(np.clip(target_raw, 0.0, 100.0), 2)

    return df


def train_crime_risk_model(df: pd.DataFrame = None, save_model: bool = True) -> dict:
    """
    Trains and evaluates the Random Forest Crime Risk Regressor.
    """
    if df is None:
        df = build_dataset_from_files()

    print(f"\n[Training] Total road records in dataset: {len(df)}")
    active_count = int((df["crime_count"] > 0).sum())
    zero_count = int((df["crime_count"] == 0).sum())
    print(f"  - Active crime roads: {active_count} ({active_count / len(df) * 100:.2f}%)")
    print(f"  - Zero crime roads:   {zero_count} ({zero_count / len(df) * 100:.2f}%)")

    # Feature matrix X and Target y
    X = df[ALL_FEATURE_COLUMNS].copy()
    y = df[TARGET_COLUMN].copy()

    # Verify no target leakage
    assert TARGET_COLUMN not in X.columns, "CRITICAL ERROR: Target variable leaked into input features!"

    # Check for NaN / Inf
    assert not X.isna().any().any(), "Input feature matrix contains NaN values!"
    assert not np.isinf(X.values).any(), "Input feature matrix contains infinite values!"

    # Train / Test split (80% train, 20% test)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42
    )
    print(f"[Training] Train samples: {len(X_train)} (80%) | Test samples: {len(X_test)} (20%)")

    # Train Random Forest Regressor
    print(f"[Training] Fitting RandomForestRegressor (n_estimators={RF_REGRESSOR_PARAMS['n_estimators']}, max_depth={RF_REGRESSOR_PARAMS['max_depth']})...")
    t0 = time.time()
    rf = RandomForestRegressor(**RF_REGRESSOR_PARAMS)
    rf.fit(X_train, y_train)
    train_duration = time.time() - t0
    print(f"[Training] Model fit completed in {train_duration:.2f}s")

    # Predictions for evaluation
    y_train_pred = rf.predict(X_train)
    y_test_pred = rf.predict(X_test)

    # Metrics
    train_mae = float(mean_absolute_error(y_train, y_train_pred))
    train_rmse = float(root_mean_squared_error(y_train, y_train_pred))
    train_r2 = float(r2_score(y_train, y_train_pred))

    test_mae = float(mean_absolute_error(y_test, y_test_pred))
    test_rmse = float(root_mean_squared_error(y_test, y_test_pred))
    test_r2 = float(r2_score(y_test, y_test_pred))

    # Feature Importances
    importances = {
        col: round(float(imp), 4)
        for col, imp in zip(ALL_FEATURE_COLUMNS, rf.feature_importances_)
    }
    sorted_importances = dict(sorted(importances.items(), key=lambda item: item[1], reverse=True))

    metadata = {
        "model_name": "RandomForestRegressor",
        "target_name": TARGET_COLUMN,
        "dataset_type": "DEVELOPMENT_SYNTHETIC_DATA",
        "disclaimer": "DEVELOPMENT MODEL — TRAINED ON SYNTHETIC DATA. NOT FOR PRODUCTION USE.",
        "trained_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_samples": len(df),
        "train_samples": len(X_train),
        "test_samples": len(X_test),
        "feature_names": ALL_FEATURE_COLUMNS,
        "parameters": RF_REGRESSOR_PARAMS,
        "metrics": {
            "train": {"mae": round(train_mae, 4), "rmse": round(train_rmse, 4), "r2": round(train_r2, 4)},
            "test": {"mae": round(test_mae, 4), "rmse": round(test_rmse, 4), "r2": round(test_r2, 4)}
        },
        "feature_importances": sorted_importances
    }

    if save_model:
        os.makedirs(SAVED_MODEL_DIR, exist_ok=True)
        joblib.dump(rf, MODEL_PATH)
        with open(METADATA_PATH, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)
        print(f"[Model Saved] Serialized Random Forest model saved to: {MODEL_PATH}")
        print(f"[Model Saved] Metadata saved to: {METADATA_PATH}")

    return {
        "model": rf,
        "metadata": metadata,
        "train_metrics": metadata["metrics"]["train"],
        "test_metrics": metadata["metrics"]["test"],
        "feature_importances": sorted_importances
    }
