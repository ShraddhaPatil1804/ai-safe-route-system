import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
conn = psycopg2.connect(
    host=os.getenv("DB_HOST", "localhost"),
    port=os.getenv("DB_PORT", "5434"),
    dbname=os.getenv("DB_NAME", "women_safe_navigation"),
    user=os.getenv("DB_USER", "postgres"),
    password=os.getenv("DB_PASSWORD", "khushi")
)
cur = conn.cursor()
cur.execute("SELECT ST_XMin(extent), ST_YMin(extent), ST_XMax(extent), ST_YMax(extent) FROM (SELECT ST_Extent(geometry) as extent FROM roads) sub;")
bounds = cur.fetchone()
print(f"Roads Bounding Box: min_lon={bounds[0]}, min_lat={bounds[1]}, max_lon={bounds[2]}, max_lat={bounds[3]}")

# Also check column names of roads table
cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'roads';")
print("\nRoads columns:", cur.fetchall())

# Check intersections columns
cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'intersections';")
print("\nIntersections columns:", cur.fetchall())

# Check existing tables
cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';")
print("\nPublic tables:", [r[0] for r in cur.fetchall()])

conn.close()
