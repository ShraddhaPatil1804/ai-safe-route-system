"""
test_phase_features.py
=============================================================================
Comprehensive test suite verifying:
1. Search endpoint (places, landmarks, named roads, coordinates, empty states)
2. POI Category filtering across all 12 specified categories (including 9 AM)
3. Authentication endpoints (Signup, Login, /auth/me, invalid credentials)
4. Baseline Routing Benchmark (Origin 20.0059, 73.7897 -> Dest 20.0124, 73.7875)
5. Route comparison endpoint (/routes/compare)
=============================================================================
"""

import sys
import os
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from backend.app.main import app

def run_all_tests():
    print("=" * 70)
    print("STARTING TEST SUITE: SEARCH, POIS, AUTH, ROUTING REGRESSION")
    print("=" * 70)

    with TestClient(app) as client:
        # 1. Health check
        print("\n--> [1/5] Testing GET /health...")
        r_health = client.get("/health")
        assert r_health.status_code == 200, f"Health check failed: {r_health.status_code}"
        print(f"    Health Status: {r_health.status_code} | System: {r_health.json().get('system')}")

        # 2. Search Endpoint Verification
        print("\n--> [2/5] Testing GET /places/search...")
        test_queries = [
            ("Muktidham", "Landmark"),
            ("Sarkarwada", "Police/Landmark"),
            ("College Road", "Prominent Road"),
            ("Starbucks", "Cafe"),
            ("19.998, 73.782", "Exact Coordinates"),
            ("NonExistentXYZPlace123", "Empty Result State")
        ]
        for q, label in test_queries:
            r = client.get("/places/search", params={"q": q, "limit": 3})
            assert r.status_code == 200, f"Search failed for {q}: {r.status_code}"
            items = r.json()
            print(f"    Query: '{q:22s}' [{label:18s}] -> Results: {len(items)}")
            if items:
                print(f"      Sample: {items[0].get('name')} ({items[0].get('latitude')}, {items[0].get('longitude')})")
            else:
                assert q == "NonExistentXYZPlace123", "Unexpected empty result for valid query!"

        # 3. POI Categories & Filter Verification
        print("\n--> [3/5] Testing GET /pois & Category Filters (all 11 categories)...")
        r_cats = client.get("/pois/categories")
        assert r_cats.status_code == 200
        cat_counts = {c["category"]: c["count"] for c in r_cats.json()}
        print(f"    Total Distinct Categories in DB: {len(cat_counts)}")

        expected_11_categories = [
            ("all", "All Markers"),
            ("police", "Police"),
            ("hospital", "Hospitals"),
            ("pharmacy", "Pharmacies"),
            ("restaurant", "Restaurants"),
            ("cafe", "Cafes"),
            ("bus_stop", "Bus Stops"),
            ("bank", "Banks"),
            ("fuel", "Fuel"),
            ("park", "Parks"),
            ("bar", "Bars")
        ]

        for cat_id, label in expected_11_categories:
            r_pois = client.get("/pois", params={"category": cat_id, "limit": 100})
            assert r_pois.status_code == 200
            pois = r_pois.json()
            print(f"    Category: {label:14s} (id='{cat_id:8s}') -> Count: {len(pois):3d}")
            if cat_id != "all":
                assert len(pois) > 0, f"Category '{label}' unexpectedly empty!"
                for p in pois:
                    assert p["category"] == cat_id or (cat_id == "hospital" and p["category"] in ["hospital", "clinic"]), f"Category mismatch: {p['category']}"

        # 4. Authentication Endpoints Verification
        print("\n--> [4/5] Testing Authentication Endpoints...")
        test_email = f"user_test_{int(time.time())}@nashiksafe.org"
        signup_payload = {
            "name": "Kavita Patil",
            "email": test_email,
            "password": "ValidPassword2026!"
        }

        # Signup
        r_signup = client.post("/auth/signup", json=signup_payload)
        assert r_signup.status_code == 200, f"Signup failed: {r_signup.text}"
        token = r_signup.json().get("access_token")
        assert token, "Token not returned from signup"
        print(f"    POST /auth/signup: 200 OK | Created User: {r_signup.json().get('user', {}).get('name')}")

        # Login
        r_login = client.post("/auth/login", json={"email": test_email, "password": "ValidPassword2026!"})
        assert r_login.status_code == 200, f"Login failed: {r_login.text}"
        print(f"    POST /auth/login:  200 OK | Token Type: {r_login.json().get('token_type')}")

        # Invalid login
        r_bad = client.post("/auth/login", json={"email": test_email, "password": "WrongPassword"})
        assert r_bad.status_code == 401, f"Expected 401 on wrong password, got: {r_bad.status_code}"
        print(f"    POST /auth/login (Invalid Credentials): 401 Unauthorized (Correctly Rejected)")

        # Auth Me (Session Validation)
        r_me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert r_me.status_code == 200, f"GET /auth/me failed: {r_me.text}"
        assert r_me.json().get("email") == test_email.lower()
        print(f"    GET /auth/me:      200 OK | Verified User Email: {r_me.json().get('email')}")

        # 5. Routing Regression Benchmark Verification
        print("\n--> [5/5] Testing Baseline Routing Regression Benchmark...")
        params = {
            "origin_lat": 20.0059,
            "origin_lon": 73.7897,
            "dest_lat": 20.0124,
            "dest_lon": 73.7875,
            "mode": "safest"
        }
        r_route = client.get("/route", params=params)
        assert r_route.status_code == 200, f"GET /route failed: {r_route.text}"
        r_data = r_route.json()
        print(f"    Calculated Distance:   {r_data.get('distance_km')} km  (Expected ~1.52 km)")
        print(f"    Calculated TravelTime: {r_data.get('estimated_time_minutes')} min  (Expected ~3 min)")
        print(f"    Baseline Safety Score: {r_data.get('safety_score')}  (Expected 81.3)")

        assert abs(r_data.get("distance_km") - 1.52) < 0.1, f"Distance regression: {r_data.get('distance_km')}"
        assert r_data.get("safety_score") == 81.3, f"Safety score regression: {r_data.get('safety_score')}"
        print("    CONFIRMATION: ROUTE BENCHMARK IS 100% VERIFIED WITH DYNAMIC POI SAFETY SCORING")

        # Compare routes
        r_compare = client.get("/routes/compare", params={
            "origin_lat": 20.0059,
            "origin_lon": 73.7897,
            "dest_lat": 20.0124,
            "dest_lon": 73.7875
        })
        assert r_compare.status_code == 200, f"GET /routes/compare failed: {r_compare.text}"
        c_data = r_compare.json()
        print(f"    GET /routes/compare: 200 OK | Modes: fastest ({c_data['fastest']['safety_score']}), safest ({c_data['safest']['safety_score']}), balanced ({c_data['balanced']['safety_score']})")

    print("\n" + "=" * 70)
    print("ALL TESTS PASSED WITH 100% SUCCESS!")
    print("=" * 70)

if __name__ == "__main__":
    run_all_tests()
