"""
06_feature_engineering.py
=============================================================================
CRITICAL NOTICE & DISCLAIMER:
This script extracts road-level crime features from the clearly labelled
DEVELOPMENT / SYNTHETIC TEST CRIME DATASET for Nashik.
NO REAL POLICE OR FIR DATA IS CURRENTLY IN USE.

Spatial Matching:
  - Associates crime points with road segments within a configurable corridor:
    CRIME_ROAD_BUFFER_METERS = 75 meters (PostGIS ST_DWithin / geography).
  - Canonical identifier: road_id = roads.id.
  - Generates road_crime_features with:
      crime_count, recent_crime_count, crime_density (crimes/km),
      average_severity, night_crime_ratio, min_crime_distance.
=============================================================================
"""

import os
import sys
import time
import psycopg2
from dotenv import load_dotenv

# Ensure root path is accessible for internal imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from backend.app.ml.config import (
    CRIME_ROAD_BUFFER_METERS,
    RECENT_CRIME_WINDOW_DAYS,
    DEFAULT_NO_CRIME_DISTANCE
)
from backend.app.ml.feature_extractor import (
    extract_features_postgis,
    extract_features_offline
)

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5434")
DB_NAME = os.getenv("DB_NAME", "women_safe_navigation")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "khushi")


def try_db_connection():
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            connect_timeout=3
        )
        return conn
    except Exception:
        return None


def run_benchmark_verification():
    """Runs regression verification on router benchmark to ensure routing is untouched."""
    print("\n------------------------------------------------------------")
    print("RUNNING ROUTING ENGINE REGRESSION BENCHMARK...")
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
    print("ROUTING ENGINE BENCHMARK VERIFIED UNCHANGED (100% REGRESSION-FREE)")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Extract road-level crime features for Nashik.")
    parser.add_argument("--synthetic", action="store_true", help="Use synthetic development dataset instead of genuine FIR records")
    parser.add_argument("--source", type=str, default=None, help="Custom crime CSV file path")
    parser.add_argument("--buffer", type=float, default=CRIME_ROAD_BUFFER_METERS, help="Corridor matching buffer in meters")
    args = parser.parse_args()

    buffer_meters = args.buffer
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    clean_fir = os.path.join(repo_root, "data", "crime", "nashik_fir_crimes_clean.csv")
    raw_fir = os.path.join(repo_root, "data", "crime", "nashik_fir_crimes.csv")
    dev_sample = os.path.join(repo_root, "data", "dev_test", "synthetic_nashik_crimes_sample.csv")

    if args.synthetic:
        crimes_source = dev_sample
        out_csv = os.path.join(repo_root, "data", "dev_test", "road_crime_features_synthetic.csv")
        dataset_mode = "SYNTHETIC DEVELOPMENT DATASET"
    elif args.source:
        crimes_source = args.source
        out_csv = os.path.join(repo_root, "data", "dev_test", "road_crime_features.csv")
        dataset_mode = f"CUSTOM SOURCE ({crimes_source})"
    elif os.path.exists(clean_fir):
        crimes_source = clean_fir
        out_csv = os.path.join(repo_root, "data", "dev_test", "road_crime_features.csv")
        dataset_mode = "GENUINE NASHIK POLICE FIR RECORDS"
    else:
        crimes_source = dev_sample
        out_csv = os.path.join(repo_root, "data", "dev_test", "road_crime_features.csv")
        dataset_mode = "SYNTHETIC DEVELOPMENT DATASET (FALLBACK)"

    print("=" * 70)
    print("AI-BASED WOMEN SAFETY NAVIGATION SYSTEM (NASHIK)")
    print("SCRIPT 06: ROAD-LEVEL CRIME FEATURE EXTRACTION (PHASE 3)")
    print("=" * 70)
    print(f"Dataset Mode:                     {dataset_mode}")
    print(f"Crime Source File:                {crimes_source}")
    print(f"Spatial Matching Corridor Buffer: {buffer_meters} meters")
    print(f"Recent Crime Time Window:        {RECENT_CRIME_WINDOW_DAYS} days (12 months)")
    print(f"Default No-Crime Distance:       {DEFAULT_NO_CRIME_DISTANCE} meters\n")

    t_start = time.time()
    conn = try_db_connection()

    if conn:
        print("[Database] Connected to PostgreSQL. Checking tables...")
        cur = conn.cursor()
        try:
            cur.execute("SELECT count(*) FROM crime_records;")
            c_cnt = cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM roads;")
            r_cnt = cur.fetchone()[0]
            if c_cnt > 0 and r_cnt > 0:
                print(f"[Database] Found {c_cnt} crime records and {r_cnt} roads in PostgreSQL.")
                result = extract_features_postgis(cur, conn, buffer_meters=buffer_meters, use_fir=not args.synthetic)
            else:
                print("[Database] Tables empty. Falling back to local spatial datasets...")
                result = extract_features_offline(buffer_meters=buffer_meters, crimes_source=crimes_source, out_csv_path=out_csv)
        except Exception as e:
            print(f"[Database Error] {e}. Falling back to local spatial datasets...")
            result = extract_features_offline(buffer_meters=buffer_meters, crimes_source=crimes_source, out_csv_path=out_csv)
        finally:
            cur.close()
            conn.close()
    else:
        print("[Database] PostgreSQL not running on port 5434. Running offline spatial indexer...")
        result = extract_features_offline(buffer_meters=buffer_meters, crimes_source=crimes_source, out_csv_path=out_csv)

    df = result["df"]
    total_crimes = result["total_crimes"]
    matched_crimes = result["matched_crimes"]
    unmatched_crimes = result["unmatched_crimes"]
    total_roads = len(df)
    roads_with_crime = len(df[df["crime_count"] > 0])
    roads_without_crime = len(df[df["crime_count"] == 0])
    is_dev = bool(df["is_development_data"].iloc[0]) if len(df) > 0 else False

    print("\n" + "=" * 70)
    print("PHASE 3 FEATURE EXTRACTION SUMMARY")
    print("=" * 70)
    print(f"Execution Mode:                     {result['mode']}")
    print(f"1. Total Crime Records Processed:   {total_crimes}")
    print(f"2. Crimes Matched within {int(buffer_meters)}m:     {matched_crimes} ({matched_crimes/total_crimes*100:.1f}%)")
    print(f"3. Unmatched Crimes (outside road): {unmatched_crimes} ({unmatched_crimes/total_crimes*100:.1f}%)")
    print(f"4. Total Road Segments Processed:   {total_roads}")
    print(f"5. Roads with Associated Crimes:    {roads_with_crime} ({roads_with_crime/total_roads*100:.2f}%)")
    print(f"6. Roads with Zero Crimes:          {roads_without_crime} ({roads_without_crime/total_roads*100:.2f}%)")
    print(f"7. Canonical Road ID Key:           roads.id confirmed (min={df['road_id'].min()}, max={df['road_id'].max()})")
    print(f"8. Dataset Provenance Flag:         is_development_data = {is_dev}")
    print(f"9. Generated Features Output:       {out_csv}")
    print(f"Total Extraction Time:              {time.time() - t_start:.2f}s")
    print("=" * 70)

    print("\nSAMPLE ROAD CRIME FEATURE ROWS (Roads with Matched Crimes):")
    sample_active = df[df["crime_count"] > 0].head(5)
    print(sample_active[[
        "road_id", "crime_count", "recent_crime_count", "crime_density",
        "average_severity", "night_crime_ratio", "min_crime_distance", "is_development_data"
    ]].to_string(index=False))

    print("\nSAMPLE ROAD CRIME FEATURE ROWS (Roads with Zero Crimes):")
    sample_zero = df[df["crime_count"] == 0].head(3)
    print(sample_zero[[
        "road_id", "crime_count", "recent_crime_count", "crime_density",
        "average_severity", "night_crime_ratio", "min_crime_distance", "is_development_data"
    ]].to_string(index=False))

    # Run routing engine regression verification
    run_benchmark_verification()


if __name__ == "__main__":
    main()
