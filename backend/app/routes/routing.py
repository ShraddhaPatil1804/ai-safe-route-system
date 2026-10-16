from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from backend.app.routing.router import NashikRoadNetwork
from backend.app.schemas.routing import RouteResponse, RouteComparisonResponse

router = APIRouter(tags=["Routing"])

@router.get("/route", response_model=RouteResponse)
def get_route(
    origin_lat: float = Query(..., description="Origin latitude", ge=19.0, le=21.0),
    origin_lon: float = Query(..., description="Origin longitude", ge=73.0, le=75.0),
    dest_lat: float = Query(..., description="Destination latitude", ge=19.0, le=21.0),
    dest_lon: float = Query(..., description="Destination longitude", ge=73.0, le=75.0),
    mode: str = Query("safest", description="Route mode: shortest, fastest, safest, or balanced"),
    time_of_day: str = Query("day", description="Departure time: 'day', 'night', or 'auto'")
):
    """
    Calculate a single route between origin and destination.
    Modes available: 'shortest', 'fastest', 'safest', 'balanced'
    """
    valid_modes = ["shortest", "fastest", "safest", "balanced"]
    if mode.lower() not in valid_modes:
        raise HTTPException(status_code=400, detail=f"Mode must be one of {valid_modes}")

    network = NashikRoadNetwork.get_instance()
    route_data = network.calculate_route(
        origin_lat, origin_lon, dest_lat, dest_lon,
        mode=mode.lower(),
        time_of_day=time_of_day.lower()
    )
    return RouteResponse(**route_data)

@router.get("/routes/compare", response_model=RouteComparisonResponse)
def compare_routes(
    origin_lat: float = Query(..., description="Origin latitude", ge=19.0, le=21.0),
    origin_lon: float = Query(..., description="Origin longitude", ge=73.0, le=75.0),
    dest_lat: float = Query(..., description="Destination latitude", ge=19.0, le=21.0),
    dest_lon: float = Query(..., description="Destination longitude", ge=73.0, le=75.0),
    time_of_day: str = Query("day", description="Departure time: 'day', 'night', or 'auto'")
):
    """
    Calculate and compare all routing modes: Safest, Fastest, Balanced, and Shortest.
    Includes time-aware safety weighting and independent ETA calculation.
    """
    network = NashikRoadNetwork.get_instance()
    comparison_data = network.compare_routes(
        origin_lat, origin_lon, dest_lat, dest_lon,
        time_of_day=time_of_day.lower()
    )
    return RouteComparisonResponse(**comparison_data)
