import sys
import os
import json
sys.path.insert(0, os.path.abspath("."))
from fastapi.testclient import TestClient
from backend.app.main import app

def run_tests():
    client = TestClient(app)

    pairs = [
        ("Pair 1", 20.0059, 73.7897, 20.0124, 73.7875),
        ("Pair 2", 19.9530, 73.8340, 20.0050, 73.7650),
        ("Pair 3", 20.0080, 73.7930, 19.9488, 73.8382),
        ("Pair 4", 20.0150, 73.7550, 19.9720, 73.7710),
        ("Pair 5", 19.9650, 73.7750, 20.0100, 73.7900),
    ]

    modes = ["fastest", "balanced", "safest"]

    results = []

    print("==========================================================================================")
    print("PHASE 8 REPRODUCIBLE ROUTE TESTING (5 PAIRS x 3 MODES x 5 REPEATED RUNS)")
    print("==========================================================================================")

    for p_name, o_lat, o_lon, d_lat, d_lon in pairs:
        print(f"\n---> Testing {p_name}: Origin ({o_lat}, {o_lon}) -> Dest ({d_lat}, {d_lon})")

        # 5 repeated runs
        runs_data = []
        for r_idx in range(5):
            res = client.get("/routes/compare", params={
                "origin_lat": o_lat,
                "origin_lon": o_lon,
                "dest_lat": d_lat,
                "dest_lon": d_lon
            })
            assert res.status_code == 200, f"Error {res.status_code}: {res.text}"
            runs_data.append(res.json())

        # Check determinism across 5 runs
        first_run = runs_data[0]
        deterministic = all(run == first_run for run in runs_data)
        print(f"     Repeated-run determinism: 5/5 identical = {deterministic}")

        for m in modes:
            m_data = first_run[m]
            dist = f"{m_data['distance_km']} km"
            t_min = f"{m_data['estimated_time_minutes']} min"
            score = str(m_data["safety_score"])
            nodes = m_data.get("node_sequence", [])
            node_seq_summary = f"{len(nodes)} nodes [{nodes[0]}..{nodes[-1]}]" if nodes else "N/A"
            u_node = nodes[0] if nodes else "N/A"
            v_node = nodes[-1] if nodes else "N/A"

            status = "PASS (Valid Corridor)" if deterministic and len(nodes) > 0 else "FAIL"

            results.append({
                "pair": p_name,
                "mode": m.capitalize(),
                "u": u_node,
                "v": v_node,
                "seq": node_seq_summary,
                "dist": dist,
                "time": t_min,
                "score": score,
                "consistency": "5/5 identical (100%)" if deterministic else "Non-deterministic",
                "result": status
            })

    print("\n" + "=" * 130)
    print("FINAL RESULTS TABLE FOR PHASE 8")
    print("=" * 130)
    header = f"{'Test Pair':<10} | {'Mode':<9} | {'Snapped Origin':<16} | {'Snapped Destination':<20} | {'Route/Edge Sequence':<28} | {'Distance':<9} | {'Est. Time':<10} | {'Safety':<7} | {'Consistency':<24} | {'Result':<10}"
    print(header)
    print("-" * 130)
    for r in results:
        row = f"{r['pair']:<10} | {r['mode']:<9} | {str(r['u']):<16} | {str(r['v']):<20} | {r['seq']:<28} | {r['dist']:<9} | {r['time']:<10} | {r['score']:<7} | {r['consistency']:<24} | {r['result']:<10}"
        print(row)
    print("=" * 130)

if __name__ == "__main__":
    run_tests()
