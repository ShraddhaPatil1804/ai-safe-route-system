from fastapi import APIRouter, Query, HTTPException
from backend.app.routing.router import NashikRoadNetwork
from backend.app.schemas.routing import RouteResponse, RouteComparisonResponse

router = APIRouter(tags=["Routing"])

@router.get("/route", response_model=RouteResponse)
def get_route(
    origin_lat: float = Query(..., description="Origin latitude", ge=19.0, le=21.0),
    origin_lon: float = Query(..., description="Origin longitude", ge=73.0, le=75.0),
    dest_lat: float = Query(..., description="Destination latitude", ge=19.0, le=21.0),
    dest_lon: float = Query(..., description="Destination longitude", ge=73.0, le=75.0),
    mode: str = Query("safest", description="Route mode: fastest, safest, or balanced")
):
    """
    Calculate a single route between origin and destination.
    Modes available: 'fastest', 'safest', 'balanced'
    """
    valid_modes = ["fastest", "safest", "balanced"]
    if mode.lower() not in valid_modes:
        raise HTTPException(status_code=400, detail=f"Mode must be one of {valid_modes}")

    network = NashikRoadNetwork.get_instance()
    route_data = network.calculate_route(origin_lat, origin_lon, dest_lat, dest_lon, mode=mode.lower())
    return RouteResponse(**route_data)

@router.get("/routes/compare", response_model=RouteComparisonResponse)
def compare_routes(
    origin_lat: float = Query(..., description="Origin latitude", ge=19.0, le=21.0),
    origin_lon: float = Query(..., description="Origin longitude", ge=73.0, le=75.0),
    dest_lat: float = Query(..., description="Destination latitude", ge=19.0, le=21.0),
    dest_lon: float = Query(..., description="Destination longitude", ge=73.0, le=75.0)
):
    """
    Calculate and compare all three routing modes: Fastest, Safest, and Balanced.
    """
    network = NashikRoadNetwork.get_instance()
    comparison_data = network.compare_routes(origin_lat, origin_lon, dest_lat, dest_lon)
    return RouteComparisonResponse(**comparison_data)
