import os
import sys
import math
import time
import psycopg2
from psycopg2.extras import execute_values
import numpy as np
from scipy.spatial import cKDTree
from dotenv import load_dotenv

# Ensure backend path is available for importing config
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from backend.app.safety.config import (
    ROAD_TYPE_RISK,
    DEFAULT_LIGHTING_LEVEL,
    LIGHTING_MAX_RISK,
    CROWD_MAX_RISK,
    MAX_CROWD_DENSITY,
    ACTIVITY_CATEGORIES,
    calculate_isolation_risk,
    LIQUOR_RISK_PER_COUNT,
    MAX_LIQUOR_RISK,
    BAR_RISK_PER_COUNT,
    MAX_BAR_RISK,
    POLICE_BONUS_MAX,
    POLICE_BONUS_SCALE,
    HOSPITAL_BONUS_MAX,
    HOSPITAL_BONUS_SCALE,
    PHARMACY_BONUS_MAX,
    PHARMACY_BONUS_SCALE,
    MAX_EMERGENCY_BONUS,
    get_safety_level
)

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5434")
DB_NAME = os.getenv("DB_NAME", "women_safe_navigation")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "khushi")

def haversine_distance_meters(lat1, lon1, lat2, lon2):
    """Accurate distance in meters between two lat/lon coordinates."""
    R = 6371000.0  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2.0)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0)**2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c

def get_clean_road_type(raw_type):
    if not raw_type:
        return "unknown"
    val = str(raw_type).strip("['\"] ")
    if "," in val:
        val = val.split(",")[0].strip("['\"] ")
    return val.lower()

def main():
    print("Connecting to PostgreSQL...")
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    cur = conn.cursor()

    t0 = time.time()
    print("Loading roads with centroids...")
    cur.execute("""
        SELECT id, road_type, length, 
               ST_Y(ST_Centroid(geometry)) as lat, 
               ST_X(ST_Centroid(geometry)) as lon
        FROM roads;
    """)
    roads = cur.fetchall()
    print(f"Loaded {len(roads)} roads in {time.time() - t0:.2f}s")

    print("Loading POIs...")
    cur.execute("""
        SELECT id, category, latitude, longitude
        FROM pois;
    """)
    pois = cur.fetchall()
    print(f"Loaded {len(pois)} POIs.")

    # Organize POIs by category
    poi_coords_by_cat = {}
    all_poi_coords = []
    all_poi_cats = []

    for poi_id, cat, plat, plon in pois:
        all_poi_coords.append((plat, plon))
        all_poi_cats.append(cat)
        if cat not in poi_coords_by_cat:
            poi_coords_by_cat[cat] = []
        poi_coords_by_cat[cat].append((plat, plon))

    # Build KD-trees for emergency nearest neighbor search (degrees approx)
    # 1 deg lat ~ 111,000m, at 20 deg lat: 1 deg lon ~ 104,300m
    lat_scale = 111000.0
    lon_scale = 104300.0

    def make_scaled_tree(cat_list):
        if not cat_list:
            return None, None
        arr = np.array(cat_list)
        # Scale to approximate meters
        scaled = np.column_stack([arr[:, 0] * lat_scale, arr[:, 1] * lon_scale])
        return cKDTree(scaled), arr

    police_tree, police_coords = make_scaled_tree(poi_coords_by_cat.get("police", []))
    hospital_tree, hospital_coords = make_scaled_tree(poi_coords_by_cat.get("hospital", []))
    pharmacy_tree, pharmacy_coords = make_scaled_tree(poi_coords_by_cat.get("pharmacy", []))

    # Full POI KDTree for 200m radius search
    all_arr = np.array(all_poi_coords)
    scaled_all_pois = np.column_stack([all_arr[:, 0] * lat_scale, all_arr[:, 1] * lon_scale])
    full_poi_tree = cKDTree(scaled_all_pois)

    # Road coordinates scaled
    road_lats = np.array([r[3] for r in roads])
    road_lons = np.array([r[4] for r in roads])
    scaled_roads = np.column_stack([road_lats * lat_scale, road_lons * lon_scale])

    print("Querying nearest emergency POIs for all roads...")
    # Police
    if police_tree:
        pol_dists, _ = police_tree.query(scaled_roads)
    else:
        pol_dists = np.full(len(roads), 5000.0)

    # Hospital
    if hospital_tree:
        hosp_dists, _ = hospital_tree.query(scaled_roads)
    else:
        hosp_dists = np.full(len(roads), 5000.0)

    # Pharmacy
    if pharmacy_tree:
        pharm_dists, _ = pharmacy_tree.query(scaled_roads)
    else:
        pharm_dists = np.full(len(roads), 5000.0)

    print("Querying POIs within 200-meter buffer for all roads...")
    # 200 meters buffer
    buffer_radius = 200.0
    neighbor_indices = full_poi_tree.query_ball_point(scaled_roads, r=buffer_radius)

    print("Calculating safety features and scores...")
    records = []
    category_counts_map = {
        "police": 0, "hospital": 1, "pharmacy": 2, "bus_stop": 3,
        "restaurant": 4, "cafe": 5, "market": 6, "bank": 7,
        "fuel": 8, "liquor_shop": 9, "bar": 10, "park": 11
    }

    for i, r in enumerate(roads):
        road_id, raw_type, length, lat, lon = r
        clean_type = get_clean_road_type(raw_type)
        r_length = max(5.0, float(length) if length else 20.0)

        # Emergency distances
        d_police = float(pol_dists[i])
        d_hospital = float(hosp_dists[i])
        d_pharmacy = float(pharm_dists[i])

        # Nearby POI counts
        poi_idxs = neighbor_indices[i]
        counts = {k: 0 for k in category_counts_map}
        activity_count = 0

        for p_idx in poi_idxs:
            p_cat = all_poi_cats[p_idx]
            if p_cat in counts:
                counts[p_cat] += 1
            if p_cat in ACTIVITY_CATEGORIES:
                activity_count += 1

        police_count = counts["police"]
        hospital_count = counts["hospital"]
        pharmacy_count = counts["pharmacy"]
        bus_stop_count = counts["bus_stop"]
        restaurant_count = counts["restaurant"]
        cafe_count = counts["cafe"]
        market_count = counts["market"]
        bank_count = counts["bank"]
        fuel_count = counts["fuel"]
        liquor_count = counts["liquor_shop"]
        bar_count = counts["bar"]
        park_count = counts["park"]

        # Activity / Crowd Density
        # Density per meter of road length
        commercial_density = activity_count / r_length
        crowd_score = min(1.0, commercial_density / MAX_CROWD_DENSITY)
        crowd_risk = CROWD_MAX_RISK * (1.0 - crowd_score)

        # Environmental Isolation Risk
        isolation_risk = calculate_isolation_risk(activity_count)
        isolation_score = max(0.0, 15.0 - isolation_risk)

        # Lighting Risk
        # Default lighting level varies slightly by major road hierarchy for realism
        if clean_type in ["motorway", "trunk", "primary"]:
            lighting_score = 0.75
        elif clean_type in ["secondary", "tertiary"]:
            lighting_score = 0.60
        elif clean_type in ["residential", "living_street"]:
            lighting_score = 0.45
        elif clean_type in ["service", "footway", "path", "steps"]:
            lighting_score = 0.25
        else:
            lighting_score = DEFAULT_LIGHTING_LEVEL

        lighting_risk = LIGHTING_MAX_RISK * (1.0 - lighting_score)

        # Alcohol-related risk
        liquor_risk = min(MAX_LIQUOR_RISK, LIQUOR_RISK_PER_COUNT * liquor_count)
        bar_risk = min(MAX_BAR_RISK, BAR_RISK_PER_COUNT * bar_count)

        # Road Type Risk
        road_risk = ROAD_TYPE_RISK.get(clean_type, 5.0)

        # Emergency Bonus
        police_bonus = max(0.0, POLICE_BONUS_MAX - (d_police / POLICE_BONUS_SCALE))
        hospital_bonus = max(0.0, HOSPITAL_BONUS_MAX - (d_hospital / HOSPITAL_BONUS_SCALE))
        pharmacy_bonus = max(0.0, PHARMACY_BONUS_MAX - (d_pharmacy / PHARMACY_BONUS_SCALE))
        emergency_bonus = min(MAX_EMERGENCY_BONUS, police_bonus + hospital_bonus + pharmacy_bonus)

        # Total Risk & Final Safety Score
        total_risk = lighting_risk + crowd_risk + isolation_risk + liquor_risk + bar_risk + road_risk
        raw_safety_score = 100.0 - total_risk + emergency_bonus
        final_safety_score = round(max(0.0, min(100.0, raw_safety_score)), 2)
        safety_level = get_safety_level(final_safety_score)

        connectivity_score = 1.0
        emergency_access_score = round(emergency_bonus, 2)

        records.append((
            road_id,
            r_length,
            clean_type,
            round(d_police, 1),
            round(d_hospital, 1),
            round(d_pharmacy, 1),
            police_count,
            hospital_count,
            pharmacy_count,
            bus_stop_count,
            restaurant_count,
            cafe_count,
            market_count,
            bank_count,
            fuel_count,
            liquor_count,
            bar_count,
            park_count,
            round(commercial_density, 5),
            round(crowd_score, 3),
            round(isolation_score, 1),
            round(lighting_score, 2),
            connectivity_score,
            emergency_access_score,
            round(lighting_risk, 2),
            round(crowd_risk, 2),
            round(isolation_risk, 2),
            round(liquor_risk, 2),
            round(bar_risk, 2),
            round(road_risk, 2),
            round(emergency_bonus, 2),
            final_safety_score,
            safety_level
        ))

    print(f"Computed features and scores for all {len(records)} roads.")

    # Re-create/clear road_features
    print("Saving to PostgreSQL table 'road_features'...")
    cur.execute("TRUNCATE TABLE road_features;")
    conn.commit()

    insert_sql = """
    INSERT INTO road_features (
        road_id, length, road_type,
        police_distance, hospital_distance, pharmacy_distance,
        police_count, hospital_count, pharmacy_count,
        bus_stop_count, restaurant_count, cafe_count,
        market_count, bank_count, fuel_station_count,
        liquor_shop_count, bar_count, park_count,
        commercial_density, crowd_score, isolation_score,
        lighting_score, connectivity_score, emergency_access_score,
        lighting_risk, crowd_risk, isolation_risk,
        liquor_risk, bar_risk, road_risk, emergency_bonus,
        final_safety_score, safety_level
    ) VALUES %s
    """
    
    batch_size = 10000
    for start_idx in range(0, len(records), batch_size):
        batch = records[start_idx:start_idx + batch_size]
        execute_values(cur, insert_sql, batch, page_size=batch_size)
        conn.commit()
        print(f"  Saved {min(start_idx + batch_size, len(records))}/{len(records)} road features...")

    # Summary distribution
    cur.execute("""
        SELECT safety_level, count(*), round(avg(final_safety_score)::numeric, 1)
        FROM road_features
        GROUP BY safety_level
        ORDER BY avg(final_safety_score) DESC;
    """)
    dist = cur.fetchall()
    print("\n============== SAFETY SCORE DISTRIBUTION ==============")
    for level, count, avg_sc in dist:
        print(f" - {level:12s}: {count:6d} segments | Avg Score: {avg_sc}")
    print("=======================================================")

    cur.close()
    conn.close()
    print("Feature engineering & safety scoring complete!")

if __name__ == "__main__":
    main()
