"""
feature_extractor.py
=============================================================================
Spatial Crime-to-Road Feature Extraction Engine for Nashik Road Network.

Spatially associates `crime_records` with nearby road segments (`roads`)
using PostGIS ST_DWithin corridor matching (with full fallback to local
spatial indexing when database is offline).

Features computed per canonical `roads.id`:
  1. crime_count         : Total crime points within buffer corridor
  2. recent_crime_count  : Incidents within 12-month temporal window
  3. crime_density       : Incidents per kilometer (crime_count / (length / 1000))
  4. average_severity    : Mean severity weight of corridor incidents (0.0 if none)
  5. night_crime_ratio   : Fraction of incidents occurring during dark hours (0.0 if none)
  6. min_crime_distance  : Distance in meters to nearest crime point (5000.0m default)

All test records explicitly flagged: is_development_data = True
=============================================================================
"""

import os
import sys
import time
import math
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

from shapely import wkt
from shapely.geometry import Point, LineString, box
from shapely.strtree import STRtree

from backend.app.ml.config import (
    CRIME_ROAD_BUFFER_METERS,
    RECENT_CRIME_WINDOW_DAYS,
    DEFAULT_NO_CRIME_DISTANCE,
    NASHIK_BOUNDS
)

LAT_SCALE = 111000.0   # Meters per degree latitude
LON_SCALE = 104300.0   # Meters per degree longitude at ~20°N


def extract_features_postgis(cur, conn, buffer_meters: float = CRIME_ROAD_BUFFER_METERS):
    """
    Executes PostGIS corridor spatial matching directly inside PostgreSQL.
    """
    print(f"[PostGIS] Running spatial join with buffer = {buffer_meters}m...")

    # 1. Total crimes in table
    cur.execute("SELECT count(*) FROM crime_records WHERE is_development_data = TRUE;")
    total_crimes = cur.fetchone()[0]

    # 2. Number of crimes matched within buffer
    cur.execute("""
        SELECT count(DISTINCT c.id)
        FROM crime_records c
        JOIN roads r ON ST_DWithin(r.geometry::geography, c.geometry::geography, %s)
        WHERE c.is_development_data = TRUE;
    """, (buffer_meters,))
    matched_crimes = cur.fetchone()[0]
    unmatched_crimes = total_crimes - matched_crimes

    # Cutoff date for recent crimes (last 365 days from newest record)
    cur.execute("SELECT MAX(crime_date) FROM crime_records;")
    max_date = cur.fetchone()[0] or datetime.now()
    cutoff_date = max_date - timedelta(days=RECENT_CRIME_WINDOW_DAYS)

    # 3. Aggregate per road_id
    query = """
    WITH matched AS (
        SELECT 
            r.id AS road_id,
            r.length AS road_length,
            c.id AS crime_id,
            COALESCE(c.severity_weight, 2.0) AS severity,
            c.time_of_day,
            c.crime_date,
            ST_Distance(r.geometry::geography, c.geometry::geography) AS dist_m
        FROM roads r
        JOIN crime_records c 
          ON ST_DWithin(r.geometry::geography, c.geometry::geography, %s)
        WHERE r.geometry IS NOT NULL AND c.geometry IS NOT NULL
    ),
    aggregated AS (
        SELECT 
            road_id,
            COUNT(crime_id) AS c_count,
            COUNT(CASE WHEN crime_date >= %s THEN 1 END) AS rec_count,
            AVG(severity) AS avg_sev,
            COUNT(CASE WHEN time_of_day IN ('Night', 'Late Night') THEN 1 END)::float / NULLIF(COUNT(crime_id), 0) AS n_ratio,
            MIN(dist_m) AS m_dist
        FROM matched
        GROUP BY road_id
    )
    SELECT 
        r.id AS road_id,
        COALESCE(a.c_count, 0) AS crime_count,
        COALESCE(a.rec_count, 0) AS recent_crime_count,
        ROUND((COALESCE(a.c_count, 0)::float / GREATEST(0.01, r.length / 1000.0))::numeric, 4) AS crime_density,
        ROUND(COALESCE(a.avg_sev, 0.0)::numeric, 3) AS average_severity,
        ROUND(COALESCE(a.n_ratio, 0.0)::numeric, 3) AS night_crime_ratio,
        ROUND(COALESCE(a.m_dist, %s)::numeric, 1) AS min_crime_distance,
        TRUE AS is_development_data
    FROM roads r
    LEFT JOIN aggregated a ON r.id = a.road_id;
    """

    cur.execute(query, (buffer_meters, cutoff_date, DEFAULT_NO_CRIME_DISTANCE))
    rows = cur.fetchall()

    df_features = pd.DataFrame(rows, columns=[
        "road_id", "crime_count", "recent_crime_count", "crime_density",
        "average_severity", "night_crime_ratio", "min_crime_distance",
        "is_development_data"
    ])

    # Insert into road_crime_features table
    print(f"[PostGIS] Populating 'road_crime_features' table for {len(df_features)} roads...")
    cur.execute("TRUNCATE TABLE road_crime_features;")
    conn.commit()

    from psycopg2.extras import execute_values
    insert_sql = """
    INSERT INTO road_crime_features (
        road_id, crime_count, recent_crime_count, crime_density,
        average_severity, night_crime_ratio, min_crime_distance, is_development_data
    ) VALUES %s
    """
    records = [
        (
            int(r.road_id), int(r.crime_count), int(r.recent_crime_count),
            float(r.crime_density), float(r.average_severity),
            float(r.night_crime_ratio), float(r.min_crime_distance),
            bool(r.is_development_data)
        )
        for _, r in df_features.iterrows()
    ]
    execute_values(cur, insert_sql, records, page_size=5000)
    conn.commit()

    return {
        "df": df_features,
        "total_crimes": total_crimes,
        "matched_crimes": matched_crimes,
        "unmatched_crimes": unmatched_crimes,
        "mode": "PostgreSQL/PostGIS"
    }


def extract_features_offline(buffer_meters: float = CRIME_ROAD_BUFFER_METERS):
    """
    High-performance spatial fallback when PostgreSQL is offline.
    Uses Shapely STRtree spatial indexing on nodes.csv / edges.csv and synthetic crimes CSV.
    """
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    crimes_path = os.path.join(repo_root, "data", "dev_test", "synthetic_nashik_crimes_sample.csv")
    nodes_path = os.path.join(repo_root, "data", "raw", "nodes.csv")
    edges_path = os.path.join(repo_root, "data", "raw", "edges.csv")

    if not os.path.exists(crimes_path):
        raise FileNotFoundError(f"Synthetic crimes CSV not found at {crimes_path}. Run 05_download_crime.py first.")

    t0 = time.time()
    print(f"[Offline Spatial] Loading synthetic crimes from {crimes_path}...")
    crimes_df = pd.read_csv(crimes_path, comment="#")
    total_crimes = len(crimes_df)

    # Reference 12-month temporal window
    crimes_df["crime_date"] = pd.to_datetime(crimes_df["crime_date"])
    max_date = crimes_df["crime_date"].max()
    cutoff_date = max_date - timedelta(days=RECENT_CRIME_WINDOW_DAYS)
    crimes_df["is_recent"] = crimes_df["crime_date"] >= cutoff_date
    crimes_df["is_night"] = crimes_df["time_of_day"].isin(["Night", "Late Night"])

    print(f"[Offline Spatial] Loading road network from {edges_path}...")
    edges_df = pd.read_csv(edges_path, usecols=["u", "v", "length", "geometry"], low_memory=False)
    total_roads = len(edges_df)
    edges_df["road_id"] = np.arange(1, total_roads + 1, dtype=int)

    # Load node coordinates for roads missing explicit LineString geometry
    print("[Offline Spatial] Parsing road geometries...")
    nodes_df = pd.read_csv(nodes_path, usecols=["osmid", "y", "x"])
    node_coords = dict(zip(nodes_df["osmid"], zip(nodes_df["x"], nodes_df["y"])))

    # Convert road geometries to scaled meter LineStrings for fast Euclidean distance
    road_geoms = []
    valid_road_indices = []

    for idx, row in edges_df.iterrows():
        g_val = row["geometry"]
        if pd.notna(g_val) and isinstance(g_val, str) and g_val.startswith("LINESTRING"):
            try:
                line = wkt.loads(g_val)
                # Scale coordinates to approximate meters: (x * LON_SCALE, y * LAT_SCALE)
                pts = [(pt[0] * LON_SCALE, pt[1] * LAT_SCALE) for pt in line.coords]
                road_geoms.append(LineString(pts))
                valid_road_indices.append(idx)
                continue
            except Exception:
                pass
        
        # Fallback to u, v node endpoints
        u, v = row["u"], row["v"]
        if u in node_coords and v in node_coords:
            p1 = (node_coords[u][0] * LON_SCALE, node_coords[u][1] * LAT_SCALE)
            p2 = (node_coords[v][0] * LON_SCALE, node_coords[v][1] * LAT_SCALE)
            road_geoms.append(LineString([p1, p2]))
            valid_road_indices.append(idx)
        else:
            road_geoms.append(None)

    valid_mask = [g is not None for g in road_geoms]
    valid_geoms = [g for g in road_geoms if g is not None]
    valid_road_ids = edges_df.loc[valid_road_indices, "road_id"].values
    valid_lengths = edges_df.loc[valid_road_indices, "length"].values

    print(f"[Offline Spatial] Building 2D spatial index over {len(valid_geoms)} road segments...")
    tree = STRtree(valid_geoms)

    # Spatial query for each crime point
    crime_pts = [
        Point(lon * LON_SCALE, lat * LAT_SCALE)
        for lon, lat in zip(crimes_df["longitude"], crimes_df["latitude"])
    ]

    print(f"[Offline Spatial] Matching {len(crime_pts)} crime points against road corridor ({buffer_meters}m)...")
    matched_crime_indices = set()
    road_matches = {r_id: [] for r_id in valid_road_ids}

    for c_idx, pt in enumerate(crime_pts):
        # Query bounding box around point
        search_box = box(
            pt.x - buffer_meters, pt.y - buffer_meters,
            pt.x + buffer_meters, pt.y + buffer_meters
        )
        candidates = tree.query(search_box)

        pt_matched = False
        c_sev = float(crimes_df.loc[c_idx, "severity_weight"])
        c_rec = bool(crimes_df.loc[c_idx, "is_recent"])
        c_ngt = bool(crimes_df.loc[c_idx, "is_night"])

        for geom_idx in candidates:
            geom = valid_geoms[geom_idx]
            dist_m = pt.distance(geom)
            if dist_m <= buffer_meters:
                pt_matched = True
                r_id = valid_road_ids[geom_idx]
                road_matches[r_id].append({
                    "dist": dist_m,
                    "severity": c_sev,
                    "is_recent": c_rec,
                    "is_night": c_ngt
                })

        if pt_matched:
            matched_crime_indices.add(c_idx)

    matched_crimes = len(matched_crime_indices)
    unmatched_crimes = total_crimes - matched_crimes

    print("[Offline Spatial] Aggregating road-level crime metrics...")
    feature_rows = []
    all_road_ids = edges_df["road_id"].values
    all_lengths = edges_df["length"].values

    for r_idx, r_id in enumerate(all_road_ids):
        l_km = max(0.01, float(all_lengths[r_idx]) / 1000.0)
        c_list = road_matches.get(r_id, [])

        if c_list:
            cnt = len(c_list)
            rec_cnt = sum(1 for c in c_list if c["is_recent"])
            dens = round(cnt / l_km, 4)
            avg_s = round(float(np.mean([c["severity"] for c in c_list])), 3)
            ngt_ratio = round(sum(1 for c in c_list if c["is_night"]) / cnt, 3)
            m_dist = round(float(min(c["dist"] for c in c_list)), 1)
        else:
            cnt = 0
            rec_cnt = 0
            dens = 0.0
            avg_s = 0.0
            ngt_ratio = 0.0
            m_dist = DEFAULT_NO_CRIME_DISTANCE

        feature_rows.append((
            int(r_id),
            cnt,
            rec_cnt,
            dens,
            avg_s,
            ngt_ratio,
            m_dist,
            True
        ))

    df_features = pd.DataFrame(feature_rows, columns=[
        "road_id", "crime_count", "recent_crime_count", "crime_density",
        "average_severity", "night_crime_ratio", "min_crime_distance",
        "is_development_data"
    ])

    # Save to CSV fixture
    out_dir = os.path.join(repo_root, "data", "dev_test")
    os.makedirs(out_dir, exist_ok=True)
    out_csv = os.path.join(out_dir, "road_crime_features.csv")
    df_features.to_csv(out_csv, index=False)
    print(f"[Offline Spatial] Saved road crime features for {len(df_features)} roads to {out_csv} in {time.time() - t0:.2f}s")

    return {
        "df": df_features,
        "total_crimes": total_crimes,
        "matched_crimes": matched_crimes,
        "unmatched_crimes": unmatched_crimes,
        "mode": "Offline Spatial Index (STRtree / Shapely Fallback)"
    }
