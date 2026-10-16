"""
scripts/test_travel_time_consistency.py
=============================================================================
Verification script testing deterministic travel-time calculation:
1. Runs 5 consecutive tests on identical origin/destination pairs.
2. Compares fastest, balanced, and safest modes.
3. Asserts zero variance in travel time, distance, safety score, and step durations.
4. Verifies physical unit consistency (meters -> km, seconds -> minutes).
=============================================================================
"""

import sys
import os
import json

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.routing.router import NashikRoadNetwork

def test_travel_time_determinism():
    print("=" * 80)
    print("RUNNING DETERMINISTIC TRAVEL-TIME AND UNIT VERIFICATION (5 RUNS PER PAIR)")
    print("=" * 80)

    test_pairs = [
        {
            "name": "Benchmark Route (Panchavati Corridor)",
            "origin": (20.0059, 73.7897),
            "dest": (20.0124, 73.7875),
        },
        {
            "name": "Cross-City Corridor (Nashik Road Station -> College Road)",
            "origin": (19.9530, 73.8340),
            "dest": (20.0050, 73.7650),
        },
        {
            "name": "Panchavati Ramkund -> Muktidham Temple",
            "origin": (20.0080, 73.7930),
            "dest": (19.9488, 73.8382),
        }
    ]

    with TestClient(app) as client:
        for pair_idx, pair in enumerate(test_pairs, 1):
            o_lat, o_lon = pair["origin"]
            d_lat, d_lon = pair["dest"]
            print(f"\n[Test Pair {pair_idx}/3] {pair['name']}")
            print(f"  Origin: ({o_lat}, {o_lon}) -> Dest: ({d_lat}, {d_lon})")

            runs_record = {"fastest": [], "balanced": [], "safest": []}

            for run_num in range(1, 6):
                params = {
                    "origin_lat": o_lat,
                    "origin_lon": o_lon,
                    "dest_lat": d_lat,
                    "dest_lon": d_lon
                }
                res = client.get("/routes/compare", params=params)
                assert res.status_code == 200, f"Compare failed: {res.text}"
                data = res.json()

                for mode in ["fastest", "balanced", "safest"]:
                    m_data = data[mode]
                    step_durations = [s["duration_sec"] for s in m_data.get("steps", [])]
                    runs_record[mode].append({
                        "run": run_num,
                        "distance_km": m_data["distance_km"],
                        "time_min": m_data["estimated_time_minutes"],
                        "score": m_data["safety_score"],
                        "level": m_data["safety_level"],
                        "num_steps": len(m_data.get("steps", [])),
                        "total_step_sec": sum(step_durations)
                    })

            # Check consistency across all 5 runs
            print("  Results across 5 repeated runs:")
            print(f"  {'Mode':10s} | {'Run 1':16s} | {'Run 2':16s} | {'Run 3':16s} | {'Run 4':16s} | {'Run 5':16s} | {'Consistent?'}")
            print("  " + "-" * 105)

            for mode in ["fastest", "balanced", "safest"]:
                recs = runs_record[mode]
                run_strs = [f"{r['time_min']}m/{r['distance_km']}k/{r['score']}" for r in recs]
                
                # Assert 100% identity
                first = recs[0]
                is_identical = all(
                    r["time_min"] == first["time_min"] and
                    r["distance_km"] == first["distance_km"] and
                    r["score"] == first["score"] and
                    r["num_steps"] == first["num_steps"] and
                    r["total_step_sec"] == first["total_step_sec"]
                    for r in recs
                )

                assert is_identical, f"Non-deterministic result detected for mode {mode}!"
                status = "PASS (100% Identical)" if is_identical else "FAIL"
                print(f"  {mode:10s} | {run_strs[0]:16s} | {run_strs[1]:16s} | {run_strs[2]:16s} | {run_strs[3]:16s} | {run_strs[4]:16s} | {status}")

            # Verify physical unit logic on Run 1
            print("\n  Physical Unit & Aggregation Verification:")
            for mode in ["fastest", "balanced", "safest"]:
                r = runs_record[mode][0]
                calculated_min = r["time_min"]
                total_step_sec = r["total_step_sec"]
                approx_min_from_steps = round(total_step_sec / 60.0)
                print(f"    Mode '{mode}': {r['distance_km']} km | API est_time: {calculated_min} min | Sum of step durations: {total_step_sec}s (~{approx_min_from_steps} min)")
                # Check that step seconds roughly equal est minutes (within 1 min rounding)
                assert abs(calculated_min - approx_min_from_steps) <= 1, f"Mismatch between step durations and total time: {calculated_min} vs {approx_min_from_steps}"

    print("\n" + "=" * 80)
    print("ALL 5-RUN REPEATABILITY & UNIT CONSISTENCY TESTS PASSED (100% DETERMINISTIC)")
    print("=" * 80)

if __name__ == "__main__":
    test_travel_time_determinism()
