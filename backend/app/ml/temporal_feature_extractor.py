"""
temporal_feature_extractor.py
=============================================================================
Phase 5: Leakage-Safe Temporal Crime Feature & Future Target Extractor

Splits crime records by an explicit cutoff date:
  - Historical Window (crime_date < CUTOFF): Used ONLY to construct input features.
  - Future Prediction Window (crime_date >= CUTOFF): Used ONLY to construct target.

Strict Leakage Invariant:
  No future crime records or features are ever present in the feature matrix X.
=============================================================================
"""

import os
import sys
import time
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from shapely import wkt
from shapely.geometry import Point, LineString, box
from shapely.strtree import STRtree

from backend.app.ml.config import (
    CRIME_ROAD_BUFFER_METERS,
    DEFAULT_NO_CRIME_DISTANCE,
    TEMPORAL_CUTOFF_DATE,
    TEMPORAL_RECENT_DAYS
)

LAT_SCALE = 111000.0   # Meters per degree latitude
LON_SCALE = 104300.0   # Meters per degree longitude at ~20°N


def extract_temporal_features_and_target(
    cutoff_date_str: str = TEMPORAL_CUTOFF_DATE,
    buffer_meters: float = CRIME_ROAD_BUFFER_METERS,
    save_csv: bool = True
) -> dict:
    """
    Extracts road-level historical features (T < cutoff) and future target (T >= cutoff).
    Enforces strict temporal separation and returns the combined clean dataset.
    """
    t0 = time.time()
    cutoff_dt = pd.to_datetime(cutoff_date_str)

    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    crimes_path = os.path.join(repo_root, "data", "dev_test", "synthetic_nashik_crimes_sample.csv")
    nodes_path = os.path.join(repo_root, "data", "raw", "nodes.csv")
    edges_path = os.path.join(repo_root, "data", "raw", "edges.csv")

    if not os.path.exists(crimes_path):
        raise FileNotFoundError(f"Synthetic crimes CSV not found at {crimes_path}")

    print(f"[Temporal Extractor] Cutoff Date: {cutoff_dt}")
    print(f"[Temporal Extractor] Loading crimes from {crimes_path}...")
    crimes_df = pd.read_csv(crimes_path, comment="#")
    crimes_df["crime_date"] = pd.to_datetime(crimes_df["crime_date"])

    # 1. Temporal Partitioning of Crimes
    hist_crimes = crimes_df[crimes_df["crime_date"] < cutoff_dt].copy().reset_index(drop=True)
    fut_crimes = crimes_df[crimes_df["crime_date"] >= cutoff_dt].copy().reset_index(drop=True)

    print(f"  - Total crime records: {len(crimes_df)}")
    print(f"  - Historical crimes (T < {cutoff_dt}): {len(hist_crimes)} records (Earliest: {hist_crimes['crime_date'].min()}, Latest: {hist_crimes['crime_date'].max()})")
    print(f"  - Future crimes     (T >= {cutoff_dt}): {len(fut_crimes)} records (Earliest: {fut_crimes['crime_date'].min()}, Latest: {fut_crimes['crime_date'].max()})")

    # Assert strict date non-overlap
    assert hist_crimes["crime_date"].max() < cutoff_dt, "LEAKAGE DETECTED: Historical crimes include dates on or after cutoff!"
    assert fut_crimes["crime_date"].min() >= cutoff_dt, "LEAKAGE DETECTED: Future crimes include dates before cutoff!"

    # 2. Historical Recency & Night flags (historical only)
    recent_hist_cutoff = cutoff_dt - timedelta(days=TEMPORAL_RECENT_DAYS)
    hist_crimes["is_recent"] = hist_crimes["crime_date"] >= recent_hist_cutoff
    hist_crimes["is_night"] = hist_crimes["time_of_day"].isin(["Night", "Late Night"])

    # 3. Load Road Network
    print(f"[Temporal Extractor] Loading road network from {edges_path}...")
    edges_df = pd.read_csv(edges_path, usecols=["u", "v", "length", "highway", "oneway", "geometry"], low_memory=False)
    total_roads = len(edges_df)
    edges_df["road_id"] = np.arange(1, total_roads + 1, dtype=int)

    print(f"[Temporal Extractor] Parsing road geometries ({total_roads} edges)...")
    nodes_df = pd.read_csv(nodes_path, usecols=["osmid", "y", "x"])
    node_coords = dict(zip(nodes_df["osmid"], zip(nodes_df["x"], nodes_df["y"])))

    road_geoms = []
    valid_road_indices = []

    for idx, row in edges_df.iterrows():
        g_val = row["geometry"]
        if pd.notna(g_val) and isinstance(g_val, str) and g_val.startswith("LINESTRING"):
            try:
                line = wkt.loads(g_val)
                pts = [(pt[0] * LON_SCALE, pt[1] * LAT_SCALE) for pt in line.coords]
                road_geoms.append(LineString(pts))
                valid_road_indices.append(idx)
                continue
            except Exception:
                pass

        u, v = row["u"], row["v"]
        if u in node_coords and v in node_coords:
            p1 = (node_coords[u][0] * LON_SCALE, node_coords[u][1] * LAT_SCALE)
            p2 = (node_coords[v][0] * LON_SCALE, node_coords[v][1] * LAT_SCALE)
            road_geoms.append(LineString([p1, p2]))
            valid_road_indices.append(idx)
        else:
            road_geoms.append(None)

    valid_geoms = [g for g in road_geoms if g is not None]
    valid_road_ids = edges_df.loc[valid_road_indices, "road_id"].values

    print(f"[Temporal Extractor] Building spatial index over {len(valid_geoms)} road geometries...")
    tree = STRtree(valid_geoms)

    def match_crimes_to_roads(crimes_subset_df):
        pts = [
            Point(lon * LON_SCALE, lat * LAT_SCALE)
            for lon, lat in zip(crimes_subset_df["longitude"], crimes_subset_df["latitude"])
        ]
        road_matched_records = {r_id: [] for r_id in edges_df["road_id"].values}
        matched_pts_set = set()

        for c_idx, pt in enumerate(pts):
            search_box = box(
                pt.x - buffer_meters, pt.y - buffer_meters,
                pt.x + buffer_meters, pt.y + buffer_meters
            )
            cands = tree.query(search_box)
            pt_matched = False
            c_row = crimes_subset_df.iloc[c_idx]

            for g_idx in cands:
                geom = valid_geoms[g_idx]
                d = pt.distance(geom)
                if d <= buffer_meters:
                    pt_matched = True
                    r_id = valid_road_ids[g_idx]
                    road_matched_records[r_id].append({
                        "dist": d,
                        "severity": float(c_row.get("severity_weight", 2.0)),
                        "is_recent": bool(c_row.get("is_recent", False)),
                        "is_night": bool(c_row.get("is_night", False))
                    })
            if pt_matched:
                matched_pts_set.add(c_idx)

        return road_matched_records, len(matched_pts_set)

    print(f"[Temporal Extractor] Matching historical crimes within corridor ({buffer_meters}m)...")
    hist_matches, h_pts_matched = match_crimes_to_roads(hist_crimes)
    print(f"  - Matched {h_pts_matched}/{len(hist_crimes)} historical crime points")

    print(f"[Temporal Extractor] Matching future crimes within corridor ({buffer_meters}m)...")
    fut_matches, f_pts_matched = match_crimes_to_roads(fut_crimes)
    print(f"  - Matched {f_pts_matched}/{len(fut_crimes)} future crime points")

    # 4. Construct Road-Level Features & Target
    print("[Temporal Extractor] Constructing road-level feature and target rows...")
    feature_rows = []
    all_lengths = edges_df["length"].fillna(25.0).clip(lower=2.0).values
    all_road_ids = edges_df["road_id"].values

    for r_idx, r_id in enumerate(all_road_ids):
        l_km = max(0.01, float(all_lengths[r_idx]) / 1000.0)

        # Historical attributes
        h_list = hist_matches.get(r_id, [])
        if h_list:
            h_count = len(h_list)
            h_rec_count = sum(1 for c in h_list if c["is_recent"])
            h_dens = round(h_count / l_km, 4)
            h_avg_sev = round(float(np.mean([c["severity"] for c in h_list])), 3)
            h_ngt_ratio = round(sum(1 for c in h_list if c["is_night"]) / h_count, 3)
            h_min_dist = round(float(min(c["dist"] for c in h_list)), 1)
        else:
            h_count = 0
            h_rec_count = 0
            h_dens = 0.0
            h_avg_sev = 0.0
            h_ngt_ratio = 0.0
            h_min_dist = DEFAULT_NO_CRIME_DISTANCE

        # Future attributes (TARGET ONLY)
        f_list = fut_matches.get(r_id, [])
        f_count = len(f_list)

        feature_rows.append((
            int(r_id),
            # Historical features
            h_count,
            h_rec_count,
            h_dens,
            h_avg_sev,
            h_ngt_ratio,
            h_min_dist,
            # Target
            f_count
        ))

    df_temporal = pd.DataFrame(feature_rows, columns=[
        "road_id",
        "historical_crime_count",
        "historical_recent_crime_count",
        "historical_crime_density",
        "historical_average_severity",
        "historical_night_crime_ratio",
        "historical_min_crime_distance",
        "future_crime_count"
    ])

    if save_csv:
        out_path = os.path.join(repo_root, "data", "dev_test", "road_temporal_features.csv")
        df_temporal.to_csv(out_path, index=False)
        print(f"[Temporal Extractor] Saved temporal dataset to {out_path} in {time.time() - t0:.2f}s")

    return {
        "df": df_temporal,
        "cutoff_date": str(cutoff_dt),
        "hist_crimes_total": len(hist_crimes),
        "hist_crimes_matched": h_pts_matched,
        "fut_crimes_total": len(fut_crimes),
        "fut_crimes_matched": f_pts_matched,
        "total_roads": len(df_temporal),
        "active_hist_roads": int((df_temporal["historical_crime_count"] > 0).sum()),
        "active_fut_roads": int((df_temporal["future_crime_count"] > 0).sum())
    }
