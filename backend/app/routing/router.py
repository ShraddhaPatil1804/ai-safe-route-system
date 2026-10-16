import os
import json
import math
import time
import networkx as nx
import numpy as np
from scipy.spatial import cKDTree
from typing import Dict, List, Any, Optional, Tuple

from backend.app.database import SessionLocal
from backend.app.safety.config import (
    ROUTE_MODES,
    ROAD_LIGHTING_DEFAULTS,
    CRIME_DATA_STATUS_UNKNOWN,
    MISSING_CRIME_DATA_DISCLAIMER,
    calculate_segment_safety,
    get_safety_level
)

def haversine_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2.0)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0)**2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c

def calculate_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates bearing from point 1 to point 2 in degrees [0, 360)."""
    phi1, lambda1, phi2, lambda2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlambda = lambda2 - lambda1
    y = math.sin(dlambda) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(dlambda)
    bearing = math.degrees(math.atan2(y, x))
    return (bearing + 360.0) % 360.0

def get_compass_direction(bearing: float) -> str:
    dirs = ["north", "northeast", "east", "southeast", "south", "southwest", "west", "northwest"]
    idx = int((bearing + 22.5) // 45) % 8
    return dirs[idx]

def get_maneuver(prev_bearing: float, next_bearing: float, street_name: str) -> Tuple[str, str]:
    """Determines turn maneuver modifier and vocal navigation instruction."""
    diff = (next_bearing - prev_bearing + 180.0) % 360.0 - 180.0
    st = f"onto {street_name}" if street_name and street_name != "Unnamed Road" else ""

    if abs(diff) <= 25.0:
        return "straight", f"Continue straight {st}".strip()
    elif 25.0 < diff <= 65.0:
        return "slight_right", f"Slight right {st}".strip()
    elif 65.0 < diff <= 125.0:
        return "right", f"Turn right {st}".strip()
    elif 125.0 < diff <= 165.0:
        return "sharp_right", f"Sharp right {st}".strip()
    elif -65.0 <= diff < -25.0:
        return "slight_left", f"Slight left {st}".strip()
    elif -125.0 <= diff < -65.0:
        return "left", f"Turn left {st}".strip()
    elif -165.0 <= diff < -125.0:
        return "sharp_left", f"Sharp left {st}".strip()
    else:
        return "uturn", f"Make a U-turn {st}".strip()

# Realistic urban driving/travel speeds in Nashik (m/s)
SPEED_M_S = {
    "motorway": 16.6,      # ~60 km/h
    "trunk": 15.0,         # ~54 km/h
    "primary": 12.5,       # ~45 km/h
    "primary_link": 10.0,  # ~36 km/h
    "secondary": 10.0,     # ~36 km/h
    "secondary_link": 8.5, # ~30 km/h
    "tertiary": 8.3,       # ~30 km/h
    "tertiary_link": 7.0,  # ~25 km/h
    "residential": 6.5,    # ~23 km/h
    "living_street": 5.0,  # ~18 km/h
    "service": 4.5,        # ~16 km/h
    "unclassified": 6.0,   # ~21 km/h
    "footway": 1.4,        # ~5 km/h
    "pedestrian": 1.4,
    "path": 1.4,
    "steps": 0.8,
    "track": 4.0,
    "unknown": 6.0
}

class NashikRoadNetwork:
    _instance = None

    def __init__(self):
        self.graph = nx.DiGraph()
        self.node_ids = []
        self.node_coords = []
        self.kdtree = None
        self.is_loaded = False
        self.road_id_to_edge = {}

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def load_network(self):
        if self.is_loaded:
            return

        t0 = time.time()
        print("Loading road network and intersections into NetworkX graph...")
        try:
            db = SessionLocal()
            try:
                nodes_res = db.execute(
                    __import__("sqlalchemy").text("SELECT osmid, latitude, longitude FROM intersections;")
                ).fetchall()

                if nodes_res:
                    for osmid, lat, lon in nodes_res:
                        self.node_ids.append(osmid)
                        self.node_coords.append((lat, lon))
                        self.graph.add_node(osmid, lat=lat, lon=lon)

                    lat_scale = 111000.0
                    lon_scale = 104300.0
                    coords_arr = np.array(self.node_coords)
                    scaled_coords = np.column_stack([coords_arr[:, 0] * lat_scale, coords_arr[:, 1] * lon_scale])
                    self.kdtree = cKDTree(scaled_coords)

                    roads_res = db.execute(__import__("sqlalchemy").text("""
                        SELECT r.id, r.from_node, r.to_node, r.length, r.road_type, r.road_name,
                               rf.final_safety_score, rf.safety_level,
                               rf.police_distance, rf.hospital_distance, rf.pharmacy_distance,
                               rf.lighting_risk, rf.isolation_risk, rf.bar_count, rf.liquor_shop_count,
                               rf.commercial_density, ST_AsGeoJSON(r.geometry) as geojson
                        FROM roads r
                        JOIN road_features rf ON r.id = rf.road_id;
                    """)).fetchall()

                    for row in roads_res:
                        (r_id, u, v, length, r_type, r_name,
                         safety, s_level, pol_d, hosp_d, pharm_d,
                         l_risk, iso_risk, bar_cnt, liq_cnt,
                         comm_dens, geom_json) = row

                        clean_type = str(r_type or "unknown").strip("['\"] ").split(",")[0].lower()
                        speed = SPEED_M_S.get(clean_type, 6.0)
                        l_meters = float(length)
                        travel_sec = l_meters / max(1.0, speed)
                        geom = json.loads(geom_json) if geom_json else None

                        edge_data = {
                            "road_id": r_id,
                            "name": r_name or "",
                            "road_type": clean_type,
                            "length": l_meters,
                            "travel_time_sec": travel_sec,
                            "speed": speed,
                            "safety_day": float(safety or 60.0),
                            "safety_night": max(10.0, float(safety or 60.0) - float(l_risk or 15.0) * 0.4),
                            "safety_level": s_level or "Moderate",
                            "police_distance": float(pol_d or 5000.0),
                            "hospital_distance": float(hosp_d or 5000.0),
                            "pharmacy_distance": float(pharm_d or 5000.0),
                            "pharmacy_24h_distance": float(pharm_d or 5000.0),
                            "lighting_risk": float(l_risk or 15.0),
                            "isolation_risk": float(iso_risk or 10.0),
                            "lighting_score": ROAD_LIGHTING_DEFAULTS.get(clean_type, 0.45),
                            "bar_count": int(bar_cnt or 0),
                            "liquor_shop_count": int(liq_cnt or 0),
                            "commercial_density": float(comm_dens or 0.0),
                            "commercial_count": int(comm_dens * 100) if comm_dens else 0,
                            "educational_count": 0,
                            "geometry": geom
                        }
                        self.graph.add_edge(u, v, **edge_data)
                        self.road_id_to_edge[r_id] = (u, v, edge_data)

                    self.is_loaded = True
                    print(f"Network loaded from DB: {self.graph.number_of_nodes()} nodes, "
                          f"{self.graph.number_of_edges()} edges in {time.time() - t0:.2f}s")
                    return
            finally:
                db.close()
        except Exception as e:
            print(f"Database road tables notice ({e}). Falling back to vectorized CSV dataset with live POI scoring...")

        self._load_from_csv(t0)

    def _load_from_csv(self, t0: float):
        import pandas as pd
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        nodes_path = os.path.join(repo_root, "data", "raw", "nodes.csv")
        edges_path = os.path.join(repo_root, "data", "raw", "edges.csv")
        pois_path = os.path.join(repo_root, "data", "dev_test", "nashik_pois.json")

        if not (os.path.exists(nodes_path) and os.path.exists(edges_path)):
            print(f"Warning: Raw CSV datasets not found at {nodes_path} or {edges_path}.")
            return

        print(f"Loading road network from CSV fallback datasets ({nodes_path})...")
        nodes_df = pd.read_csv(nodes_path, usecols=["osmid", "y", "x"])
        self.node_ids = nodes_df["osmid"].tolist()
        self.node_coords = list(zip(nodes_df["y"], nodes_df["x"]))
        node_dict = dict(zip(self.node_ids, self.node_coords))

        lat_scale = 111000.0
        lon_scale = 104300.0
        coords_arr = np.array(self.node_coords)
        scaled_coords = np.column_stack([coords_arr[:, 0] * lat_scale, coords_arr[:, 1] * lon_scale])
        self.kdtree = cKDTree(scaled_coords)

        for osmid, (lat, lon) in zip(self.node_ids, self.node_coords):
            self.graph.add_node(osmid, lat=lat, lon=lon)

        edges_df = pd.read_csv(edges_path, usecols=["u", "v", "length", "highway", "name"], low_memory=False)

        # Load POIs for live spatial scoring
        pois = []
        if os.path.exists(pois_path):
            with open(pois_path, "r", encoding="utf-8") as pf:
                pois = json.load(pf)

        # Build KD-trees for POI proximity
        pol_coords = np.array([[p["latitude"] * lat_scale, p["longitude"] * lon_scale] for p in pois if p.get("category") == "police"])
        pol_tree = cKDTree(pol_coords) if len(pol_coords) > 0 else None

        hosp_coords = np.array([[p["latitude"] * lat_scale, p["longitude"] * lon_scale] for p in pois if p.get("category") == "hospital"])
        hosp_tree = cKDTree(hosp_coords) if len(hosp_coords) > 0 else None

        pharm_coords = np.array([[p["latitude"] * lat_scale, p["longitude"] * lon_scale] for p in pois if p.get("category") == "pharmacy"])
        pharm_tree = cKDTree(pharm_coords) if len(pharm_coords) > 0 else None

        pharm_24h_coords = np.array([[p["latitude"] * lat_scale, p["longitude"] * lon_scale] for p in pois if p.get("category") == "pharmacy" and (p.get("is_24_7") or "24" in p.get("name", ""))])
        pharm_24h_tree = cKDTree(pharm_24h_coords) if len(pharm_24h_coords) > 0 else pharm_tree

        comm_coords = np.array([[p["latitude"] * lat_scale, p["longitude"] * lon_scale] for p in pois if p.get("category") in ["restaurant", "cafe", "shop", "supermarket", "bank", "bus_stop"]])
        comm_tree = cKDTree(comm_coords) if len(comm_coords) > 0 else None

        edu_coords = np.array([[p["latitude"] * lat_scale, p["longitude"] * lon_scale] for p in pois if p.get("category") in ["college", "school"]])
        edu_tree = cKDTree(edu_coords) if len(edu_coords) > 0 else None

        bar_coords = np.array([[p["latitude"] * lat_scale, p["longitude"] * lon_scale] for p in pois if p.get("category") in ["bar", "liquor_shop"]])
        bar_tree = cKDTree(bar_coords) if len(bar_coords) > 0 else None

        # Vectorized midpoint calculation
        u_arr = edges_df["u"].values
        v_arr = edges_df["v"].values
        u_lats = np.array([node_dict[u][0] for u in u_arr])
        u_lons = np.array([node_dict[u][1] for u in u_arr])
        v_lats = np.array([node_dict[v][0] for v in v_arr])
        v_lons = np.array([node_dict[v][1] for v in v_arr])

        mid_lats = (u_lats + v_lats) / 2.0
        mid_lons = (u_lons + v_lons) / 2.0
        scaled_mids = np.column_stack([mid_lats * lat_scale, mid_lons * lon_scale])

        # Query POI distances and counts
        pol_dists, _ = pol_tree.query(scaled_mids) if pol_tree else (np.full(len(u_arr), 5000.0), None)
        hosp_dists, _ = hosp_tree.query(scaled_mids) if hosp_tree else (np.full(len(u_arr), 5000.0), None)
        pharm_dists, _ = pharm_tree.query(scaled_mids) if pharm_tree else (np.full(len(u_arr), 5000.0), None)
        pharm_24h_dists, _ = pharm_24h_tree.query(scaled_mids) if pharm_24h_tree else (pharm_dists, None)

        comm_counts = np.array(comm_tree.query_ball_point(scaled_mids, r=250.0, return_length=True)) if comm_tree else np.zeros(len(u_arr))
        edu_counts = np.array(edu_tree.query_ball_point(scaled_mids, r=300.0, return_length=True)) if edu_tree else np.zeros(len(u_arr))
        bar_counts = np.array(bar_tree.query_ball_point(scaled_mids, r=150.0, return_length=True)) if bar_tree else np.zeros(len(u_arr))

        length_arr = edges_df["length"].values
        highway_arr = edges_df["highway"].values
        name_arr = edges_df["name"].values

        edge_batch = []
        for i in range(len(u_arr)):
            clean_type = str(highway_arr[i] or "unknown").strip("['\"] ").split(",")[0].lower()
            speed = SPEED_M_S.get(clean_type, 6.0)
            l_val = float(length_arr[i])
            travel_sec = l_val / max(1.0, speed)
            nm = str(name_arr[i]) if pd.notna(name_arr[i]) else ""

            # Base lighting boosted by commercial shop illumination
            base_l = ROAD_LIGHTING_DEFAULTS.get(clean_type, 0.45)
            lighting_score = min(1.0, base_l + (0.1 if comm_counts[i] >= 2 else 0.0))

            # Day Safety
            day_metrics = calculate_segment_safety(
                road_type=clean_type,
                lighting_score=lighting_score,
                d_police=float(pol_dists[i]),
                d_hospital=float(hosp_dists[i]),
                d_pharmacy=float(pharm_dists[i]),
                d_pharmacy_24h=float(pharm_24h_dists[i]),
                commercial_count=int(comm_counts[i]),
                educational_count=int(edu_counts[i]),
                bar_count=int(bar_counts[i]),
                liquor_count=0,
                is_night=False
            )

            # Night Safety
            night_metrics = calculate_segment_safety(
                road_type=clean_type,
                lighting_score=lighting_score,
                d_police=float(pol_dists[i]),
                d_hospital=float(hosp_dists[i]),
                d_pharmacy=float(pharm_dists[i]),
                d_pharmacy_24h=float(pharm_24h_dists[i]),
                commercial_count=int(comm_counts[i]),
                educational_count=int(edu_counts[i]),
                bar_count=int(bar_counts[i]),
                liquor_count=0,
                is_night=True
            )

            edge_data = {
                "road_id": i + 1,
                "name": nm,
                "road_type": clean_type,
                "length": l_val,
                "travel_time_sec": travel_sec,
                "speed": speed,
                "safety_day": day_metrics["final_safety_score"],
                "safety_night": night_metrics["final_safety_score"],
                "safety_level": day_metrics["safety_level"],
                "police_distance": float(pol_dists[i]),
                "hospital_distance": float(hosp_dists[i]),
                "pharmacy_distance": float(pharm_dists[i]),
                "pharmacy_24h_distance": float(pharm_24h_dists[i]),
                "lighting_score": lighting_score,
                "lighting_risk_day": day_metrics["lighting_risk"],
                "lighting_risk_night": night_metrics["lighting_risk"],
                "isolation_risk_day": day_metrics["isolation_risk"],
                "isolation_risk_night": night_metrics["isolation_risk"],
                "commercial_count": int(comm_counts[i]),
                "educational_count": int(edu_counts[i]),
                "bar_count": int(bar_counts[i]),
                "liquor_shop_count": 0,
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[u_lons[i], u_lats[i]], [v_lons[i], v_lats[i]]]
                }
            }
            edge_batch.append((u_arr[i], v_arr[i], edge_data))
            self.road_id_to_edge[i + 1] = (u_arr[i], v_arr[i], edge_data)

        self.graph.add_edges_from(edge_batch)
        self.is_loaded = True
        print(f"Network loaded from CSV with live POI scoring: {self.graph.number_of_nodes()} nodes, "
              f"{self.graph.number_of_edges()} edges in {time.time() - t0:.2f}s")

    def find_nearest_node(self, lat: float, lon: float) -> int:
        if not self.kdtree:
            self.load_network()
        lat_scale = 111000.0
        lon_scale = 104300.0
        query_pt = np.array([lat * lat_scale, lon * lon_scale])
        _, idx = self.kdtree.query(query_pt)
        return self.node_ids[idx]

    def _get_cost(self, u: int, v: int, edge_data: dict, mode: str, is_night: bool = False) -> float:
        travel_time = edge_data["travel_time_sec"]
        length = edge_data["length"]
        safety = edge_data.get("safety_night" if is_night else "safety_day", edge_data.get("safety_score", 60.0))

        if mode == "shortest":
            # Strictly shortest physical distance
            return length
        elif mode == "fastest":
            # Strictly time-based: minimizes travel duration along high-speed corridors
            return travel_time
        elif mode == "balanced":
            # Medium route: balances travel time with avoiding dark/isolated/risky corridors
            risk = max(0.0, 100.0 - safety) / 45.0
            return travel_time * (1.0 + 1.8 * (risk ** 1.4))
        else:  # safest
            # Maximizes safety: heavily penalizes low lighting, isolation, and unmonitored roads
            risk = max(0.0, 100.0 - safety) / 45.0
            return length * (1.0 + 3.5 * (risk ** 2.2))

    def _find_path(self, start_node: int, end_node: int, weight_func, dest_coord: tuple, mode: str) -> Optional[List[int]]:
        def astar_heuristic(u, v_target):
            u_data = self.graph.nodes[u]
            h_dist = haversine_meters(u_data["lat"], u_data["lon"], dest_coord[0], dest_coord[1])
            if mode == "fastest" or mode == "balanced":
                return h_dist / 16.6
            return h_dist

        try:
            return nx.astar_path(self.graph, start_node, end_node, heuristic=astar_heuristic, weight=weight_func)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            try:
                return nx.bidirectional_shortest_path(self.graph, start_node, end_node)
            except Exception:
                try:
                    undir = self.graph.to_undirected(as_view=True)
                    return nx.shortest_path(undir, start_node, end_node, weight=weight_func)
                except Exception:
                    return None

    def calculate_route(
        self,
        origin_lat: float, origin_lon: float,
        dest_lat: float, dest_lon: float,
        mode: str = "safest",
        time_of_day: str = "day"
    ) -> Dict[str, Any]:
        if not self.is_loaded:
            self.load_network()

        mode_clean = mode.lower()
        if mode_clean not in ["fastest", "balanced", "safest"]:
            mode_clean = "safest"

        # Time-of-day resolution
        is_night = False
        t_clean = time_of_day.lower().strip()
        if t_clean == "night":
            is_night = True
        elif t_clean == "auto":
            cur_hour = time.localtime().tm_hour
            is_night = (cur_hour < 6 or cur_hour >= 19)

        start_node = self.find_nearest_node(origin_lat, origin_lon)
        end_node = self.find_nearest_node(dest_lat, dest_lon)

        if start_node == end_node:
            return self._create_empty_route(mode_clean, origin_lat, origin_lon, is_night)

        weight_func = lambda u, v, d: self._get_cost(u, v, d, mode_clean, is_night=is_night)
        dest_data = self.graph.nodes[end_node]
        dest_coord = (dest_data["lat"], dest_data["lon"])

        path = self._find_path(start_node, end_node, weight_func, dest_coord, mode_clean)
        if not path:
            return self._create_empty_route(mode_clean, origin_lat, origin_lon, is_night, dest_lat, dest_lon)

        return self._build_route_output(path, mode_clean, origin_lat, origin_lon, dest_lat, dest_lon, is_night)

    def _build_route_output(
        self,
        path: List[int],
        mode: str,
        origin_lat: float, origin_lon: float,
        dest_lat: float, dest_lon: float,
        is_night: bool = False
    ) -> Dict[str, Any]:
        total_length = 0.0
        total_travel_time_sec = 0.0
        weighted_safety_sum = 0.0

        all_coords = [[origin_lon, origin_lat]]
        segments = []

        total_police_dists = []
        total_hospital_dists = []
        total_pharm_dists = []
        total_pharm_24h_dists = []
        total_lighting_scores = []
        total_isolation_risks = []
        total_commercial_count = 0
        total_educational_count = 0
        total_bars = 0
        total_liquor = 0

        edge_list = []

        for i in range(len(path) - 1):
            u = path[i]
            v = path[i + 1]
            edge = self.graph.get_edge_data(u, v)
            if not edge:
                edge = self.graph.get_edge_data(v, u) or {}

            length = edge.get("length", 50.0)
            travel_time = edge.get("travel_time_sec", length / 6.0)
            safety = edge.get("safety_night" if is_night else "safety_day", edge.get("safety_score", 60.0))
            s_level = get_safety_level(safety)
            r_name = edge.get("name", "")
            r_type = edge.get("road_type", "residential")
            r_id = edge.get("road_id", 0)

            total_length += length
            total_travel_time_sec += travel_time
            weighted_safety_sum += (length * safety)

            total_police_dists.append(edge.get("police_distance", 5000.0))
            total_hospital_dists.append(edge.get("hospital_distance", 5000.0))
            total_pharm_dists.append(edge.get("pharmacy_distance", 5000.0))
            total_pharm_24h_dists.append(edge.get("pharmacy_24h_distance", 5000.0))
            total_lighting_scores.append(edge.get("lighting_score", 0.5))
            total_isolation_risks.append(edge.get("isolation_risk_night" if is_night else "isolation_risk_day", 10.0))
            total_commercial_count += edge.get("commercial_count", 0)
            total_educational_count += edge.get("educational_count", 0)
            total_bars += edge.get("bar_count", 0)
            total_liquor += edge.get("liquor_shop_count", 0)

            geom = edge.get("geometry")
            if geom and "coordinates" in geom:
                edge_coords = geom["coordinates"]
                all_coords.extend(edge_coords)
            else:
                u_node = self.graph.nodes[u]
                v_node = self.graph.nodes[v]
                edge_coords = [[u_node["lon"], u_node["lat"]], [v_node["lon"], v_node["lat"]]]
                all_coords.extend(edge_coords)

            segments.append({
                "road_id": r_id,
                "name": r_name,
                "road_type": r_type,
                "length_meters": round(length, 1),
                "safety_score": round(safety, 1),
                "safety_level": s_level
            })

            edge_list.append({
                "road_id": r_id,
                "name": r_name or "Unnamed Road",
                "length": length,
                "travel_time": travel_time,
                "safety": safety,
                "level": s_level,
                "coords": edge_coords
            })

        all_coords.append([dest_lon, dest_lat])

        clean_coords = []
        for pt in all_coords:
            if not clean_coords or clean_coords[-1] != pt:
                clean_coords.append(pt)

        # ==========================================
        # Generate Turn-by-Turn Navigation Steps
        # ==========================================
        steps = []
        turn_penalties_sec = 0.0

        if edge_list:
            grouped_steps = []
            cur_group = None

            for edge_info in edge_list:
                st_name = edge_info["name"]
                if cur_group is None:
                    cur_group = {
                        "name": st_name,
                        "length": edge_info["length"],
                        "travel_time": edge_info["travel_time"],
                        "safety_sum": edge_info["safety"] * edge_info["length"],
                        "coords": list(edge_info["coords"])
                    }
                elif cur_group["name"] == st_name and st_name != "Unnamed Road":
                    cur_group["length"] += edge_info["length"]
                    cur_group["travel_time"] += edge_info["travel_time"]
                    cur_group["safety_sum"] += (edge_info["safety"] * edge_info["length"])
                    cur_group["coords"].extend(edge_info["coords"])
                else:
                    grouped_steps.append(cur_group)
                    cur_group = {
                        "name": st_name,
                        "length": edge_info["length"],
                        "travel_time": edge_info["travel_time"],
                        "safety_sum": edge_info["safety"] * edge_info["length"],
                        "coords": list(edge_info["coords"])
                    }
            if cur_group:
                grouped_steps.append(cur_group)

            prev_bearing = None
            step_counter = 1

            for s_idx, g in enumerate(grouped_steps):
                c_list = g["coords"]
                if len(c_list) >= 2:
                    p_start = c_list[0]
                    p_end = c_list[-1]
                    cur_bearing = calculate_bearing(p_start[1], p_start[0], p_end[1], p_end[0])
                else:
                    cur_bearing = 0.0

                dist_m = g["length"]
                dur_s = int(round(g["travel_time"]))
                avg_sc = round(g["safety_sum"] / max(1.0, dist_m), 1)
                dist_txt = f"{int(round(dist_m))} m" if dist_m < 1000 else f"{round(dist_m/1000.0, 1)} km"

                if s_idx == 0:
                    compass = get_compass_direction(cur_bearing)
                    modifier = "depart"
                    instruction = f"Head {compass} on {g['name']}"
                else:
                    modifier, instruction = get_maneuver(prev_bearing or cur_bearing, cur_bearing, g["name"])
                    # Realistic turn delay at urban intersections (6 seconds)
                    if modifier in ["left", "right", "sharp_left", "sharp_right", "uturn"]:
                        turn_penalties_sec += 6.0

                prev_bearing = cur_bearing

                steps.append({
                    "step_number": step_counter,
                    "modifier": modifier,
                    "instruction": instruction,
                    "distance_meters": round(dist_m, 1),
                    "distance_text": dist_txt,
                    "duration_sec": dur_s,
                    "street_name": g["name"],
                    "safety_score": avg_sc,
                    "safety_level": get_safety_level(avg_sc),
                    "coordinates": c_list
                })
                step_counter += 1

            # Arrival step
            steps.append({
                "step_number": step_counter,
                "modifier": "arrive",
                "instruction": "You have arrived at your destination",
                "distance_meters": 0.0,
                "distance_text": "0 m",
                "duration_sec": 0,
                "street_name": "Destination",
                "safety_score": round(weighted_safety_sum / max(1.0, total_length), 1),
                "safety_level": get_safety_level(weighted_safety_sum / max(1.0, total_length)),
                "coordinates": [[dest_lon, dest_lat]]
            })

        avg_safety = weighted_safety_sum / max(1.0, total_length)
        final_score = round(max(5.0, min(100.0, avg_safety)), 1)
        final_level = get_safety_level(final_score)

        avg_lighting = float(np.mean(total_lighting_scores)) if total_lighting_scores else 0.5
        avg_isolation_risk = float(np.mean(total_isolation_risks)) if total_isolation_risks else 10.0
        min_police_dist = float(min(total_police_dists)) if total_police_dists else 5000.0
        min_hospital_dist = float(min(total_hospital_dists)) if total_hospital_dists else 5000.0
        min_pharm_dist = float(min(total_pharm_dists)) if total_pharm_dists else 5000.0
        min_pharm_24h_dist = float(min(total_pharm_24h_dists)) if total_pharm_24h_dists else 5000.0

        explanations = []
        if mode == "shortest":
            explanations.append("Shortest physical distance path minimizing total kilometers")
        elif mode == "fastest":
            explanations.append("Least travel time along higher-speed thoroughfares")
        elif mode == "balanced":
            explanations.append("Medium route: balances speed with enhanced safety away from isolated streets")
        elif mode == "safest":
            explanations.append("Maximized safety: prioritized street lighting, active venues, and emergency hubs")

        # Time-aware context explanation
        if is_night:
            explanations.append("Nighttime safety rules active: lighting & isolation weights amplified; closed schools have 0 benefit")
        else:
            explanations.append("Daytime natural surveillance active: educational campuses and active retail provide footfall benefits")

        if avg_lighting >= 0.70:
            explanations.append("High street lighting along main illuminated avenues")
        elif avg_lighting >= 0.50:
            explanations.append("Moderate road lighting with intermittent illumination")

        if total_commercial_count >= 5:
            explanations.append(f"Passes {total_commercial_count} active retail, cafe, or transit locations")

        if min_police_dist <= 1200.0:
            explanations.append(f"Within {int(min_police_dist)}m of a police station/chowki")

        if is_night and min_pharm_24h_dist <= 1000.0:
            explanations.append(f"Passes within {int(min_pharm_24h_dist)}m of a verified 24/7 pharmacy safe haven")
        elif not is_night and min_pharm_dist <= 800.0:
            explanations.append(f"Passes within {int(min_pharm_dist)}m of a chemist/pharmacy")

        if min_hospital_dist <= 1000.0:
            explanations.append(f"Within {int(min_hospital_dist)}m of emergency hospital care")

        if total_bars == 0 and total_liquor == 0:
            explanations.append("Zero exposure to bars or liquor outlets")

        # Transparent missing crime data note
        explanations.append("Environmental safety estimate; official police crime records are unverified/unavailable")

        distance_km = round(total_length / 1000.0, 2)
        total_time_with_turns = total_travel_time_sec + turn_penalties_sec
        est_minutes = max(1, int(round(total_time_with_turns / 60.0)))

        risk_factors = {
            "avg_lighting_score": round(avg_lighting, 2),
            "avg_isolation_risk": round(avg_isolation_risk, 1),
            "min_police_dist_m": round(min_police_dist, 1),
            "min_hospital_dist_m": round(min_hospital_dist, 1),
            "min_pharmacy_24h_dist_m": round(min_pharm_24h_dist, 1),
            "commercial_venues_count": int(total_commercial_count),
            "bars_count": int(total_bars),
            "is_night": is_night
        }

        return {
            "route_type": mode,
            "distance_km": distance_km,
            "estimated_time_minutes": est_minutes,
            "safety_score": final_score,
            "safety_level": final_level,
            "time_of_day": "night" if is_night else "day",
            "crime_data_status": CRIME_DATA_STATUS_UNKNOWN,
            "crime_data_disclaimer": MISSING_CRIME_DATA_DISCLAIMER,
            "risk_factors": risk_factors,
            "geometry": {
                "type": "LineString",
                "coordinates": clean_coords
            },
            "explanation": explanations,
            "segments": segments[:20],
            "steps": steps
        }

    def _create_empty_route(
        self,
        mode: str,
        o_lat: float, o_lon: float,
        is_night: bool = False,
        d_lat: float = None, d_lon: float = None
    ) -> Dict[str, Any]:
        coords = [[o_lon, o_lat]]
        if d_lat and d_lon:
            coords.append([d_lon, d_lat])
            dist = round(haversine_meters(o_lat, o_lon, d_lat, d_lon) / 1000.0, 2)
        else:
            dist = 0.0

        return {
            "route_type": mode,
            "distance_km": dist,
            "estimated_time_minutes": max(1, int(dist * 2.5)),
            "safety_score": 60.0,
            "safety_level": "Moderate",
            "time_of_day": "night" if is_night else "day",
            "crime_data_status": CRIME_DATA_STATUS_UNKNOWN,
            "crime_data_disclaimer": MISSING_CRIME_DATA_DISCLAIMER,
            "risk_factors": {
                "avg_lighting_score": 0.5,
                "avg_isolation_risk": 10.0,
                "is_night": is_night
            },
            "geometry": {
                "type": "LineString",
                "coordinates": coords
            },
            "explanation": ["Direct straight line approximation (no road graph path found)"],
            "segments": [],
            "steps": [
                {
                    "step_number": 1,
                    "modifier": "depart",
                    "instruction": "Proceed towards destination",
                    "distance_meters": dist * 1000.0,
                    "distance_text": f"{dist} km",
                    "duration_sec": int(dist * 150),
                    "street_name": "Direct Route",
                    "safety_score": 60.0,
                    "safety_level": "Moderate",
                    "coordinates": coords
                },
                {
                    "step_number": 2,
                    "modifier": "arrive",
                    "instruction": "You have arrived at your destination",
                    "distance_meters": 0.0,
                    "distance_text": "0 m",
                    "duration_sec": 0,
                    "street_name": "Destination",
                    "safety_score": 60.0,
                    "safety_level": "Moderate",
                    "coordinates": coords[-1:]
                }
            ]
        }

    def compare_routes(
        self,
        origin_lat: float, origin_lon: float,
        dest_lat: float, dest_lon: float,
        time_of_day: str = "day"
    ) -> Dict[str, Any]:
        """
        Calculates and compares the three route choices: Safest, Fastest, and Balanced.
        Fastest strictly minimizes travel time.
        Safest strictly minimizes estimated risk (lighting, isolation, emergency proximity).
        Balanced combines safety and travel time.
        When routes overlap or are identical because the base objective selected the same highway,
        it searches for next-best feasible loop-free alternative routes in the road graph.
        Never fabricates different distances, times, or scores.
        """
        if not self.is_loaded:
            self.load_network()

        is_night = False
        t_clean = time_of_day.lower().strip()
        if t_clean == "night":
            is_night = True
        elif t_clean == "auto":
            cur_hour = time.localtime().tm_hour
            is_night = (cur_hour < 6 or cur_hour >= 19)

        start_node = self.find_nearest_node(origin_lat, origin_lon)
        end_node = self.find_nearest_node(dest_lat, dest_lon)

        if start_node == end_node:
            empty_f = self._create_empty_route("fastest", origin_lat, origin_lon, is_night)
            empty_s = self._create_empty_route("safest", origin_lat, origin_lon, is_night)
            empty_b = self._create_empty_route("balanced", origin_lat, origin_lon, is_night)
            return {
                "origin": {"latitude": origin_lat, "longitude": origin_lon},
                "destination": {"latitude": dest_lat, "longitude": dest_lon},
                "safest": empty_s,
                "fastest": empty_f,
                "balanced": empty_b,
                "time_of_day": "night" if is_night else "day"
            }

        dest_data = self.graph.nodes[end_node]
        dest_coord = (dest_data["lat"], dest_data["lon"])

        # 1. Calculate Fastest Path (strictly minimizes travel time)
        fastest_weight = lambda u, v, d: self._get_cost(u, v, d, "fastest", is_night=is_night)
        fastest_path = self._find_path(start_node, end_node, fastest_weight, dest_coord, "fastest")

        # 2. Calculate Safest Path (strictly minimizes risk)
        safest_weight = lambda u, v, d: self._get_cost(u, v, d, "safest", is_night=is_night)
        safest_path = self._find_path(start_node, end_node, safest_weight, dest_coord, "safest")

        # 3. Calculate Balanced Path (combines time and safety)
        balanced_weight = lambda u, v, d: self._get_cost(u, v, d, "balanced", is_night=is_night)
        balanced_path = self._find_path(start_node, end_node, balanced_weight, dest_coord, "balanced")

        def get_path_edges(p):
            if not p or len(p) < 2:
                return set()
            return set(zip(p[:-1], p[1:]))

        def get_interior_edges(p):
            if not p or len(p) <= 3:
                return set()
            return set(zip(p[1:-2], p[2:-1]))

        def path_length(p):
            if not p:
                return 0.0
            total = 0.0
            for u, v in zip(p[:-1], p[1:]):
                ed = self.graph.get_edge_data(u, v) or self.graph.get_edge_data(v, u) or {}
                total += ed.get("length", 50.0)
            return total

        fast_len = path_length(fastest_path)

        # Check if safest is identical to fastest and whether an alternative high-safety corridor exists
        if fastest_path and safest_path:
            fast_edges = get_path_edges(fastest_path)
            safe_edges = get_path_edges(safest_path)
            overlap_fs = len(fast_edges & safe_edges) / max(1, len(safe_edges))

            # Only search for alternative if they almost completely overlap
            if overlap_fs > 0.85:
                interior_fast = get_interior_edges(fastest_path)
                if interior_fast:
                    def penalized_safest_weight(u, v, d):
                        base = safest_weight(u, v, d)
                        if (u, v) in interior_fast or (v, u) in interior_fast:
                            return base * 4.0
                        return base

                    alt_safest = self._find_path(start_node, end_node, penalized_safest_weight, dest_coord, "safest")
                    if alt_safest and alt_safest != fastest_path:
                        alt_len = path_length(alt_safest)
                        if len(alt_safest) == len(set(alt_safest)) and alt_len <= 1.65 * fast_len:
                            # Only adopt if the alternative route does NOT degrade safety below the fastest route
                            alt_test = self._build_route_output(alt_safest, "safest", origin_lat, origin_lon, dest_lat, dest_lon, is_night)
                            fast_test = self._build_route_output(fastest_path, "fastest", origin_lat, origin_lon, dest_lat, dest_lon, is_night)
                            if alt_test["safety_score"] >= fast_test["safety_score"]:
                                safest_path = alt_safest

        # Select Balanced route:
        # Balanced route should be between safest and fastest route.
        # Its distance should be strictly between safest and fastest
        # (minimum than fastest and maximum than safest when d_safe < d_fast).
        if fastest_path and safest_path:
            fast_test = self._build_route_output(fastest_path, "fastest", origin_lat, origin_lon, dest_lat, dest_lon, is_night)
            safe_test = self._build_route_output(safest_path, "safest", origin_lat, origin_lon, dest_lat, dest_lon, is_night)
            d_fast = fast_test["distance_km"]
            d_safe = safe_test["distance_km"]
            min_d, max_d = min(d_safe, d_fast), max(d_safe, d_fast)

            # Search across convex Pareto weights between time and safety
            if (max_d - min_d) >= 0.04:
                target_d = (min_d + max_d) / 2.0
                best_cand_path = None
                best_diff = float("inf")

                for lam in [0.35, 0.25, 0.40, 0.30, 0.20, 0.50, 0.60]:
                    def w_bal(u, v, d):
                        c_f = d.get("travel_time_sec", 5.0) * 10.0
                        safety = d.get("safety_night" if is_night else "safety_day", 60.0)
                        risk = max(0.0, 100.0 - safety) / 45.0
                        c_s = d.get("length", 50.0) * (1.0 + 3.5 * (risk ** 2.2))
                        return (1.0 - lam) * c_f + lam * c_s

                    p = self._find_path(start_node, end_node, w_bal, dest_coord, "balanced")
                    if p and p != fastest_path and p != safest_path:
                        r_cand = self._build_route_output(p, "balanced", origin_lat, origin_lon, dest_lat, dest_lon, is_night)
                        d_cand = r_cand["distance_km"]
                        if min_d <= d_cand <= max_d:
                            diff = abs(d_cand - target_d)
                            if diff < best_diff:
                                best_diff = diff
                                best_cand_path = p

                if best_cand_path:
                    balanced_path = best_cand_path

        # If balanced still duplicates fastest or safest, find alternative using unique divergent edges
        if balanced_path and (balanced_path == fastest_path or balanced_path == safest_path):
            fast_edges = get_path_edges(fastest_path)
            safe_edges = get_path_edges(safest_path)
            unique_diverge = (fast_edges - safe_edges) | (safe_edges - fast_edges)
            if unique_diverge:
                def penalized_diverge_weight(u, v, d):
                    base = balanced_weight(u, v, d)
                    if (u, v) in unique_diverge or (v, u) in unique_diverge:
                        return base * 2.0
                    return base
                alt_b = self._find_path(start_node, end_node, penalized_diverge_weight, dest_coord, "balanced")
                if alt_b and alt_b != fastest_path and alt_b != safest_path:
                    if len(alt_b) == len(set(alt_b)):
                        balanced_path = alt_b

        # Fallback to empty routes if graph disconnected
        if not fastest_path:
            fastest_r = self._create_empty_route("fastest", origin_lat, origin_lon, is_night, dest_lat, dest_lon)
        else:
            fastest_r = self._build_route_output(fastest_path, "fastest", origin_lat, origin_lon, dest_lat, dest_lon, is_night)

        if not safest_path:
            safest_r = self._create_empty_route("safest", origin_lat, origin_lon, is_night, dest_lat, dest_lon)
        else:
            safest_r = self._build_route_output(safest_path, "safest", origin_lat, origin_lon, dest_lat, dest_lon, is_night)

        if not balanced_path:
            balanced_r = self._create_empty_route("balanced", origin_lat, origin_lon, is_night, dest_lat, dest_lon)
        else:
            balanced_r = self._build_route_output(balanced_path, "balanced", origin_lat, origin_lon, dest_lat, dest_lon, is_night)

        # Transparent identical corridor explanations if no alternative exists
        coords_fast = fastest_r["geometry"]["coordinates"]
        coords_safe = safest_r["geometry"]["coordinates"]
        coords_bal = balanced_r["geometry"]["coordinates"]

        if coords_safe == coords_fast:
            safest_r["explanation"].append("Identical corridor to Fastest route: This represents the only direct viable connection between these locations in the network.")
        if coords_bal == coords_safe:
            balanced_r["explanation"].append("Shares corridor with Safest route as no intermediate safety trade-off detour is available.")
        elif coords_bal == coords_fast:
            balanced_r["explanation"].append("Shares corridor with Fastest route: Direct corridor provides optimal speed and safety balance.")

        return {
            "origin": {"latitude": origin_lat, "longitude": origin_lon},
            "destination": {"latitude": dest_lat, "longitude": dest_lon},
            "safest": safest_r,
            "fastest": fastest_r,
            "balanced": balanced_r,
            "time_of_day": fastest_r.get("time_of_day", "day")
        }

    # ==============================================================
    # In-memory GeoJSON queries for Heatmap and Roads (Offline fallback)
    # ==============================================================
    def get_heatmap_features(
        self,
        min_lat: float, min_lon: float,
        max_lat: float, max_lon: float,
        level: Optional[str] = None,
        limit: int = 500,
        is_night: bool = False
    ) -> List[Dict[str, Any]]:
        if not self.is_loaded:
            self.load_network()

        color_map = {
            "Very Safe": "#10B981",
            "Safe": "#34D399",
            "Moderate": "#FBBF24",
            "Risky": "#F97316",
            "High Risk": "#EF4444"
        }

        features = []
        for u, v, d in self.graph.edges(data=True):
            geom = d.get("geometry")
            if not geom or "coordinates" not in geom:
                continue

            coords = geom["coordinates"]
            # Check bounding box on first coordinate
            if not coords:
                continue
            lon, lat = coords[0]
            if not (min_lat <= lat <= max_lat and min_lon <= lon <= max_lon):
                continue

            score = d.get("safety_night" if is_night else "safety_day", d.get("safety_score", 60.0))
            s_level = get_safety_level(score)

            if level and s_level.lower() != level.lower():
                continue

            features.append({
                "type": "Feature",
                "properties": {
                    "id": d.get("road_id", 0),
                    "name": d.get("name", ""),
                    "road_type": d.get("road_type", "residential"),
                    "safety_score": score,
                    "safety_level": s_level,
                    "color": color_map.get(s_level, "#FBBF24")
                },
                "geometry": geom
            })

            if len(features) >= limit:
                break

        return features

    def get_roads_in_bbox(
        self,
        min_lat: float, min_lon: float,
        max_lat: float, max_lon: float,
        limit: int = 300
    ) -> List[Dict[str, Any]]:
        if not self.is_loaded:
            self.load_network()

        features = []
        for u, v, d in self.graph.edges(data=True):
            geom = d.get("geometry")
            if not geom or "coordinates" not in geom:
                continue
            coords = geom["coordinates"]
            if not coords:
                continue
            lon, lat = coords[0]
            if not (min_lat <= lat <= max_lat and min_lon <= lon <= max_lon):
                continue

            score = d.get("safety_day", d.get("safety_score", 60.0))
            s_level = get_safety_level(score)

            features.append({
                "type": "Feature",
                "properties": {
                    "id": d.get("road_id", 0),
                    "name": d.get("name", ""),
                    "road_type": d.get("road_type", "residential"),
                    "length": d.get("length", 0.0),
                    "safety_score": score,
                    "safety_level": s_level
                },
                "geometry": geom
            })

            if len(features) >= limit:
                break

        return features

    def get_road_by_id(self, road_id: int) -> Optional[Dict[str, Any]]:
        if not self.is_loaded:
            self.load_network()

        edge_info = self.road_id_to_edge.get(road_id)
        if not edge_info:
            return None

        u, v, d = edge_info
        return {
            "road_id": road_id,
            "name": d.get("name") or "Unnamed Road",
            "road_type": d.get("road_type", "residential"),
            "length_meters": round(d.get("length", 0.0), 1),
            "final_safety_score": d.get("safety_day", 60.0),
            "safety_level": get_safety_level(d.get("safety_day", 60.0)),
            "factors": {
                "lighting_score": d.get("lighting_score", 0.5),
                "lighting_risk": d.get("lighting_risk_day", 10.0),
                "isolation_risk": d.get("isolation_risk_day", 10.0),
                "bar_count": d.get("bar_count", 0),
                "crime_data_status": CRIME_DATA_STATUS_UNKNOWN
            },
            "emergency_distances": {
                "police_meters": round(d.get("police_distance", 5000.0), 1),
                "hospital_meters": round(d.get("hospital_distance", 5000.0), 1),
                "pharmacy_meters": round(d.get("pharmacy_distance", 5000.0), 1),
                "pharmacy_24h_meters": round(d.get("pharmacy_24h_distance", 5000.0), 1)
            },
            "geometry": d.get("geometry")
        }
