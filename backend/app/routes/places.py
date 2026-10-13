import os
import json
import re
import math
import requests
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text

from backend.app.database import get_db, pg_engine
from backend.app.services.nashik_places import search_catalog

router = APIRouter(prefix="/places", tags=["Places & Geocoding"])

# Bounds for Nashik area sanity check
NASHIK_BOUNDS = {
    "min_lat": 19.50,
    "max_lat": 20.40,
    "min_lon": 73.40,
    "max_lon": 74.30
}

def is_within_nashik(lat: float, lon: float) -> bool:
    return (NASHIK_BOUNDS["min_lat"] <= lat <= NASHIK_BOUNDS["max_lat"] and
            NASHIK_BOUNDS["min_lon"] <= lon <= NASHIK_BOUNDS["max_lon"])

def load_verified_pois() -> List[Dict[str, Any]]:
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    json_path = os.path.join(repo_root, "data", "dev_test", "nashik_pois.json")
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

@router.get("/search")
def search_places(
    q: str = Query(..., min_length=1, description="Search term for any place, locality, shop, street, or landmark in Nashik"),
    limit: int = Query(10, ge=1, le=30),
    db: Session = Depends(get_db)
):
    query_str = q.strip()
    if not query_str:
        return []

    results: List[Dict[str, Any]] = []
    seen_names = set()

    # 1. Direct coordinate check (e.g. "19.998, 73.782")
    coord_match = re.match(r"^\s*([+-]?\d+(?:\.\d+)?)\s*,\s*([+-]?\d+(?:\.\d+)?)\s*$", query_str)
    if coord_match:
        lat = float(coord_match.group(1))
        lon = float(coord_match.group(2))
        if is_within_nashik(lat, lon):
            return [{
                "name": f"Coordinates ({round(lat, 4)}, {round(lon, 4)})",
                "tag": "Exact Location",
                "latitude": lat,
                "longitude": lon,
                "source": "coordinates"
            }]

    # 2. Search Nashik Built-in Catalog (Localities, Chowks, Temples, Stations)
    catalog_matches = search_catalog(query_str, limit=limit)
    for m in catalog_matches:
        key = (round(m["latitude"], 3), round(m["longitude"], 3))
        if key not in seen_names:
            seen_names.add(key)
            results.append(m)

    # 3. Search Verified POIs (Hospitals, Police, Cafes, Restaurants, Bus Stops, Banks, Fuel, Parks, Bars)
    if pg_engine is not None:
        try:
            poi_sql = """
                SELECT name, category, latitude, longitude
                FROM pois
                WHERE name ILIKE :term
                ORDER BY 
                    CASE WHEN name ILIKE :prefix THEN 1 ELSE 2 END,
                    name ASC
                LIMIT :lim;
            """
            poi_rows = db.execute(text(poi_sql), {
                "term": f"%{query_str}%",
                "prefix": f"{query_str}%",
                "lim": max(5, limit - len(results))
            }).fetchall()

            for r in poi_rows:
                p_name, p_cat, p_lat, p_lon = r
                if not p_name:
                    continue
                key = (round(p_lat, 3), round(p_lon, 3))
                if key not in seen_names:
                    seen_names.add(key)
                    results.append({
                        "name": p_name,
                        "tag": p_cat.replace("_", " ").title(),
                        "latitude": float(p_lat),
                        "longitude": float(p_lon),
                        "source": "poi_database"
                    })
        except Exception as e:
            pass
    else:
        # Offline verified POIs dataset search
        q_lower = query_str.lower()
        verified_pois = load_verified_pois()
        for p in verified_pois:
            name = p.get("name", "")
            cat = p.get("category", "")
            if q_lower in name.lower() or q_lower in cat.lower():
                key = (round(p["latitude"], 3), round(p["longitude"], 3))
                if key not in seen_names:
                    seen_names.add(key)
                    results.append({
                        "name": name,
                        "tag": cat.replace("_", " ").title(),
                        "latitude": float(p["latitude"]),
                        "longitude": float(p["longitude"]),
                        "address": p.get("address", ""),
                        "source": "verified_pois"
                    })
                if len(results) >= limit:
                    break

    # 4. Search Named Roads from edges if needed
    if len(results) < limit and pg_engine is not None:
        try:
            road_sql = """
                SELECT road_name, ST_Y(ST_Centroid(ST_Union(geometry))) as lat, ST_X(ST_Centroid(ST_Union(geometry))) as lon
                FROM roads
                WHERE road_name IS NOT NULL AND road_name != '' AND road_name ILIKE :term
                GROUP BY road_name
                LIMIT :lim;
            """
            road_rows = db.execute(text(road_sql), {
                "term": f"%{query_str}%",
                "lim": min(5, limit - len(results))
            }).fetchall()

            for r in road_rows:
                r_name, r_lat, r_lon = r
                if r_name and r_lat and r_lon:
                    key = (round(r_lat, 3), round(r_lon, 3))
                    if key not in seen_names:
                        seen_names.add(key)
                        results.append({
                            "name": f"{r_name}, Nashik",
                            "tag": "Road / Street",
                            "latitude": float(r_lat),
                            "longitude": float(r_lon),
                            "source": "road_network"
                        })
        except Exception as e:
            pass

    # 5. Live OSM Geocoder (for any specific street, building, or society)
    if len(results) < 3:
        try:
            url = f"https://nominatim.openstreetmap.org/search?q={query_str}+Nashik+Maharashtra&format=json&limit=5"
            resp = requests.get(
                url,
                headers={"User-Agent": "NashikWomenNavSystem/1.0 (contact: info@women-nav-nashik.in)"},
                timeout=4
            )
            if resp.status_code == 200:
                osm_items = resp.json()
                for item in osm_items:
                    lat = float(item["lat"])
                    lon = float(item["lon"])
                    if is_within_nashik(lat, lon):
                        key = (round(lat, 3), round(lon, 3))
                        if key not in seen_names:
                            seen_names.add(key)
                            disp = item.get("display_name", "")
                            parts = [p.strip() for p in disp.split(",") if p.strip()]
                            short_name = ", ".join(parts[:3]) if len(parts) >= 3 else disp
                            results.append({
                                "name": short_name,
                                "tag": "OSM Place",
                                "latitude": lat,
                                "longitude": lon,
                                "source": "osm_geocoder"
                            })
                            if len(results) >= limit:
                                break
        except Exception:
            pass

    return results[:limit]
