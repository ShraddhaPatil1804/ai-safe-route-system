import json
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional, List, Dict, Any

from backend.app.database import get_db, pg_engine
from backend.app.routing.router import NashikRoadNetwork

router = APIRouter(tags=["Safety & Roads"])

@router.get("/safety/{road_id}")
def get_road_safety(road_id: int, db: Session = Depends(get_db)):
    """
    Get detailed safety metrics and factor breakdown for a specific road segment.
    """
    if pg_engine is not None:
        try:
            sql = """
                SELECT r.id, r.road_name, r.road_type, r.length,
                       rf.final_safety_score, rf.safety_level,
                       rf.police_distance, rf.hospital_distance, rf.pharmacy_distance,
                       rf.police_count, rf.hospital_count, rf.pharmacy_count,
                       rf.bus_stop_count, rf.restaurant_count, rf.cafe_count,
                       rf.commercial_density, rf.crowd_score, rf.isolation_score,
                       rf.lighting_score, rf.lighting_risk, rf.crowd_risk,
                       rf.isolation_risk, rf.liquor_risk, rf.bar_risk, rf.road_risk,
                       rf.emergency_bonus, ST_AsGeoJSON(r.geometry) as geojson
                FROM roads r
                JOIN road_features rf ON r.id = rf.road_id
                WHERE r.id = :road_id;
            """
            row = db.execute(text(sql), {"road_id": road_id}).fetchone()
            if row:
                return {
                    "road_id": row[0],
                    "name": row[1] or "Unnamed Road",
                    "road_type": row[2],
                    "length_meters": round(row[3], 1),
                    "final_safety_score": row[4],
                    "safety_level": row[5],
                    "factors": {
                        "lighting_score": row[18],
                        "lighting_risk": row[19],
                        "crowd_score": row[16],
                        "crowd_risk": row[20],
                        "isolation_score": row[17],
                        "isolation_risk": row[21],
                        "liquor_risk": row[22],
                        "bar_risk": row[23],
                        "road_type_risk": row[24],
                        "emergency_bonus": row[25],
                    },
                    "nearby_counts": {
                        "police": row[9],
                        "hospital": row[10],
                        "pharmacy": row[11],
                        "bus_stop": row[12],
                        "restaurant": row[13],
                        "cafe": row[14],
                    },
                    "emergency_distances": {
                        "police_meters": row[6],
                        "hospital_meters": row[7],
                        "pharmacy_meters": row[8],
                    },
                    "geometry": json.loads(row[26]) if row[26] else None
                }
        except Exception:
            pass

    # In-memory graph fallback
    network = NashikRoadNetwork.get_instance()
    road_data = network.get_road_by_id(road_id)
    if not road_data:
        raise HTTPException(status_code=404, detail="Road segment not found")
    return road_data

@router.get("/roads")
def get_roads(
    min_lat: float = Query(19.85),
    min_lon: float = Query(73.68),
    max_lat: float = Query(20.10),
    max_lon: float = Query(73.92),
    limit: int = Query(300, ge=1, le=2000),
    db: Session = Depends(get_db)
):
    """
    Get road segments within a bounding box.
    """
    if pg_engine is not None:
        try:
            sql = """
                SELECT r.id, r.road_name, r.road_type, r.length,
                       rf.final_safety_score, rf.safety_level,
                       ST_AsGeoJSON(r.geometry) as geojson
                FROM roads r
                JOIN road_features rf ON r.id = rf.road_id
                WHERE ST_Intersects(r.geometry, ST_MakeEnvelope(:min_lon, :min_lat, :max_lon, :max_lat, 4326))
                LIMIT :limit;
            """
            rows = db.execute(text(sql), {
                "min_lat": min_lat, "min_lon": min_lon,
                "max_lat": max_lat, "max_lon": max_lon,
                "limit": limit
            }).fetchall()

            features = []
            for r in rows:
                geom = json.loads(r[6]) if r[6] else None
                if geom:
                    features.append({
                        "type": "Feature",
                        "properties": {
                            "id": r[0],
                            "name": r[1] or "",
                            "road_type": r[2],
                            "length": r[3],
                            "safety_score": r[4],
                            "safety_level": r[5]
                        },
                        "geometry": geom
                    })

            return {
                "type": "FeatureCollection",
                "features": features
            }
        except Exception:
            pass

    # In-memory graph fallback
    network = NashikRoadNetwork.get_instance()
    features = network.get_roads_in_bbox(min_lat, min_lon, max_lat, max_lon, limit=limit)
    return {
        "type": "FeatureCollection",
        "features": features
    }

@router.get("/heatmap")
def get_safety_heatmap(
    min_lat: float = Query(19.90),
    min_lon: float = Query(73.70),
    max_lat: float = Query(20.06),
    max_lon: float = Query(73.88),
    level: Optional[str] = Query(None, description="Filter by level: 'Very Safe', 'Safe', 'Moderate', 'Risky', 'High Risk'"),
    time_of_day: Optional[str] = Query("day", description="Departure time: 'day' or 'night'"),
    limit: int = Query(500, ge=1, le=3000),
    db: Session = Depends(get_db)
):
    """
    Returns GeoJSON FeatureCollection of road segments color-coded by estimated safety score.
    Legend: Estimated Safety Score
    - Very Safe (>=80): #10B981 (Green)
    - Safe (65-79): #34D399 (Emerald Green)
    - Moderate (50-64): #FBBF24 (Yellow/Amber)
    - Risky (35-49): #F97316 (Orange)
    - High Risk (<35): #EF4444 (Red)
    """
    is_night = (time_of_day.lower() == "night") if time_of_day else False

    if pg_engine is not None:
        try:
            level_filter = "AND rf.safety_level = :level" if level else ""
            sql = f"""
                SELECT r.id, r.road_name, r.road_type,
                       rf.final_safety_score, rf.safety_level,
                       ST_AsGeoJSON(r.geometry) as geojson
                FROM roads r
                JOIN road_features rf ON r.id = rf.road_id
                WHERE ST_Intersects(r.geometry, ST_MakeEnvelope(:min_lon, :min_lat, :max_lon, :max_lat, 4326))
                {level_filter}
                ORDER BY rf.final_safety_score DESC
                LIMIT :limit;
            """
            params = {
                "min_lat": min_lat, "min_lon": min_lon,
                "max_lat": max_lat, "max_lon": max_lon,
                "limit": limit
            }
            if level:
                params["level"] = level

            rows = db.execute(text(sql), params).fetchall()

            color_map = {
                "Very Safe": "#10B981",
                "Safe": "#34D399",
                "Moderate": "#FBBF24",
                "Risky": "#F97316",
                "High Risk": "#EF4444"
            }

            features = []
            for r in rows:
                geom = json.loads(r[5]) if r[5] else None
                if geom:
                    s_level = r[4] or "Moderate"
                    features.append({
                        "type": "Feature",
                        "properties": {
                            "id": r[0],
                            "name": r[1] or "",
                            "road_type": r[2],
                            "safety_score": r[3],
                            "safety_level": s_level,
                            "color": color_map.get(s_level, "#FBBF24")
                        },
                        "geometry": geom
                    })

            return {
                "type": "FeatureCollection",
                "legend": "Estimated Safety Score",
                "features": features
            }
        except Exception:
            pass

    # In-memory graph fallback
    network = NashikRoadNetwork.get_instance()
    features = network.get_heatmap_features(
        min_lat=min_lat, min_lon=min_lon,
        max_lat=max_lat, max_lon=max_lon,
        level=level, limit=limit,
        is_night=is_night
    )
    return {
        "type": "FeatureCollection",
        "legend": "Estimated Safety Score",
        "features": features
    }
