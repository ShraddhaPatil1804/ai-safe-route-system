"""
05_download_crime.py
=============================================================================
Crime Data Ingestion & Seeding Engine for Nashik Road Network.

Supports two modes:
1. Production FIR Ingestion (DEFAULT when data/crime/nashik_fir_crimes.csv exists):
   - Ingests, validates, and normalizes genuine Nashik police FIR records.
   - Strictly flags records as `is_development_data = FALSE`, `is_synthetic = FALSE`,
     `record_origin = 'REAL_FIR'`.
   - Flags geocoded coordinates as approximate (`coordinate_precision = 'approximate'`).
   - Normalizes DD-MM-YYYY dates and time_of_day categories.
   - Rejection and deduplication tracking with clean reporting.

2. Synthetic Development Mode (--synthetic flag):
   - Generates clearly labelled DEVELOPMENT/SYNTHETIC test fixtures.
   - All records flagged as `is_development_data = TRUE`, `is_synthetic = TRUE`,
     `record_origin = 'SYNTHETIC'`.
=============================================================================
"""

import os
import sys
import re
import argparse
from datetime import datetime
from typing import Dict, Any, Tuple
import pandas as pd
import numpy as np
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

# Ensure root path is accessible for internal imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from backend.app.ml.dev_dataset_generator import generate_synthetic_crimes

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5434")
DB_NAME = os.getenv("DB_NAME", "women_safe_navigation")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "khushi")


def get_connection():
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        connect_timeout=3
    )


def ensure_crime_table_exists(cur):
    """Ensures PostGIS extension and crime_records table with indexes exist."""
    cur.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS crime_records (
        id SERIAL PRIMARY KEY,
        fir_number TEXT UNIQUE NOT NULL,
        crime_date TIMESTAMP NOT NULL,
        crime_type TEXT NOT NULL,
        severity_weight DOUBLE PRECISION NOT NULL,
        time_of_day TEXT NOT NULL,
        latitude DOUBLE PRECISION NOT NULL,
        longitude DOUBLE PRECISION NOT NULL,
        geometry geometry(Point, 4326),
        is_development_data BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_crime_records_geom ON crime_records USING GIST (geometry);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_crime_records_date ON crime_records (crime_date);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_crime_records_type ON crime_records (crime_type);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_crime_records_dev ON crime_records (is_development_data);")


VALID_TIME_OF_DAY = {"Day", "Dusk", "Night", "Late Night"}

NASHIK_DISTRICT_BOUNDS = {
    "min_lat": 19.50,
    "max_lat": 20.60,
    "min_lon": 73.20,
    "max_lon": 74.60,
}

def parse_time_of_day_fallback(time_str: str) -> str:
    """Infers time of day category from original time text if available."""
    if not isinstance(time_str, str) or not time_str.strip():
        return "Day"
    m = re.search(r"(\d{1,2}):(\d{2})", time_str)
    if m:
        hr = int(m.group(1))
        if 6 <= hr < 18:
            return "Day"
        elif 18 <= hr < 21:
            return "Dusk"
        elif 21 <= hr < 24:
            return "Night"
        else:
            return "Late Night"
    return "Day"


def validate_and_normalize_fir_csv(
    csv_path: str,
    deduplicate_fir: bool = True
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Loads, cleans, validates, and normalizes the Nashik FIR CSV dataset.
    Preserves genuine FIR details without fabrication or alteration.
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"FIR CSV not found at: {csv_path}")

    raw_df = pd.read_csv(csv_path)
    total_raw = len(raw_df)

    stats = {
        "total_records_raw": total_raw,
        "rejected_missing_coordinates": 0,
        "rejected_out_of_bounds": 0,
        "rejected_invalid_dates": 0,
        "duplicates_skipped": 0,
        "imported_records": 0,
        "records_with_coordinates": 0,
        "rejection_details": [],
    }

    # 1. Date Validation (DD-MM-YYYY)
    raw_df["crime_date_parsed"] = pd.to_datetime(
        raw_df["crime_date"], format="%d-%m-%Y", errors="coerce"
    )
    invalid_dates = raw_df["crime_date_parsed"].isnull()
    if invalid_dates.any():
        stats["rejected_invalid_dates"] = int(invalid_dates.sum())
        for _, r in raw_df[invalid_dates].iterrows():
            stats["rejection_details"].append({
                "fir_number": r["fir_number"],
                "reason": f"Invalid date format: {r['crime_date']}"
            })

    # 2. Missing Coordinates Check
    missing_coords = raw_df["latitude"].isnull() | raw_df["longitude"].isnull()
    stats["rejected_missing_coordinates"] = int(missing_coords.sum())
    for _, r in raw_df[missing_coords].iterrows():
        stats["rejection_details"].append({
            "fir_number": r["fir_number"],
            "reason": f"Missing coordinates: {r.get('review_reason') or 'Ungeocoded'}"
        })

    # 3. Coordinate Bounds Check
    valid_coords_mask = ~missing_coords
    out_of_bounds = valid_coords_mask & (
        (raw_df["latitude"] < NASHIK_DISTRICT_BOUNDS["min_lat"]) |
        (raw_df["latitude"] > NASHIK_DISTRICT_BOUNDS["max_lat"]) |
        (raw_df["longitude"] < NASHIK_DISTRICT_BOUNDS["min_lon"]) |
        (raw_df["longitude"] > NASHIK_DISTRICT_BOUNDS["max_lon"])
    )
    stats["rejected_out_of_bounds"] = int(out_of_bounds.sum())

    # Keep records with valid coordinates within bounds
    usable_mask = valid_coords_mask & ~out_of_bounds & ~invalid_dates
    df_usable = raw_df[usable_mask].copy()

    # 4. Deduplication
    if deduplicate_fir:
        df_usable.sort_values(
            by=["fir_number", "verified", "latitude"],
            ascending=[True, False, False],
            inplace=True
        )
        is_dup = df_usable.duplicated(subset=["fir_number"], keep="first")
        stats["duplicates_skipped"] = int(is_dup.sum())
        clean_df = df_usable[~is_dup].copy().reset_index(drop=True)
    else:
        clean_df = df_usable.copy().reset_index(drop=True)

    # 5. Normalization
    def normalize_tod(row):
        val = row.get("time_of_day")
        if pd.notna(val) and str(val).strip() in VALID_TIME_OF_DAY:
            return str(val).strip()
        return parse_time_of_day_fallback(row.get("time_original", ""))

    clean_df["time_of_day"] = clean_df.apply(normalize_tod, axis=1)
    clean_df["crime_date"] = clean_df["crime_date_parsed"].dt.strftime("%Y-%m-%d %H:%M:%S")
    clean_df["severity_weight"] = clean_df["severity_weight"].astype(float).clip(lower=1.0, upper=10.0)
    clean_df["latitude"] = clean_df["latitude"].astype(float)
    clean_df["longitude"] = clean_df["longitude"].astype(float)
    clean_df["geometry"] = clean_df.apply(lambda r: f"POINT({r['longitude']} {r['latitude']})", axis=1)

    # Provenance and Approximateness Flags
    clean_df["is_development_data"] = False
    clean_df["is_synthetic"] = False
    clean_df["record_origin"] = "REAL_FIR"
    clean_df["coordinate_precision"] = "approximate"
    clean_df["incident_id"] = [f"FIR_{r['fir_number']}_{i+1}" for i, (_, r) in enumerate(clean_df.iterrows())]

    stats["imported_records"] = len(clean_df)
    stats["records_with_coordinates"] = len(clean_df)

    return clean_df, stats


def seed_crimes_into_db(df, is_dev: bool = True):
    """Inserts crime records into PostgreSQL crime_records table."""
    try:
        conn = get_connection()
        cur = conn.cursor()
        print("Connected to PostgreSQL database successfully.")

        ensure_crime_table_exists(cur)

        # Clear previous records matching the same development/production status
        cur.execute("DELETE FROM crime_records WHERE is_development_data = %s;", (is_dev,))
        conn.commit()

        records = []
        for _, row in df.iterrows():
            records.append((
                str(row["fir_number"]),
                row["crime_date"],
                row["crime_type"],
                float(row["severity_weight"]),
                row["time_of_day"],
                float(row["latitude"]),
                float(row["longitude"]),
                row["geometry"],  # WKT: POINT(lon lat)
                bool(row["is_development_data"])
            ))

        insert_query = """
        INSERT INTO crime_records (
            fir_number, crime_date, crime_type, severity_weight,
            time_of_day, latitude, longitude, geometry, is_development_data
        ) VALUES %s
        ON CONFLICT (fir_number) DO UPDATE
        SET crime_date = EXCLUDED.crime_date,
            crime_type = EXCLUDED.crime_type,
            severity_weight = EXCLUDED.severity_weight,
            time_of_day = EXCLUDED.time_of_day,
            latitude = EXCLUDED.latitude,
            longitude = EXCLUDED.longitude,
            geometry = EXCLUDED.geometry,
            is_development_data = EXCLUDED.is_development_data;
        """
        template = "(%s, %s, %s, %s, %s, %s, %s, ST_GeomFromText(%s, 4326), %s)"
        execute_values(cur, insert_query, records, template=template, page_size=1000)
        conn.commit()

        cur.execute("SELECT count(*), is_development_data FROM crime_records GROUP BY is_development_data;")
        summary = cur.fetchall()
        print("\n================ DATABASE INSERTION SUMMARY ================")
        for count, dev_flag in summary:
            status_label = "SYNTHETIC DEV/TEST DATA" if dev_flag else "GENUINE PRODUCTION FIR DATA"
            print(f" - {count} records | Status: {status_label}")
        print("============================================================\n")

        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Database insertion note: PostgreSQL not reachable ({e}).")
        return False


def main():
    parser = argparse.ArgumentParser(description="Seed or import crime records for Nashik.")
    parser.add_argument("--synthetic", action="store_true", help="Generate synthetic development fixtures instead of FIR data")
    parser.add_argument("--source", type=str, default=None, help="Path to FIR crime CSV file")
    parser.add_argument("--allow-duplicate-firs", action="store_true", help="Do not deduplicate by fir_number (keep all incident entries)")
    args = parser.parse_args()

    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    default_fir_path = os.path.join(repo_root, "data", "crime", "nashik_fir_crimes.csv")
    fir_path = args.source or default_fir_path

    print("=" * 70)
    print("AI-BASED WOMEN SAFETY NAVIGATION SYSTEM (NASHIK)")
    print("SCRIPT 05: CRIME DATA INGESTION & PIPELINE INTEGRATION")
    print("=" * 70)

    if not args.synthetic and os.path.exists(fir_path):
        print(f"MODE: INGESTING GENUINE NASHIK POLICE FIR RECORDS")
        print(f"Source CSV: {fir_path}")
        print("Provenance: REAL_FIR | is_development_data = FALSE | is_synthetic = FALSE")
        print("Coordinates: Approximate (OSM Nominatim & Verified Gazetteer Geocoding)\n")

        clean_df, stats = validate_and_normalize_fir_csv(
            csv_path=fir_path,
            deduplicate_fir=not args.allow_duplicate_firs
        )

        print("\n================ CSV INGESTION & VALIDATION STATS ================")
        print(f"1. Total Raw CSV Rows:                 {stats['total_records_raw']}")
        print(f"2. Rejected - Missing Coordinates:     {stats['rejected_missing_coordinates']}")
        print(f"3. Rejected - Out of Bounds:           {stats['rejected_out_of_bounds']}")
        print(f"4. Rejected - Invalid Dates:           {stats['rejected_invalid_dates']}")
        print(f"5. Skipped as Duplicates:              {stats['duplicates_skipped']}")
        print(f"6. Total Valid Clean FIR Records:      {stats['imported_records']}")
        print("==================================================================\n")

        print("SAMPLE IMPORTED FIR RECORDS:")
        print(clean_df[[
            "fir_number", "crime_date", "crime_type", "severity_weight",
            "time_of_day", "latitude", "longitude", "record_origin", "coordinate_precision"
        ]].head(5).to_string(index=False))

        # Save clean normalized FIR dataset to data/crime/nashik_fir_crimes_clean.csv
        clean_csv_path = os.path.join(repo_root, "data", "crime", "nashik_fir_crimes_clean.csv")
        clean_df.to_csv(clean_csv_path, index=False)
        print(f"\nSaved normalized genuine FIR records to: {clean_csv_path}")

        # Seed into PostgreSQL if active
        db_ok = seed_crimes_into_db(clean_df, is_dev=False)
        if db_ok:
            print("Database status: Seeded in PostgreSQL 'crime_records' table.")
        else:
            print(f"Database status: Offline. Dataset ready for offline spatial matching via {clean_csv_path}.")

    else:
        print("MODE: SEEDING SYNTHETIC DEVELOPMENT/TEST CRIME DATASET")
        print("DISCLAIMER: This mode seeds SYNTHETIC test fixtures only.\n")

        num_test_records = 750
        print(f"Generating {num_test_records} synthetic test crime records for Nashik...")
        df = generate_synthetic_crimes(num_records=num_test_records, save_csv=True)
        df["is_synthetic"] = True
        df["record_origin"] = "SYNTHETIC"

        db_ok = seed_crimes_into_db(df, is_dev=True)
        print(f"\nDone! Processed {len(df)} synthetic crime records.")
        print(f"All records tagged with: is_development_data = TRUE, is_synthetic = TRUE")
        if db_ok:
            print("Database status: Seeded in PostgreSQL 'crime_records' table.")
        else:
            print("Database status: Persisted to data/dev_test/synthetic_nashik_crimes_sample.csv")


if __name__ == "__main__":
    main()

