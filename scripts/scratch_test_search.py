import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from fastapi.testclient import TestClient
from backend.app.main import app

with TestClient(app) as client:
    for q in ['Muktidham to College Road', 'Panchavati to City Center', 'From Muktidham to College Road', 'Nashik Road to College Road']:
        res = client.get('/places/search', params={'q': q})
        print(f'Query: "{q}" -> {len(res.json())} results: {res.json()}')
