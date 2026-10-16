import os
import json
import math
import time
import networkx as nx
import numpy as np
from scipy.spatial import cKDTree
from typing import Dict, List, Any, Optional, Tuple

from backend.app.database import SessionLocal
from backend.app.safety.config import ROUTE_MODES, get_safety_level

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

# Road speed values in meters per second (m/s) based on standard OpenStreetMap road hierarchy.
# Used for deterministic travel-time calculation: travel_time_sec = length_meters / speed_m_s.
# In the absence of live traffic sensor data, travel times are derived strictly from these
# documented speed values and actual road segment geometries.
SPEED_M_S = {
    "motorway": 16.6,        # ~60 km/h (divided high-speed expressway/bypass)
    "trunk": 15.0,           # ~54 km/h (major arterial road)
    "primary": 12.5,         # ~45 km/h (city primary arterial road)
    "primary_link": 10.0,    # ~36 km/h (arterial slip road/connector)
    "secondary": 10.0,       # ~36 km/h (city secondary connector road)
    "secondary_link": 8.5,   # ~30 km/h (secondary slip road)
    "tertiary": 8.3,         # ~30 km/h (standard urban collector street)
    "tertiary_link": 7.0,    # ~25 km/h (collector slip road)
    "residential": 6.9,      # ~25 km/h (local residential neighborhood street)
    "living_street": 5.5,    # ~20 km/h (pedestrian-priority shared street)
    "service": 4.5,          # ~16 km/h (access lane, alley, or driveway)
    "unclassified": 6.0,     # ~22 km/h (minor unclassified road)
    "footway": 1.4,          # ~5 km/h (pedestrian walkway/footpath)
    "pedestrian": 1.4,       # ~5 km/h (pedestrian zone)
    "path": 1.4,             # ~5 km/h (general non-motorized path)
    "unknown": 6.0           # ~22 km/h (standard default fallback)
}

class NashikRoadNetwork:
    _instance = None

    def __init__(self):
        self.graph = nx.DiGraph()
        self.node_ids = []
        self.node_coords = []
        self.kdtree = None
        self.is_loaded = False

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def load_network(self):
        if self.is_loaded:
            return

        t0 = time.time()
        print("Loading road network and intersections from database into NetworkX graph...")
        try:
            db = SessionLocal()
            try:
                nodes_res = db.execute(
                    __import__("sqlalchemy").text("SELECT osmid, latitude, longitude FROM intersections;")
                ).fetchall()
                
                if nodes_res:
                    node_map = {}
                    for osmid, lat, lon in nodes_res:
                        self.node_ids.append(osmid)
                        self.node_coords.append((lat, lon))
                        node_map[osmid] = (lat, lon)
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
                        travel_sec = length / max(1.0, speed)

                        geom = json.loads(geom_json) if geom_json else None

                        self.graph.add_edge(
                            u, v,
                            road_id=r_id,
                            name=r_name or "",
                            road_type=clean_type,
                            length=float(length),
                            travel_time_sec=float(travel_sec),
                            safety_score=float(safety or 50.0),
                            safety_level=s_level or "Moderate",
                            police_distance=float(pol_d or 5000.0),
                            hospital_distance=float(hosp_d or 5000.0),
                            pharmacy_distance=float(pharm_d or 5000.0),
                            lighting_risk=float(l_risk or 15.0),
                            isolation_risk=float(iso_risk or 10.0),
                            bar_count=int(bar_cnt or 0),
                            liquor_shop_count=int(liq_cnt or 0),
                            commercial_density=float(comm_dens or 0.0),
                            geometry=geom
                        )

                    self.is_loaded = True
                    print(f"Network loaded from DB: {self.graph.number_of_nodes()} nodes, "
                          f"{self.graph.number_of_edges()} edges in {time.time() - t0:.2f}s")
                    return
            finally:
                db.close()
        except Exception as e:
            print(f"Database unavailable or empty ({e}). Falling back to CSV dataset...")

        self._load_from_csv(t0)

    def _load_from_csv(self, t0: float):
        import pandas as pd
        # Resolve path relative to repo root
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        nodes_path = os.path.join(repo_root, "data", "raw", "nodes.csv")
        edges_path = os.path.join(repo_root, "data", "raw", "edges.csv")

        if not (os.path.exists(nodes_path) and os.path.exists(edges_path)):
            print(f"Warning: Raw CSV datasets not found at {nodes_path} or {edges_path}.")
            return

        print(f"Loading road network from CSV fallback datasets ({nodes_path})...")
        nodes_df = pd.read_csv(nodes_path, usecols=["osmid", "y", "x"])
        self.node_ids = nodes_df["osmid"].tolist()
        self.node_coords = list(zip(nodes_df["y"], nodes_df["x"]))
        lat_scale = 111000.0
        lon_scale = 104300.0
        coords_arr = np.array(self.node_coords)
        scaled_coords = np.column_stack([coords_arr[:, 0] * lat_scale, coords_arr[:, 1] * lon_scale])
        self.kdtree = cKDTree(scaled_coords)

        for osmid, (lat, lon) in zip(self.node_ids, self.node_coords):
            self.graph.add_node(osmid, lat=lat, lon=lon)

        edges_df = pd.read_csv(edges_path, usecols=["u", "v", "length", "highway", "name"], low_memory=False)
        DEFAULT_SCORES = {
            "motorway": 85.0, "trunk": 85.0, "primary": 80.0, "primary_link": 78.0,
            "secondary": 75.0, "secondary_link": 72.0, "tertiary": 70.0, "tertiary_link": 68.0,
            "residential": 62.0, "living_street": 60.0, "unclassified": 58.0,
            "service": 50.0, "footway": 52.0, "pedestrian": 55.0, "path": 45.0, "unknown": 55.0
        }

        u_arr = edges_df["u"].values
        v_arr = edges_df["v"].values
        length_arr = edges_df["length"].values
        highway_arr = edges_df["highway"].values
        name_arr = edges_df["name"].values

        edge_batch = []
        for i in range(len(u_arr)):
            clean_type = str(highway_arr[i] or "unknown").strip("['\"] ").split(",")[0].lower()
            speed = SPEED_M_S.get(clean_type, 6.0)
            l = float(length_arr[i])
            travel_sec = l / max(1.0, speed)
            safety = DEFAULT_SCORES.get(clean_type, 60.0)
            s_level = "Safe" if safety >= 65 else "Moderate"
            nm = str(name_arr[i]) if pd.notna(name_arr[i]) else ""
            edge_batch.append((
                u_arr[i], v_arr[i], {
                    "road_id": i + 1,
                    "name": nm,
                    "road_type": clean_type,
                    "length": l,
                    "travel_time_sec": travel_sec,
                    "safety_score": safety,
                    "safety_level": s_level,
                    "police_distance": 1500.0,
                    "hospital_distance": 1200.0,
                    "pharmacy_distance": 800.0,
                    "lighting_risk": 15.0,
                    "isolation_risk": 10.0,
                    "bar_count": 0,
                    "liquor_shop_count": 0,
                    "commercial_density": 0.0,
                    "geometry": None
                }
            ))

        self.graph.add_edges_from(edge_batch)
        self.is_loaded = True
        print(f"Network loaded from CSV: {self.graph.number_of_nodes()} nodes, "
              f"{self.graph.number_of_edges()} edges in {time.time() - t0:.2f}s")

    def find_nearest_node(self, lat: float, lon: float) -> int:
        if not self.kdtree:
            self.load_network()
        lat_scale = 111000.0
        lon_scale = 104300.0
        query_pt = np.array([lat * lat_scale, lon * lon_scale])
        _, idx = self.kdtree.query(query_pt)
        return self.node_ids[idx]

    def _get_cost(self, u: int, v: int, edge_data: dict, mode: str) -> float:
        travel_time = edge_data["travel_time_sec"]
        safety = edge_data["safety_score"]

        if mode == "fastest":
            # Strictly time-based: minimizes travel duration
            return travel_time
        elif mode == "balanced":
            # Balanced: trades off travel time and safety risk without extreme circuitous detours
            risk = max(0.0, (100.0 - safety) / 50.0)
            return travel_time * (1.0 + 0.5 * risk)
        else:  # safest
            # Maximum safety: prioritizes high-safety corridors, lighting, and emergency access
            risk = max(0.0, (100.0 - safety) / 25.0)
            return travel_time * (1.0 + 5.0 * (risk ** 2.0))

    def _generate_candidate_paths(self, start_node: int, end_node: int) -> List[List[int]]:
        """
        Generate a bounded set of valid, loop-free candidate paths connecting start_node
        and end_node on the real road network. Respects graph directionality.
        """
        dest_data = self.graph.nodes[end_node]
        dest_coord = (dest_data["lat"], dest_data["lon"])

        # Max vehicle speed on primary/motorway is 16.6 m/s
        # Admissible travel time lower bound heuristic
        def astar_heuristic(u, v_target):
            u_data = self.graph.nodes[u]
            h_dist = haversine_meters(u_data["lat"], u_data["lon"], dest_coord[0], dest_coord[1])
            return h_dist / 16.6

        raw_candidates = []

        # Candidate 1: Shortest estimated travel time
        try:
            p_fast = nx.astar_path(
                self.graph, start_node, end_node,
                heuristic=astar_heuristic,
                weight=lambda u, v, d: d.get("travel_time_sec", d.get("length", 50.0) / 6.0)
            )
            raw_candidates.append(p_fast)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            pass

        # Candidate 2: Safest objective
        try:
            p_safe = nx.astar_path(
                self.graph, start_node, end_node,
                heuristic=astar_heuristic,
                weight=lambda u, v, d: self._get_cost(u, v, d, "safest")
            )
            raw_candidates.append(p_safe)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            pass

        # Candidate 3: Balanced objective
        try:
            p_bal = nx.astar_path(
                self.graph, start_node, end_node,
                heuristic=astar_heuristic,
                weight=lambda u, v, d: self._get_cost(u, v, d, "balanced")
            )
            raw_candidates.append(p_bal)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            pass

        # Candidate 4: Alternative corridor diverting from primary fastest corridor
        if raw_candidates:
            p_fast = raw_candidates[0]
            # Exclude terminal access edges (first 2, last 2) so alternatives don't fail at cul-de-sacs/endpoints
            p_fast_mid = set(zip(p_fast[2:-2], p_fast[3:-1])) if len(p_fast) > 4 else set(zip(p_fast[:-1], p_fast[1:]))
            def pen_fast(u, v, d):
                base = d.get("travel_time_sec", d.get("length", 50.0) / 6.0)
                return base * 3.0 if (u, v) in p_fast_mid else base
            try:
                p_alt1 = nx.astar_path(self.graph, start_node, end_node, heuristic=astar_heuristic, weight=pen_fast)
                raw_candidates.append(p_alt1)
            except Exception:
                pass

        # Candidate 5: Alternative corridor diverting from primary safest corridor
        if len(raw_candidates) >= 2:
            p_safe = raw_candidates[1]
            p_safe_mid = set(zip(p_safe[2:-2], p_safe[3:-1])) if len(p_safe) > 4 else set(zip(p_safe[:-1], p_safe[1:]))
            def pen_safe(u, v, d):
                base = self._get_cost(u, v, d, "safest")
                return base * 3.0 if (u, v) in p_safe_mid else base
            try:
                p_alt2 = nx.astar_path(self.graph, start_node, end_node, heuristic=astar_heuristic, weight=pen_safe)
                raw_candidates.append(p_alt2)
            except Exception:
                pass

        # Fallback if no directed path found via A*
        if not raw_candidates:
            try:
                p_bidi = nx.bidirectional_shortest_path(self.graph, start_node, end_node)
                raw_candidates.append(p_bidi)
            except Exception:
                try:
                    undir = self.graph.to_undirected(as_view=True)
                    p_undir = nx.shortest_path(undir, start_node, end_node)
                    raw_candidates.append(p_undir)
                except Exception:
                    return []

        # Deduplicate candidates and filter out trivial deviations (>98% edge overlap)
        unique_candidates = []
        unique_edge_sets = []
        for p in raw_candidates:
            p_edges = set(zip(p[:-1], p[1:]))
            is_dup = False
            for u_edges in unique_edge_sets:
                if not p_edges or not u_edges:
                    continue
                overlap = len(p_edges.intersection(u_edges)) / min(len(p_edges), len(u_edges))
                if overlap > 0.98:  # 98% edge overlap is a trivial 1-node variation
                    is_dup = True
                    break
            if not is_dup:
                unique_candidates.append(p)
                unique_edge_sets.append(p_edges)

        return unique_candidates

    def _evaluate_candidate(self, path: List[int]) -> Dict[str, Any]:
        """
        Evaluate candidate route metrics directly and independently from constituent edges.
        """
        total_length = 0.0
        total_travel_time_sec = 0.0
        weighted_safety = 0.0
        cost_fastest = 0.0
        cost_balanced = 0.0
        cost_safest = 0.0

        for i in range(len(path) - 1):
            u = path[i]
            v = path[i + 1]
            edge = self.graph.get_edge_data(u, v)
            if not edge:
                edge = self.graph.get_edge_data(v, u) or {}

            length = edge.get("length", 50.0)
            travel_time = edge.get("travel_time_sec", length / 6.0)
            safety = edge.get("safety_score", 50.0)

            total_length += length
            total_travel_time_sec += travel_time
            weighted_safety += (length * safety)

            cost_fastest += travel_time
            cost_balanced += self._get_cost(u, v, edge, "balanced")
            cost_safest += self._get_cost(u, v, edge, "safest")

        avg_safety = round(weighted_safety / total_length, 1) if total_length > 0 else 50.0
        distance_km = round(total_length / 1000.0, 2)
        est_minutes = max(1, int(round(total_travel_time_sec / 60.0))) if total_travel_time_sec > 0 else 1

        return {
            "path": path,
            "distance_km": distance_km,
            "estimated_time_minutes": est_minutes,
            "travel_time_sec": total_travel_time_sec,
            "safety_score": avg_safety,
            "cost_fastest": cost_fastest,
            "cost_balanced": cost_balanced,
            "cost_safest": cost_safest,
        }

    def _select_candidates_for_modes(self, candidates: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        Select optimal candidate for each of the three modes:
        - Fastest: strictly minimizes travel_time_sec (tie-break on safety_score).
        - Safest: minimizes cost_safest (prioritizes high safety while considering travel time).
        - Balanced: minimizes cost_balanced (reasonable trade-off between travel time and safety).
        """
        if not candidates:
            return {}

        best_fastest = min(candidates, key=lambda c: (c["travel_time_sec"], -c["safety_score"]))
        best_safest = min(candidates, key=lambda c: (c["cost_safest"], c["travel_time_sec"]))
        best_balanced = min(candidates, key=lambda c: (c["cost_balanced"], c["travel_time_sec"]))

        return {
            "fastest": best_fastest,
            "safest": best_safest,
            "balanced": best_balanced,
        }

    def calculate_route(
        self,
        origin_lat: float, origin_lon: float,
        dest_lat: float, dest_lon: float,
        mode: str = "safest"
    ) -> Dict[str, Any]:
        if not self.is_loaded:
            self.load_network()

        mode_clean = mode.lower()
        if mode_clean not in ["fastest", "balanced", "safest"]:
            mode_clean = "safest"

        start_node = self.find_nearest_node(origin_lat, origin_lon)
        end_node = self.find_nearest_node(dest_lat, dest_lon)

        if start_node == end_node:
            return self._create_empty_route(mode_clean, origin_lat, origin_lon)

        candidates = self._generate_candidate_paths(start_node, end_node)
        if not candidates:
            return self._create_empty_route(mode_clean, origin_lat, origin_lon, dest_lat, dest_lon)

        evaluated = [self._evaluate_candidate(p) for p in candidates]
        selected_map = self._select_candidates_for_modes(evaluated)
        selected = selected_map.get(mode_clean, evaluated[0])

        has_alternatives = len(candidates) > 1
        return self._build_route_output(
            selected["path"], mode_clean, origin_lat, origin_lon, dest_lat, dest_lon,
            has_alternatives=has_alternatives
        )


    def _build_route_output(
        self,
        path: List[int],
        mode: str,
        origin_lat: float, origin_lon: float,
        dest_lat: float, dest_lon: float,
        has_alternatives: bool = True
    ) -> Dict[str, Any]:
        total_length = 0.0
        total_travel_time_sec = 0.0
        weighted_safety_sum = 0.0

        all_coords = [[origin_lon, origin_lat]]
        segments = []

        total_police_dists = []
        total_hospital_dists = []
        total_lighting_risks = []
        total_isolation_risks = []
        total_bars = 0
        total_liquor = 0
        commercial_densities = []

        edge_list = []

        for i in range(len(path) - 1):
            u = path[i]
            v = path[i + 1]
            edge = self.graph.get_edge_data(u, v)
            if not edge:
                edge = self.graph.get_edge_data(v, u) or {}

            length = edge.get("length", 50.0)
            travel_time = edge.get("travel_time_sec", length / 6.0)
            safety = edge.get("safety_score", 50.0)
            s_level = edge.get("safety_level", "Moderate")
            r_name = edge.get("name", "")
            r_type = edge.get("road_type", "residential")
            r_id = edge.get("road_id", 0)

            total_length += length
            total_travel_time_sec += travel_time
            weighted_safety_sum += (length * safety)

            total_police_dists.append(edge.get("police_distance", 5000.0))
            total_hospital_dists.append(edge.get("hospital_distance", 5000.0))
            total_lighting_risks.append(edge.get("lighting_risk", 15.0))
            total_isolation_risks.append(edge.get("isolation_risk", 10.0))
            total_bars += edge.get("bar_count", 0)
            total_liquor += edge.get("liquor_shop_count", 0)
            commercial_densities.append(edge.get("commercial_density", 0.0))

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
        if edge_list:
            # Group consecutive edges on the same road name
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
        final_score = round(max(0.0, min(100.0, avg_safety)), 1)
        final_level = get_safety_level(final_score)

        explanations = []
        avg_lighting_risk = np.mean(total_lighting_risks) if total_lighting_risks else 15.0
        avg_isolation_risk = np.mean(total_isolation_risks) if total_isolation_risks else 10.0
        min_police_dist = min(total_police_dists) if total_police_dists else 5000.0
        min_hospital_dist = min(total_hospital_dists) if total_hospital_dists else 5000.0
        avg_comm_dens = np.mean(commercial_densities) if commercial_densities else 0.0

        if avg_lighting_risk <= 12.0:
            explanations.append("Better estimated lighting along major thoroughfares")
        if avg_comm_dens >= 0.01:
            explanations.append("More nearby active shops, transit, and commercial venues")
        if min_police_dist <= 1200.0:
            explanations.append(f"Passes within {int(min_police_dist)}m of a police station")
        if min_hospital_dist <= 800.0:
            explanations.append(f"Passes within {int(min_hospital_dist)}m of emergency medical facilities")
        if avg_isolation_risk <= 6.0:
            explanations.append("Lower environmental isolation and higher natural surveillance")
        if total_bars == 0 and total_liquor == 0:
            explanations.append("Zero exposure to bars or liquor outlets")

        if mode == "fastest":
            explanations.insert(0, "Shortest travel time along high-speed corridors")
        elif mode == "balanced":
            explanations.insert(0, "Medium route: enhanced safety with moderate travel time")
        elif mode == "safest":
            explanations.insert(0, "Maximized safety: prioritized lighting, active retail, and emergency hubs")

        if not explanations:
            explanations.append("Standard navigational corridor with verified road network coverage")
        if not has_alternatives:
            explanations.append("Single physical corridor; alternative routes unavailable in graph")

        distance_km = round(total_length / 1000.0, 2)
        est_minutes = max(1, int(round(total_travel_time_sec / 60.0)))

        return {
            "route_type": mode,
            "distance_km": distance_km,
            "estimated_time_minutes": est_minutes,
            "safety_score": final_score,
            "safety_level": final_level,
            "geometry": {
                "type": "LineString",
                "coordinates": clean_coords
            },
            "explanation": explanations,
            "segments": segments[:15],
            "steps": steps,
            "node_sequence": path
        }

    def _create_empty_route(self, mode: str, o_lat: float, o_lon: float, d_lat: float = None, d_lon: float = None) -> Dict[str, Any]:
        coords = [[o_lon, o_lat]]
        if d_lat and d_lon:
            coords.append([d_lon, d_lat])
            dist = round(haversine_meters(o_lat, o_lon, d_lat, d_lon) / 1000.0, 2)
        else:
            dist = 0.0

        # Nominal driving speed 30 km/h (8.33 m/s) matching urban tertiary street speed
        dur_s = int(round(dist * 1000.0 / 8.33)) if dist > 0 else 0
        est_minutes = max(1, int(round(dur_s / 60.0))) if dist > 0 else 0

        return {
            "route_type": mode,
            "distance_km": dist,
            "estimated_time_minutes": est_minutes,
            "safety_score": 65.0,
            "safety_level": "Safe",
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
                    "distance_text": f"{dist} km" if dist >= 1.0 else f"{int(dist * 1000)} m",
                    "duration_sec": dur_s,
                    "street_name": "Direct Route",
                    "safety_score": 65.0,
                    "safety_level": "Safe",
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
                    "safety_score": 65.0,
                    "safety_level": "Safe",
                    "coordinates": coords[-1:]
                }
            ],
            "node_sequence": []
        }

    def compare_routes(
        self,
        origin_lat: float, origin_lon: float,
        dest_lat: float, dest_lon: float
    ) -> Dict[str, Any]:
        if not self.is_loaded:
            self.load_network()

        start_node = self.find_nearest_node(origin_lat, origin_lon)
        end_node = self.find_nearest_node(dest_lat, dest_lon)

        if start_node == end_node:
            f = self._create_empty_route("fastest", origin_lat, origin_lon)
            s = self._create_empty_route("safest", origin_lat, origin_lon)
            b = self._create_empty_route("balanced", origin_lat, origin_lon)
            return {
                "origin": {"latitude": origin_lat, "longitude": origin_lon},
                "destination": {"latitude": dest_lat, "longitude": dest_lon},
                "fastest": f,
                "safest": s,
                "balanced": b
            }

        candidates = self._generate_candidate_paths(start_node, end_node)
        if not candidates:
            f = self._create_empty_route("fastest", origin_lat, origin_lon, dest_lat, dest_lon)
            s = self._create_empty_route("safest", origin_lat, origin_lon, dest_lat, dest_lon)
            b = self._create_empty_route("balanced", origin_lat, origin_lon, dest_lat, dest_lon)
            return {
                "origin": {"latitude": origin_lat, "longitude": origin_lon},
                "destination": {"latitude": dest_lat, "longitude": dest_lon},
                "fastest": f,
                "safest": s,
                "balanced": b
            }

        evaluated = [self._evaluate_candidate(p) for p in candidates]
        selected_map = self._select_candidates_for_modes(evaluated)
        has_alternatives = len(candidates) > 1

        fastest_r = self._build_route_output(
            selected_map["fastest"]["path"], "fastest",
            origin_lat, origin_lon, dest_lat, dest_lon,
            has_alternatives=has_alternatives
        )
        safest_r = self._build_route_output(
            selected_map["safest"]["path"], "safest",
            origin_lat, origin_lon, dest_lat, dest_lon,
            has_alternatives=has_alternatives
        )
        balanced_r = self._build_route_output(
            selected_map["balanced"]["path"], "balanced",
            origin_lat, origin_lon, dest_lat, dest_lon,
            has_alternatives=has_alternatives
        )

        return {
            "origin": {"latitude": origin_lat, "longitude": origin_lon},
            "destination": {"latitude": dest_lat, "longitude": dest_lon},
            "fastest": fastest_r,
            "safest": safest_r,
            "balanced": balanced_r
        }
