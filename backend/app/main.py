import os
import sys
from pathlib import Path

PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from backend.app.routing.router import NashikRoadNetwork
from backend.app.routes import (
    auth_router,
    routing_router,
    pois_router,
    safety_router,
    reports_router,
    places_router
)


load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("=========================================================")
    print("Starting Women Safe Navigation System Backend (Nashik)...")
    print("=========================================================")
    # Pre-load road network into memory for fast A* routing
    network = NashikRoadNetwork.get_instance()
    try:
        network.load_network()
        print("Routing network initialized and ready!")
    except Exception as e:
        print(f"Warning: Road network database not ready or unreachable ({e}).")
        print("FastAPI server starting without pre-loaded routing graph. Connect PostgreSQL to enable routing.")
    yield
    print("Shutting down Women Safe Navigation System Backend...")

app = FastAPI(
    title="Safety-Aware Navigation System for Women in Nashik",
    description=(
        "A formula-based safety-aware navigation platform that evaluates road "
        "segments using environmental, accessibility, activity, lighting, and "
        "nearby-POI factors and combines safety with distance to recommend routes."
    ),
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for Mobile App and Web Dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Routers
app.include_router(auth_router)
app.include_router(routing_router)
app.include_router(pois_router)
app.include_router(safety_router)
app.include_router(reports_router)
app.include_router(places_router)


@app.get("/health", tags=["Health"])
def health_check():
    network = NashikRoadNetwork.get_instance()
    return {
        "status": "healthy",
        "city": "Nashik, Maharashtra",
        "system": "Formula-Based Safety-Aware Navigation",
        "graph_loaded": network.is_loaded,
        "nodes_count": network.graph.number_of_nodes() if network.is_loaded else 0,
        "edges_count": network.graph.number_of_edges() if network.is_loaded else 0
    }

if __name__ == "__main__":
    import sys
    from pathlib import Path
    project_root = str(Path(__file__).resolve().parent.parent.parent)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=False)
