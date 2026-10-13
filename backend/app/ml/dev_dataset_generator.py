"""
Development / Synthetic Crime Dataset Generator for Nashik City
=============================================================================
CRITICAL DISCLAIMER:
THIS MODULE GENERATES STRICTLY SYNTHETIC DEVELOPMENT / TEST DATA.
IT DOES NOT REPRESENT REAL POLICE, FIR, OR CRIME RECORDS IN NASHIK.
NO REAL-WORLD ACCURACY IS CLAIMED.
=============================================================================
"""

import os
import random
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# Nashik Landmark Clusters for spatial realism in dev testing
NASHIK_DEV_CLUSTERS = [
    {"name": "Panchavati / Old City", "lat": 20.008, "lon": 73.795, "weight": 0.22},
    {"name": "Nashik Road Station Hub", "lat": 19.953, "lon": 73.834, "weight": 0.20},
    {"name": "Dwarka / Highway Junction", "lat": 19.988, "lon": 73.805, "weight": 0.18},
    {"name": "College Road / KTHM", "lat": 20.005, "lon": 73.765, "weight": 0.15},
    {"name": "CIDCO / Ambad Link", "lat": 19.965, "lon": 73.745, "weight": 0.13},
    {"name": "Gangapur Road / Anandwalli", "lat": 20.025, "lon": 73.740, "weight": 0.12},
]

CRIME_TYPE_DISTRIBUTION = [
    ("Harassment / Eve Teasing", 2.5, 0.28),
    ("Phone / Bag Snatching", 2.0, 0.22),
    ("Verbal Abuse / Intimidation", 2.0, 0.18),
    ("Stalking", 3.0, 0.14),
    ("Theft", 1.5, 0.10),
    ("Assault", 4.5, 0.05),
    ("Physical Molestation", 5.0, 0.03),
]

DISCLAIMER_HEADER = (
    "# =============================================================================\n"
    "# DEVELOPMENT / SYNTHETIC TEST DATA — NOT REAL FIR DATA\n"
    "# Generated solely to test ML pipelines and PostGIS spatial mapping in Nashik.\n"
    "# =============================================================================\n"
)


def get_time_of_day(hour: int) -> str:
    if 6 <= hour < 18:
        return "Day"
    elif 18 <= hour < 21:
        return "Dusk"
    elif 21 <= hour < 24:
        return "Night"
    else:
        return "Late Night"


def generate_synthetic_crimes(num_records: int = 750, seed: int = 42, save_csv: bool = True) -> pd.DataFrame:
    """
    Generates synthetic crime incidents across Nashik coordinates.
    All records explicitly have `is_development_data = True`.
    """
    np.random.seed(seed)
    random.seed(seed)

    cluster_names = [c["name"] for c in NASHIK_DEV_CLUSTERS]
    cluster_weights = [c["weight"] for c in NASHIK_DEV_CLUSTERS]
    chosen_clusters = np.random.choice(len(NASHIK_DEV_CLUSTERS), size=num_records, p=cluster_weights)

    crime_types = [c[0] for c in CRIME_TYPE_DISTRIBUTION]
    crime_severities = {c[0]: c[1] for c in CRIME_TYPE_DISTRIBUTION}
    crime_weights = [c[2] for c in CRIME_TYPE_DISTRIBUTION]
    chosen_crimes = np.random.choice(crime_types, size=num_records, p=crime_weights)

    # Date range: between 18 months ago and today (reference: 2023-04-01 to 2024-10-01)
    end_date = datetime(2024, 10, 1)
    start_date = end_date - timedelta(days=540)
    total_seconds = int((end_date - start_date).total_seconds())

    records = []
    for i in range(num_records):
        cluster = NASHIK_DEV_CLUSTERS[chosen_clusters[i]]
        # Gaussian dispersion around hub: sigma ~ 0.008 deg (~850m)
        lat = cluster["lat"] + np.random.normal(0, 0.0075)
        lon = cluster["lon"] + np.random.normal(0, 0.0080)

        # Clip to Nashik development bounds
        lat = float(np.clip(lat, 19.910, 20.070))
        lon = float(np.clip(lon, 73.710, 73.870))

        c_type = chosen_crimes[i]
        sev = crime_severities[c_type]

        # Time distribution: 60% evening/night (18:00 - 02:00), 40% daytime
        if random.random() < 0.60:
            incident_hour = random.choice([18, 19, 20, 21, 22, 23, 0, 1])
        else:
            incident_hour = random.randint(6, 17)

        rand_sec = random.randint(0, total_seconds)
        base_dt = start_date + timedelta(seconds=rand_sec)
        incident_dt = base_dt.replace(hour=incident_hour, minute=random.randint(0, 59), second=random.randint(0, 59))

        tod = get_time_of_day(incident_hour)
        fir_no = f"DEV-SYNTH-FIR-2024-{i + 1:04d}"
        wkt_geom = f"POINT ({lon:.6f} {lat:.6f})"

        records.append({
            "fir_number": fir_no,
            "crime_date": incident_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "crime_type": c_type,
            "severity_weight": sev,
            "time_of_day": tod,
            "latitude": round(lat, 6),
            "longitude": round(lon, 6),
            "geometry": wkt_geom,
            "is_development_data": True
        })

    df = pd.DataFrame(records)

    if save_csv:
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        out_dir = os.path.join(repo_root, "data", "dev_test")
        os.makedirs(out_dir, exist_ok=True)
        csv_path = os.path.join(out_dir, "synthetic_nashik_crimes_sample.csv")

        with open(csv_path, "w", encoding="utf-8") as f:
            f.write(DISCLAIMER_HEADER)
            df.to_csv(f, index=False)
        print(f"[DEV DATASET] Saved {len(df)} synthetic records to: {csv_path}")

    return df


if __name__ == "__main__":
    df = generate_synthetic_crimes(num_records=750)
    print("Sample of generated synthetic dataset:")
    print(df.head(5)[["fir_number", "crime_type", "severity_weight", "time_of_day", "latitude", "longitude", "is_development_data"]])
