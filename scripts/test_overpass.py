import requests
import json

endpoints = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
    "https://overpass.private.coffee/api/interpreter"
]

# Nashik bounding box (approx 19.85 to 20.08 lat, 73.68 to 73.90 lon)
# Or using area filter
query = """[out:json][timeout:30];
(
  node["amenity"="police"](19.85,73.68,20.10,73.92);
  way["amenity"="police"](19.85,73.68,20.10,73.92);
);
out center;
"""

for ep in endpoints:
    try:
        print(f"Testing {ep}...")
        resp = requests.post(ep, data={"data": query}, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            elems = data.get("elements", [])
            print(f"  SUCCESS! Found {len(elems)} police stations from {ep}")
            break
        else:
            print(f"  Failed with status {resp.status_code}")
    except Exception as e:
        print(f"  Error: {e}")
