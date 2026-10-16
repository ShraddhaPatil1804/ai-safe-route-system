import os
import json
import math
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional, Dict, Any

from backend.app.database import get_db, pg_engine
from backend.app.models.poi import POI
from backend.app.schemas.poi import POIOut

router = APIRouter(prefix="/pois", tags=["POIs"])

# Canonical category mapping from UI labels and alternative names to internal category IDs
CATEGORY_MAPPING = {
    "all": "all",
    "all markers": "all",
    "police": "police",
    "police station": "police",
    "hospital": "hospital",
    "hospitals": "hospital",
    "clinic": "hospital",
    "pharmacy": "pharmacy",
    "pharmacies": "pharmacy",
    "chemist": "pharmacy",
    "medical": "pharmacy",
    "restaurant": "restaurant",
    "restaurants": "restaurant",
    "dining": "restaurant",
    "cafe": "cafe",
    "cafes": "cafe",
    "coffee": "cafe",
    "bus_stop": "bus_stop",
    "bus stops": "bus_stop",
    "bus stop": "bus_stop",
    "bus_station": "bus_stop",
    "transit": "bus_stop",
    "bank": "bank",
    "banks": "bank",
    "atm": "bank",
    "fuel": "fuel",
    "petrol": "fuel",
    "petrol pump": "fuel",
    "gas": "fuel",
    "park": "park",
    "parks": "park",
    "garden": "park",
    "bar": "bar",
    "bars": "bar",
    "pub": "bar",
    "lounge": "bar",
    "school": "school",
    "schools": "school",
    "college": "college",
    "colleges": "college",
    "university": "college",
    "shop": "shop",
    "shops": "shop",
    "mall": "shop",
    "malls": "shop",
    "supermarket": "shop"
}

def load_local_pois() -> List[Dict[str, Any]]:
    """Loads consolidated real Nashik POIs from the local JSON fixture."""
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    json_path = os.path.join(repo_root, "data", "dev_test", "nashik_pois.json")
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def haversine_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2.0)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0)**2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c

@router.get("", response_model=List[POIOut])
def get_pois(
    category: Optional[str] = Query(None, description="Filter by category (police, hospital, pharmacy, restaurant, cafe, bus_stop, bank, fuel, park, bar)"),
    lat: Optional[float] = Query(None, description="Center latitude for proximity search"),
    lon: Optional[float] = Query(None, description="Center longitude for proximity search"),
    radius_meters: float = Query(25000.0, description="Search radius in meters"),
    limit: int = Query(300, ge=1, le=1000, description="Maximum number of POIs to return"),
    db: Session = Depends(get_db)
):
    """
    Retrieve POIs with optional category and proximity filtering.
    Works seamlessly against PostgreSQL/PostGIS or fallback verified Nashik dataset.
    """
    # Normalize category using category mapping
    mapped_cat = None
    if category:
        c_clean = category.strip().lower()
        mapped_cat = CATEGORY_MAPPING.get(c_clean, c_clean)

    # If PostgreSQL engine is active, attempt database query
    if pg_engine is not None:
        try:
            if lat is not None and lon is not None:
                cat_clause = "AND category = :category" if (mapped_cat and mapped_cat != "all") else ""
                sql = f"""
                    SELECT id, osm_id, name, category, latitude, longitude,
                           ST_Distance(geometry::geography, ST_MakePoint(:lon, :lat)::geography) as distance_meters
                    FROM pois
                    WHERE ST_DWithin(geometry::geography, ST_MakePoint(:lon, :lat)::geography, :radius)
                    {cat_clause}
                    ORDER BY distance_meters ASC
                    LIMIT :limit;
                """
                params = {"lat": lat, "lon": lon, "radius": radius_meters, "limit": limit}
                if mapped_cat and mapped_cat != "all":
                    params["category"] = mapped_cat
                rows = db.execute(text(sql), params).fetchall()
                if rows:
                    return [
                        POIOut(
                            id=r[0],
                            osm_id=r[1],
                            name=r[2],
                            category=r[3],
                            latitude=r[4],
                            longitude=r[5],
                            distance_meters=round(r[6], 1)
                        )
                        for r in rows
                    ]
            else:
                q = db.query(POI)
                if mapped_cat and mapped_cat != "all":
                    q = q.filter(POI.category == mapped_cat)
                db_pois = q.limit(limit).all()
                if db_pois:
                    return [
                        POIOut(
                            id=p.id,
                            osm_id=p.osm_id,
                            name=p.name,
                            category=p.category,
                            latitude=p.latitude,
                            longitude=p.longitude
                        )
                        for p in db_pois
                    ]
        except Exception as e:
            print(f"[POIs] Database query notice: {e}, falling back to verified dataset.")

    # Resilient Verified Nashik POI Dataset Engine
    all_local = load_local_pois()
    filtered = []

    for item in all_local:
        item_cat = item.get("category", "").lower()
        if mapped_cat and mapped_cat != "all":
            if item_cat != mapped_cat:
                continue

        p_lat = float(item["latitude"])
        p_lon = float(item["longitude"])
        dist_m = None

        if lat is not None and lon is not None:
            dist_m = round(haversine_distance_m(lat, lon, p_lat, p_lon), 1)
            if dist_m > radius_meters:
                continue

        filtered.append({
            "id": int(item["id"]),
            "osm_id": int(item.get("osm_id", item["id"])),
            "name": item.get("name"),
            "category": item_cat,
            "latitude": p_lat,
            "longitude": p_lon,
            "distance_meters": dist_m,
            "address": item.get("address"),
            "opening_hours": item.get("opening_hours"),
            "is_24_7": bool(item.get("is_24_7", False)),
            "is_emergency_safe_haven": bool(item.get("is_emergency_safe_haven", False))
        })

    if lat is not None and lon is not None:
        filtered.sort(key=lambda x: x["distance_meters"] if x["distance_meters"] is not None else 0)

    return [POIOut(**p) for p in filtered[:limit]]

@router.get("/emergency")
def get_emergency_facilities(
    lat: float = Query(..., description="Current latitude"),
    lon: float = Query(..., description="Current longitude"),
    db: Session = Depends(get_db)
):
    """
    Returns the closest police station, hospital, and pharmacy with emergency contact numbers.
    """
    emergency_cats = ["police", "hospital", "pharmacy"]
    results = {}

    all_local = load_local_pois()
    for cat in emergency_cats:
        matching = [p for p in all_local if p.get("category") == cat]
        if not matching:
            continue

        # Find closest
        closest = min(
            matching,
            key=lambda p: haversine_distance_m(lat, lon, p["latitude"], p["longitude"])
        )
        dist_m = round(haversine_distance_m(lat, lon, closest["latitude"], closest["longitude"]), 1)
        phone = "112" if cat == "police" else ("108" if cat == "hospital" else "102")

        results[cat] = {
            "id": closest["id"],
            "name": closest.get("name") or f"Nearest {cat.capitalize()}",
            "category": closest["category"],
            "latitude": closest["latitude"],
            "longitude": closest["longitude"],
            "distance_meters": dist_m,
            "distance_km": round(dist_m / 1000.0, 2),
            "phone": phone,
            "opening_hours": closest.get("opening_hours", "24/7" if closest.get("is_24_7") else "Standard"),
            "is_24_7": bool(closest.get("is_24_7", False))
        }

    pharmacy_24h = [p for p in all_local if p.get("category") == "pharmacy" and p.get("is_24_7")]
    if pharmacy_24h:
        closest_24h = min(pharmacy_24h, key=lambda p: haversine_distance_m(lat, lon, p["latitude"], p["longitude"]))
        d_24h = round(haversine_distance_m(lat, lon, closest_24h["latitude"], closest_24h["longitude"]), 1)
        results["pharmacy_24h"] = {
            "id": closest_24h["id"],
            "name": closest_24h.get("name"),
            "category": "pharmacy",
            "latitude": closest_24h["latitude"],
            "longitude": closest_24h["longitude"],
            "distance_meters": d_24h,
            "distance_km": round(d_24h / 1000.0, 2),
            "phone": "102",
            "opening_hours": "24/7",
            "is_24_7": True
        }

    return results

@router.get("/categories")
def get_categories(db: Session = Depends(get_db)):
    """
    Returns all supported POI categories with their actual counts in Nashik.
    """
    all_local = load_local_pois()
    counts = {}
    for p in all_local:
        c = p.get("category", "other").lower()
        counts[c] = counts.get(c, 0) + 1

    return [{"category": c, "count": cnt} for c, cnt in sorted(counts.items(), key=lambda x: x[1], reverse=True)]
