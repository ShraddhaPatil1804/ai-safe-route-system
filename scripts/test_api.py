import sys
import os
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from backend.app.main import app

def run_tests():
    print("Testing FastAPI Application Endpoints with TestClient...")
    with TestClient(app) as client:
        # 1. Health
        print("\n--> 1. Testing GET /health")
        r = client.get("/health")
        print("Status:", r.status_code, "Response:", r.json())
        assert r.status_code == 200

        # 2. Auth Signup
        print("\n--> 2. Testing POST /auth/signup")
        email = f"test_user_{int(time.time())}@example.com"
        signup_payload = {
            "name": "Priya Sharma",
            "email": email,
            "password": "SecurePassword123!"
        }
        r = client.post("/auth/signup", json=signup_payload)
        print("Status:", r.status_code, "Token present:", "access_token" in r.json())
        assert r.status_code == 200
        token = r.json()["access_token"]

        # 3. Auth Login
        print("\n--> 3. Testing POST /auth/login")
        login_payload = {
            "email": email,
            "password": "SecurePassword123!"
        }
        r = client.post("/auth/login", json=login_payload)
        print("Status:", r.status_code, "Token present:", "access_token" in r.json())
        assert r.status_code == 200

        # 4. Auth Me
        print("\n--> 4. Testing GET /auth/me")
        headers = {"Authorization": f"Bearer {token}"}
        r = client.get("/auth/me", headers=headers)
        print("Status:", r.status_code, "User:", r.json())
        assert r.status_code == 200

        # 5. POIs
        print("\n--> 5. Testing GET /pois?category=police")
        r = client.get("/pois?category=police")
        print("Status:", r.status_code, "Count:", len(r.json()), "Sample:", r.json()[:1])
        assert r.status_code == 200

        # 6. Emergency Facilities
        print("\n--> 6. Testing GET /pois/emergency")
        r = client.get("/pois/emergency?lat=19.997&lon=73.789")
        print("Status:", r.status_code, "Emergency Facilities:", r.json())
        assert r.status_code == 200
        assert "police" in r.json()

        # 7. Routes Compare
        print("\n--> 7. Testing GET /routes/compare (Day & Night)")
        r = client.get("/routes/compare?origin_lat=19.953&origin_lon=73.834&dest_lat=20.005&dest_lon=73.765&time_of_day=day")
        print("Status:", r.status_code)
        data = r.json()
        print("  Fastest :", data["fastest"]["distance_km"], "km |", data["fastest"]["estimated_time_minutes"], "min | Score:", data["fastest"]["safety_score"])
        print("  Safest  :", data["safest"]["distance_km"], "km |", data["safest"]["estimated_time_minutes"], "min | Score:", data["safest"]["safety_score"])
        print("  Balanced:", data["balanced"]["distance_km"], "km |", data["balanced"]["estimated_time_minutes"], "min | Score:", data["balanced"]["safety_score"])
        if "shortest" in data and data["shortest"]:
            print("  Shortest:", data["shortest"]["distance_km"], "km |", data["shortest"]["estimated_time_minutes"], "min | Score:", data["shortest"]["safety_score"])
        print("  Safest Reasons:", data["safest"]["explanation"][:2])
        assert r.status_code == 200

        # Night comparison
        r_night = client.get("/routes/compare?origin_lat=19.953&origin_lon=73.834&dest_lat=20.005&dest_lon=73.765&time_of_day=night")
        assert r_night.status_code == 200
        night_data = r_night.json()
        print("  Night Safest:", night_data["safest"]["distance_km"], "km |", night_data["safest"]["estimated_time_minutes"], "min | Score:", night_data["safest"]["safety_score"])

        # 8. Heatmap
        print("\n--> 8. Testing GET /heatmap")
        r = client.get("/heatmap?min_lat=19.95&min_lon=73.75&max_lat=20.02&max_lon=73.85&limit=10")
        print("Status:", r.status_code, "Features count:", len(r.json().get("features", [])))
        assert r.status_code == 200

        # 9. Safety Report Submission
        print("\n--> 9. Testing POST /reports")
        report_data = {
            "report_type": "Poor Lighting",
            "description": "Streetlights off along College Road near the park",
            "severity": "Medium",
            "latitude": 20.005,
            "longitude": 73.765
        }
        r = client.post("/reports", json=report_data, headers=headers)
        print("Status:", r.status_code, "Report created:", r.json())
        assert r.status_code == 200

        # 10. Get Safety Reports
        print("\n--> 10. Testing GET /reports")
        r = client.get("/reports")
        print("Status:", r.status_code, "Reports count:", len(r.json()))
        assert r.status_code == 200

        print("\n ALL BACKEND ENDPOINTS PASSED WITH 100% SUCCESS!")

if __name__ == "__main__":
    run_tests()
