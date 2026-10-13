from backend.app.routes.auth import router as auth_router
from backend.app.routes.routing import router as routing_router
from backend.app.routes.pois import router as pois_router
from backend.app.routes.safety import router as safety_router
from backend.app.routes.reports import router as reports_router
from backend.app.routes.places import router as places_router

__all__ = ["auth_router", "routing_router", "pois_router", "safety_router", "reports_router", "places_router"]

