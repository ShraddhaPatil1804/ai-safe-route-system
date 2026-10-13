import requests

terms = [
    'Muktidham',
    'Tidke Colony',
    'Dwarka',
    'Govind Nagar',
    'CCM',
    'Kalaram',
    'Apollo',
    'Trimbak',
    '19.98, 73.78',
    'Sula'
]

print("Testing /places/search endpoint:")
for t in terms:
    url = f"http://127.0.0.1:8000/places/search?q={t}&limit=2"
    r = requests.get(url)
    items = r.json()
    print(f"\nQuery: '{t}' -> Found {len(items)} result(s)")
    for it in items:
        print(f"  * {it['name']} [{it['tag']}] ({it['latitude']}, {it['longitude']})")
