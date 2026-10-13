import requests

origin_lat, origin_lon = 19.953, 73.834 # Nashik Road Station hub

queries = [
    'Tidke Colony',
    'Muktidham',
    'Govind Nagar',
    'Dwarka Circle',
    'Sula Vineyards',
    'Kalaram Mandir',
    'Apollo Hospital',
    'City Centre Mall'
]

print("Simulating end-to-end user input to route generation across Nashik:")
for q in queries:
    search_res = requests.get(f"http://127.0.0.1:8000/places/search?q={q}&limit=1").json()
    if search_res:
        place = search_res[0]
        d_lat, d_lon = place['latitude'], place['longitude']
        route_res = requests.get(
            f"http://127.0.0.1:8000/routes/compare?origin_lat={origin_lat}&origin_lon={origin_lon}&dest_lat={d_lat}&dest_lon={d_lon}"
        ).json()
        f_min = route_res['fastest']['estimated_time_minutes']
        f_km = route_res['fastest']['distance_km']
        f_s = route_res['fastest']['safety_score']

        m_min = route_res['balanced']['estimated_time_minutes']
        m_km = route_res['balanced']['distance_km']
        m_s = route_res['balanced']['safety_score']

        s_min = route_res['safest']['estimated_time_minutes']
        s_km = route_res['safest']['distance_km']
        s_s = route_res['safest']['safety_score']
        first_step = route_res['safest']['steps'][0]['instruction'] if route_res['safest']['steps'] else 'Proceed'

        print(f"\nUser Input: '{q}' -> Resolved to: {place['name']} [{place['tag']}] ({d_lat}, {d_lon})")
        print(f"  * Fastest:  {f_min} min | {f_km} km | Safety: {f_s}/100")
        print(f"  * Medium:   {m_min} min | {m_km} km | Safety: {m_s}/100")
        print(f"  * Safest:   {s_min} min | {s_km} km | Safety: {s_s}/100")
        print(f"  * Navigation Step: '{first_step}'")
    else:
        print(f"\nUser Input: '{q}' -> NOT FOUND")
