"""
05_download_crime.py
=============================================================================
CRITICAL NOTICE & DISCLAIMER:
This script DOES NOT download real crime data from the internet.
Real Nashik FIR / police crime records are not yet integrated.

This script generates and seeds a clearly labelled DEVELOPMENT/SYNTHETIC
TEST DATASET for Nashik city into the `crime_records` table and persists
a local CSV fixture in `data/dev_test/`.

Every record has: is_development_data = TRUE
=============================================================================
"""

import os
import sys
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


def seed_crimes_into_db(df):
    """Inserts synthetic test records into PostgreSQL crime_records table."""
    try:
        conn = get_connection()
        cur = conn.cursor()
        print("Connected to PostgreSQL database successfully.")

        ensure_crime_table_exists(cur)

        # Clear previous development/test records to avoid duplicate key issues on re-run
        cur.execute("DELETE FROM crime_records WHERE is_development_data = TRUE;")
        conn.commit()

        records = []
        for _, row in df.iterrows():
            records.append((
                row["fir_number"],
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
        """
        template = "(%s, %s, %s, %s, %s, %s, %s, ST_GeomFromText(%s, 4326), %s)"
        execute_values(cur, insert_query, records, template=template, page_size=1000)
        conn.commit()

        cur.execute("SELECT count(*), is_development_data FROM crime_records GROUP BY is_development_data;")
        summary = cur.fetchall()
        print("\n================ DATABASE INSERTION SUMMARY ================")
        for count, is_dev in summary:
            status_label = "SYNTHETIC DEV/TEST DATA" if is_dev else "VERIFIED PRODUCTION DATA"
            print(f" - {count} records | Status: {status_label}")
        print("============================================================\n")

        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Database insertion note: PostgreSQL not reachable ({e}).")
        print("Dataset has been saved to CSV for offline/fallback use.")
        return False


def main():
    print("=" * 70)
    print("AI-BASED WOMEN SAFETY NAVIGATION SYSTEM (NASHIK)")
    print("SCRIPT 05: SEED DEVELOPMENT / TEST CRIME DATASET")
    print("=" * 70)
    print("DISCLAIMER: This script seeds SYNTHETIC test fixtures only.")
    print("NO REAL CRIME OR POLICE FIR DATA IS USED.\n")

    # 1. Generate 750 synthetic test records
    num_test_records = 750
    print(f"Generating {num_test_records} synthetic test crime records for Nashik...")
    df = generate_synthetic_crimes(num_records=num_test_records, save_csv=True)

    # 2. Seed into PostgreSQL if reachable
    db_ok = seed_crimes_into_db(df)

    print(f"\nDone! Processed {len(df)} synthetic crime records.")
    print(f"All records tagged with: is_development_data = TRUE")
    if db_ok:
        print("Database status: Seeded in PostgreSQL 'crime_records' table.")
    else:
        print("Database status: Persisted to data/dev_test/synthetic_nashik_crimes_sample.csv")


if __name__ == "__main__":
    main()
