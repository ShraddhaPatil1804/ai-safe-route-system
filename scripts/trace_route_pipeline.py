"""
scripts/trace_route_pipeline.py
=============================================================================
Phase 1 Reproduction & Pipeline Tracer:
Traces 3 genuinely different origin-destination pairs from input coordinates
through node snapping, A* graph search, backend API response, and frontend mapping.
=============================================================================
"""

import sys
import os
import json

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.routing.router import NashikRoadNetwork, haversine_meters

def trace_pipeline():
    print("=" * 90)
    print("PHASE 1: TRACING 3 DISTINCT ORIGIN-DESTINATION PAIRS THROUGH ROUTING PIPELINE")
    print("=" * 90)

    net = NashikRoadNetwork.get_instance()
    net.load_network()

    pairs = [
        {
            "id": "Pair A",
            "name": "Muktidham Temple (Nashik Road) -> College Road (BYK)",
            "origin_name": "Muktidham Temple, Nashik Road",
            "origin": (19.9488, 73.8382),
            "dest_name": "College Road (BYK)",
            "dest": (20.0055, 73.7645)
        },
        {
            "id": "Pair B",
            "name": "Panchavati Ramkund -> City Center Mall (Untwadi)",
            "origin_name": "Panchavati (Ramkund)",
            "origin": (20.0080, 73.7930),
            "dest_name": "City Center Mall",
            "dest": (19.9720, 73.7710)
        },
        {
            "id": "Pair C",
            "name": "Indira Nagar -> Bhadrakali / Sarkarwada (Old Nashik)",
            "origin_name": "Indira Nagar",
            "origin": (19.9650, 73.7750),
            "dest_name": "Old Nashik (Bhadrakali)",
            "dest": (19.9961, 73.7915)
        }
    ]

    with TestClient(app) as client:
        for p in pairs:
            print("\n" + "-" * 90)
            print(f"[{p['id']}] {p['name']}")
            print("-" * 90)

            o_lat, o_lon = p["origin"]
            d_lat, d_lon = p["dest"]

            print(f"1. Frontend Input Coordinates Received:")
            print(f"   Origin:      ({o_lat}, {o_lon}) [{p['origin_name']}]")
            print(f"   Destination: ({d_lat}, {d_lon}) [{p['dest_name']}]")

            # Graph status
            g_nodes = net.graph.number_of_nodes()
            g_edges = net.graph.number_of_edges()
            print(f"\n2. Road Graph Used:")
            print(f"   Total Graph Nodes: {g_nodes} | Total Edges: {g_edges}")

            # Node snapping
            start_node = net.find_nearest_node(o_lat, o_lon)
            end_node = net.find_nearest_node(d_lat, d_lon)
            s_node_data = net.graph.nodes[start_node]
            e_node_data = net.graph.nodes[end_node]
            snap_dist_origin = haversine_meters(o_lat, o_lon, s_node_data["lat"], s_node_data["lon"])
            snap_dist_dest = haversine_meters(d_lat, d_lon, e_node_data["lat"], e_node_data["lon"])

            print(f"\n3. Road-Node Snapping Results:")
            print(f"   Origin Snapped Node ID:      {start_node} at ({s_node_data['lat']:.5f}, {s_node_data['lon']:.5f}) [Distance: {snap_dist_origin:.1f}m]")
            print(f"   Destination Snapped Node ID: {end_node} at ({e_node_data['lat']:.5f}, {e_node_data['lon']:.5f}) [Distance: {snap_dist_dest:.1f}m]")
            assert start_node != end_node, "Error: Origin and Destination snapped to identical node!"

            # API Call
            params = {
                "origin_lat": o_lat, "origin_lon": o_lon,
                "dest_lat": d_lat, "dest_lon": d_lon
            }
            api_res = client.get("/routes/compare", params=params)
            assert api_res.status_code == 200, f"API Error: {api_res.status_code} - {api_res.text}"
            data = api_res.json()

            print(f"\n4. Backend Route Calculation & API Response:")
            for mode in ["fastest", "balanced", "safest"]:
                r = data[mode]
                dist_km = r["distance_km"]
                time_min = r["estimated_time_minutes"]
                score = r["safety_score"]
                level = r["safety_level"]
                coords = r["geometry"]["coordinates"]
                segments = r.get("segments", [])
                road_ids = [s["road_id"] for s in segments]

                # Calculate total routing cost across path
                # Re-calculate cost using mode cost function
                print(f"   Mode: {mode.upper():8s} | Dist: {dist_km:5.2f} km | Time: {time_min:2d} min | Score: {score:4.1f} ({level:8s}) | Segments: {len(segments)} | Coords: {len(coords)} pts")
                print(f"     First 5 Road IDs: {road_ids[:5]}")
                print(f"     Frontend Card Display: '{time_min} min ({dist_km} km)' with SafetyBadge '{score}/100'")

    print("\n" + "=" * 90)
    print("PHASE 1 TRACING COMPLETED SUCCESSFULLY")
    print("=" * 90)

if __name__ == "__main__":
    trace_pipeline()
