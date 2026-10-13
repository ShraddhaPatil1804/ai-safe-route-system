import os
import psycopg2
import pandas as pd
from dotenv import load_dotenv

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
        password=DB_PASSWORD
    )

def create_schema():
    conn = get_connection()
    cur = conn.cursor()
    print("Enabling PostGIS extension...")
    cur.execute("CREATE EXTENSION IF NOT EXISTS postgis;")

    # Check if roads has 'from_node'
    cur.execute("""
    SELECT column_name FROM information_schema.columns 
    WHERE table_name = 'roads' AND column_name = 'from_node';
    """)
    has_from_node = cur.fetchone() is not None
    if not has_from_node:
        print("Existing roads table does not match standard schema. Recreating roads and intersections...")
        cur.execute("DROP TABLE IF EXISTS road_features CASCADE;")
        cur.execute("DROP TABLE IF EXISTS roads CASCADE;")
        cur.execute("DROP TABLE IF EXISTS intersections CASCADE;")
        conn.commit()

    print("Creating tables as per specification...")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        email VARCHAR(255) UNIQUE NOT NULL,
        password_hash VARCHAR(255) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS intersections (
        id SERIAL PRIMARY KEY,
        osmid BIGINT NOT NULL,
        latitude DOUBLE PRECISION NOT NULL,
        longitude DOUBLE PRECISION NOT NULL,
        geometry geometry(Point, 4326)
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS roads (
        id SERIAL PRIMARY KEY,
        osm_way_id TEXT,
        from_node BIGINT NOT NULL,
        to_node BIGINT NOT NULL,
        road_name TEXT,
        road_type TEXT,
        maxspeed TEXT,
        lanes TEXT,
        length DOUBLE PRECISION NOT NULL,
        geometry geometry(LineString, 4326),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS pois (
        id SERIAL PRIMARY KEY,
        osm_id BIGINT,
        name TEXT,
        category TEXT NOT NULL,
        latitude DOUBLE PRECISION NOT NULL,
        longitude DOUBLE PRECISION NOT NULL,
        geometry geometry(Point, 4326)
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS user_reports (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
        report_type TEXT NOT NULL,
        description TEXT,
        severity TEXT NOT NULL,
        status TEXT DEFAULT 'pending',
        latitude DOUBLE PRECISION NOT NULL,
        longitude DOUBLE PRECISION NOT NULL,
        geometry geometry(Point, 4326),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS road_features (
        road_id INTEGER PRIMARY KEY REFERENCES roads(id) ON DELETE CASCADE,
        length DOUBLE PRECISION,
        road_type TEXT,
        
        police_distance DOUBLE PRECISION,
        hospital_distance DOUBLE PRECISION,
        pharmacy_distance DOUBLE PRECISION,
        
        police_count INTEGER DEFAULT 0,
        hospital_count INTEGER DEFAULT 0,
        pharmacy_count INTEGER DEFAULT 0,
        
        bus_stop_count INTEGER DEFAULT 0,
        restaurant_count INTEGER DEFAULT 0,
        cafe_count INTEGER DEFAULT 0,
        market_count INTEGER DEFAULT 0,
        bank_count INTEGER DEFAULT 0,
        fuel_station_count INTEGER DEFAULT 0,
        liquor_shop_count INTEGER DEFAULT 0,
        bar_count INTEGER DEFAULT 0,
        park_count INTEGER DEFAULT 0,
        
        commercial_density DOUBLE PRECISION DEFAULT 0.0,
        crowd_score DOUBLE PRECISION DEFAULT 0.0,
        isolation_score DOUBLE PRECISION DEFAULT 0.0,
        lighting_score DOUBLE PRECISION DEFAULT 0.0,
        connectivity_score DOUBLE PRECISION DEFAULT 0.0,
        emergency_access_score DOUBLE PRECISION DEFAULT 0.0,
        
        lighting_risk DOUBLE PRECISION DEFAULT 0.0,
        crowd_risk DOUBLE PRECISION DEFAULT 0.0,
        isolation_risk DOUBLE PRECISION DEFAULT 0.0,
        liquor_risk DOUBLE PRECISION DEFAULT 0.0,
        bar_risk DOUBLE PRECISION DEFAULT 0.0,
        road_risk DOUBLE PRECISION DEFAULT 0.0,
        emergency_bonus DOUBLE PRECISION DEFAULT 0.0,
        
        final_safety_score DOUBLE PRECISION DEFAULT 0.0,
        safety_level TEXT
    );
    """)

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

    cur.execute("""
    CREATE TABLE IF NOT EXISTS road_crime_features (
        road_id INTEGER PRIMARY KEY REFERENCES roads(id) ON DELETE CASCADE,
        crime_count INTEGER DEFAULT 0 NOT NULL,
        recent_crime_count INTEGER DEFAULT 0 NOT NULL,
        crime_density DOUBLE PRECISION DEFAULT 0.0 NOT NULL,
        average_severity DOUBLE PRECISION DEFAULT 0.0 NOT NULL,
        night_crime_ratio DOUBLE PRECISION DEFAULT 0.0 NOT NULL,
        min_crime_distance DOUBLE PRECISION DEFAULT 5000.0 NOT NULL,
        is_development_data BOOLEAN DEFAULT TRUE NOT NULL,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Spatial Indexes
    print("Creating spatial and attribute indexes...")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_intersections_geom ON intersections USING GIST (geometry);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_intersections_osmid ON intersections (osmid);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_roads_geom ON roads USING GIST (geometry);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_roads_from_node ON roads (from_node);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_roads_to_node ON roads (to_node);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_pois_geom ON pois USING GIST (geometry);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_pois_category ON pois (category);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_user_reports_geom ON user_reports USING GIST (geometry);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_crime_records_geom ON crime_records USING GIST (geometry);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_crime_records_date ON crime_records (crime_date);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_crime_records_type ON crime_records (crime_type);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_crime_records_dev ON crime_records (is_development_data);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_road_crime_density ON road_crime_features (crime_density);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_road_crime_count ON road_crime_features (crime_count);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_road_crime_dev ON road_crime_features (is_development_data);")

    conn.commit()
    cur.close()
    conn.close()
    print("Schema initialized successfully!")



def populate_network():
    conn = get_connection()
    cur = conn.cursor()

    # Check if already populated
    cur.execute("SELECT count(*) FROM roads;")
    r_count = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM intersections;")
    i_count = cur.fetchone()[0]

    nodes_file = os.path.join("data", "raw", "nodes.csv")
    edges_file = os.path.join("data", "raw", "edges.csv")

    if i_count == 0 and os.path.exists(nodes_file):
        print(f"Loading intersections from {nodes_file}...")
        df_nodes = pd.read_csv(nodes_file)
        print(f"Found {len(df_nodes)} nodes. Inserting into intersections table...")
        # Prepare rows: osmid, y (lat), x (lon), geometry
        # Batch insert
        records = []
        for _, row in df_nodes.iterrows():
            osmid = int(row['osmid'])
            lat = float(row['y'])
            lon = float(row['x'])
            wkt = str(row['geometry'])
            records.append((osmid, lat, lon, wkt))

        from psycopg2.extras import execute_values
        query = """
        INSERT INTO intersections (osmid, latitude, longitude, geometry)
        VALUES %s
        """
        template = "(%s, %s, %s, ST_GeomFromText(%s, 4326))"
        execute_values(cur, query, records, template=template, page_size=5000)
        conn.commit()
        print(f"Successfully inserted {len(records)} intersections!")
    else:
        print(f"Intersections table already has {i_count} rows.")

    if r_count == 0 and os.path.exists(edges_file):
        print(f"Loading roads from {edges_file}...")
        df_edges = pd.read_csv(edges_file)
        print(f"Found {len(df_edges)} edges. Inserting into roads table...")
        
        from psycopg2.extras import execute_values
        insert_query = """
        INSERT INTO roads (osm_way_id, from_node, to_node, road_name, road_type, maxspeed, lanes, length, geometry)
        VALUES %s
        """
        template = "(%s, %s, %s, %s, %s, %s, %s, %s, ST_GeomFromText(%s, 4326))"
        
        batch = []
        batch_size = 5000
        total = len(df_edges)
        for i, row in df_edges.iterrows():
            osm_way_id = str(row['osmid']) if pd.notna(row['osmid']) else None
            from_node = int(row['u'])
            to_node = int(row['v'])
            road_name = str(row['name']) if pd.notna(row['name']) else None
            road_type = str(row['highway']) if pd.notna(row['highway']) else 'unknown'
            maxspeed = str(row['maxspeed']) if pd.notna(row['maxspeed']) else None
            lanes = str(row['lanes']) if pd.notna(row['lanes']) else None
            length = float(row['length'])
            wkt = str(row['geometry'])
            batch.append((osm_way_id, from_node, to_node, road_name, road_type, maxspeed, lanes, length, wkt))

            if len(batch) >= batch_size:
                execute_values(cur, insert_query, batch, template=template, page_size=batch_size)
                conn.commit()
                print(f"  Inserted {i + 1}/{total} roads...")
                batch = []

        if batch:
            execute_values(cur, insert_query, batch, template=template, page_size=batch_size)
            conn.commit()
            print(f"  Inserted {total}/{total} roads.")
        print(f"Successfully inserted all roads!")
    else:
        print(f"Roads table already has {r_count} rows.")

    cur.close()
    conn.close()

if __name__ == "__main__":
    create_schema()
    populate_network()
