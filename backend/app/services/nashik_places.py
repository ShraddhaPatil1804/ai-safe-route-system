"""
Comprehensive Nashik Places, Localities, Landmarks, and Hubs Database.
Enables instant, accurate geocoding and routing for any typed input across Nashik.
"""

from typing import List, Dict, Any, Optional
import re

NASHIK_CATALOG: List[Dict[str, Any]] = [
    # Transit & Major Stations
    {"name": "Nashik Road Railway Station", "tag": "Transit Hub", "lat": 19.9530, "lon": 73.8340, "keywords": ["station", "railway", "train", "nashik road"]},
    {"name": "CBS (Central Bus Stand) Nashik", "tag": "Bus Stand", "lat": 19.9975, "lon": 73.7898, "keywords": ["cbs", "bus stand", "central bus stand", "old cbs"]},
    {"name": "New CBS (Mela Stand)", "tag": "Bus Stand", "lat": 20.0010, "lon": 73.7845, "keywords": ["new cbs", "mela stand", "bus port"]},
    {"name": "Shalimar Bus Station", "tag": "Bus Stand", "lat": 19.9940, "lon": 73.7910, "keywords": ["shalimar", "bus", "shalimar chowk"]},
    {"name": "Thakkar Bazaar Bus Port", "tag": "Bus Port", "lat": 20.0005, "lon": 73.7810, "keywords": ["thakkar bazaar", "bus port", "private travel"]},
    {"name": "Nimani Bus Stand, Panchavati", "tag": "Bus Stand", "lat": 20.0140, "lon": 73.7970, "keywords": ["nimani", "nimani stand", "panchavati bus"]},
    {"name": "Ozar Airport (Nashik Airport)", "tag": "Airport", "lat": 20.1180, "lon": 73.9180, "keywords": ["ozar", "airport", "flight"]},
    {"name": "Gandhinagar Airport", "tag": "Airstrip", "lat": 19.9670, "lon": 73.8240, "keywords": ["gandhinagar", "airforce", "runway"]},

    # Major Circles, Chowks & Junctions
    {"name": "Dwarka Circle (Dwarka Chowk)", "tag": "Major Circle", "lat": 19.9942, "lon": 73.7970, "keywords": ["dwarka", "dwarka circle", "dwarka chowk", "highway circle"]},
    {"name": "Mumbai Naka Circle", "tag": "Major Circle", "lat": 19.9862, "lon": 73.7818, "keywords": ["mumbai naka", "naka", "highway junction"]},
    {"name": "Ashok Stambh Chowk", "tag": "Chowk", "lat": 20.0010, "lon": 73.7820, "keywords": ["ashok stambh", "pillar", "stambh chowk"]},
    {"name": "Canada Corner", "tag": "Commercial Circle", "lat": 19.9985, "lon": 73.7740, "keywords": ["canada corner", "canada", "sharanpur"]},
    {"name": "ABB Circle, Mahatma Nagar", "tag": "Major Circle", "lat": 19.9960, "lon": 73.7580, "keywords": ["abb circle", "abb", "trimbak road"]},
    {"name": "Jehan Circle, Gangapur Road", "tag": "Major Circle", "lat": 20.0160, "lon": 73.7520, "keywords": ["jehan circle", "gangapur chowk"]},
    {"name": "Trimurti Chowk, CIDCO", "tag": "Major Chowk", "lat": 19.9680, "lon": 73.7510, "keywords": ["trimurti", "trimurti chowk", "cidco chowk"]},
    {"name": "Pathardi Phata", "tag": "Highway Junction", "lat": 19.9480, "lon": 73.7650, "keywords": ["pathardi", "pathardi phata", "expressway"]},
    {"name": "Garware Point, Ambad", "tag": "Junction", "lat": 19.9410, "lon": 73.7430, "keywords": ["garware", "garware point", "ambad"]},
    {"name": "ITI Signal, Satpur", "tag": "Signal Chowk", "lat": 19.9990, "lon": 73.7410, "keywords": ["iti", "iti signal", "satpur iti"]},
    {"name": "Trimbak Naka", "tag": "Chowk", "lat": 19.9940, "lon": 73.7840, "keywords": ["trimbak naka", "trimbak road chowk"]},
    {"name": "Bytco Point, Nashik Road", "tag": "Major Junction", "lat": 19.9490, "lon": 73.8370, "keywords": ["bytco", "bytco point", "bytco hospital"]},
    {"name": "Sinnar Phata, Nashik Road", "tag": "Highway Junction", "lat": 19.9420, "lon": 73.8450, "keywords": ["sinnar phata", "sinnar naka"]},
    {"name": "Datta Mandir Signal, Nashik Road", "tag": "Signal Chowk", "lat": 19.9510, "lon": 73.8310, "keywords": ["datta mandir", "datta mandir signal"]},
    {"name": "Upnagar Signal", "tag": "Signal Chowk", "lat": 19.9610, "lon": 73.8180, "keywords": ["upnagar", "upnagar signal"]},
    {"name": "Ravivar Karanja (RK)", "tag": "Heritage Market", "lat": 20.0020, "lon": 73.7920, "keywords": ["rk", "ravivar karanja", "market"]},
    {"name": "Panchavati Karanja", "tag": "Heritage Chowk", "lat": 20.0095, "lon": 73.7940, "keywords": ["panchavati karanja", "karanja"]},

    # Colonies, Residential & Commercial Localities
    {"name": "College Road", "tag": "Prominent Avenue", "lat": 20.0055, "lon": 73.7645, "keywords": ["college road", "college rd", "byk", "kthm"]},
    {"name": "Gangapur Road", "tag": "Major Corridor", "lat": 20.0210, "lon": 73.7460, "keywords": ["gangapur road", "gangapur rd"]},
    {"name": "Sharanpur Road", "tag": "Commercial Road", "lat": 20.0005, "lon": 73.7730, "keywords": ["sharanpur road", "sharanpur"]},
    {"name": "Mahatma Nagar", "tag": "Prime Residential", "lat": 20.0010, "lon": 73.7560, "keywords": ["mahatma nagar", "mahatma"]},
    {"name": "Thatte Nagar", "tag": "Commercial Area", "lat": 20.0045, "lon": 73.7690, "keywords": ["thatte nagar", "thatte"]},
    {"name": "Tidke Colony", "tag": "Residential Colony", "lat": 19.9860, "lon": 73.7740, "keywords": ["tidke colony", "tidke", "milap nagar"]},
    {"name": "Govind Nagar", "tag": "Residential Area", "lat": 19.9820, "lon": 73.7690, "keywords": ["govind nagar", "govind"]},
    {"name": "Rane Nagar, CIDCO", "tag": "Residential Area", "lat": 19.9650, "lon": 73.7650, "keywords": ["rane nagar", "rane"]},
    {"name": "Chetna Nagar", "tag": "Colony", "lat": 19.9670, "lon": 73.7620, "keywords": ["chetna nagar", "chetna"]},
    {"name": "Indira Nagar", "tag": "Large Suburb", "lat": 19.9640, "lon": 73.7750, "keywords": ["indira nagar", "indira"]},
    {"name": "CIDCO (New Nashik)", "tag": "Major Suburb", "lat": 19.9720, "lon": 73.7580, "keywords": ["cidco", "new nashik", "cidco bus stand"]},
    {"name": "Pawan Nagar, CIDCO", "tag": "CIDCO Sector", "lat": 19.9750, "lon": 73.7480, "keywords": ["pawan nagar", "pawan"]},
    {"name": "Uttam Nagar, CIDCO", "tag": "CIDCO Sector", "lat": 19.9780, "lon": 73.7450, "keywords": ["uttam nagar", "uttam"]},
    {"name": "Kamatwade", "tag": "Suburb", "lat": 19.9610, "lon": 73.7420, "keywords": ["kamatwade", "kamatwada"]},
    {"name": "Satpur MIDC Industrial Area", "tag": "Industrial Hub", "lat": 19.9980, "lon": 73.7310, "keywords": ["satpur", "satpur midc", "midc satpur"]},
    {"name": "Ambad MIDC Industrial Area", "tag": "Industrial Hub", "lat": 19.9450, "lon": 73.7380, "keywords": ["ambad", "ambad midc", "midc ambad"]},
    {"name": "Parijat Nagar", "tag": "Residential Area", "lat": 20.0020, "lon": 73.7610, "keywords": ["parijat nagar", "parijat"]},
    {"name": "Samarth Nagar", "tag": "Residential Area", "lat": 20.0050, "lon": 73.7680, "keywords": ["samarth nagar", "samarth"]},
    {"name": "Krishi Nagar", "tag": "Residential Area", "lat": 20.0070, "lon": 73.7590, "keywords": ["krishi nagar", "krishi"]},
    {"name": "Serene Meadows, Gangapur Road", "tag": "Township", "lat": 20.0290, "lon": 73.7350, "keywords": ["serene meadows", "serene"]},
    {"name": "Anandwalli", "tag": "Residential Suburb", "lat": 20.0230, "lon": 73.7410, "keywords": ["anandwalli", "anandwali"]},
    {"name": "Mhasrul", "tag": "North Suburb", "lat": 20.0450, "lon": 73.8050, "keywords": ["mhasrul", "dindori road"]},
    {"name": "Makhmalabad", "tag": "North Suburb", "lat": 20.0410, "lon": 73.7820, "keywords": ["makhmalabad", "makhmalabad naka"]},
    {"name": "Adgaon", "tag": "Highway Suburb", "lat": 20.0380, "lon": 73.8450, "keywords": ["adgaon", "adgaon naka"]},
    {"name": "Panchavati", "tag": "Historic Cultural Hub", "lat": 20.0110, "lon": 73.7960, "keywords": ["panchavati", "panchvati"]},
    {"name": "Jail Road, Nashik Road", "tag": "Prominent Road", "lat": 19.9470, "lon": 73.8380, "keywords": ["jail road", "central jail"]},
    {"name": "Upnagar, Nashik Road", "tag": "Suburb", "lat": 19.9610, "lon": 73.8180, "keywords": ["upnagar"]},
    {"name": "Deolali Camp", "tag": "Cantonment Town", "lat": 19.9320, "lon": 73.8350, "keywords": ["deolali", "deolali camp", "cantonment"]},
    {"name": "Bhagur", "tag": "Historic Town", "lat": 19.9120, "lon": 73.8310, "keywords": ["bhagur", "savarkar smarak"]},
    {"name": "Wadala Naka / Wadala Gaon", "tag": "Locality", "lat": 19.9850, "lon": 73.7950, "keywords": ["wadala", "wadala naka", "wadala gaon"]},
    {"name": "Ashoka Marg", "tag": "Residential Avenue", "lat": 19.9750, "lon": 73.7920, "keywords": ["ashoka marg", "ashoka"]},
    {"name": "DGP Nagar", "tag": "Colony", "lat": 19.9550, "lon": 73.7690, "keywords": ["dgp nagar", "dgp"]},
    {"name": "Untwadi", "tag": "Commercial Suburb", "lat": 19.9740, "lon": 73.7640, "keywords": ["untwadi", "untwadi road"]},
    {"name": "Old Nashik (Bhadrakali / Tiwandha)", "tag": "Old City", "lat": 19.9961, "lon": 73.7915, "keywords": ["old nashik", "bhadrakali", "tiwandha", "sarkarwada"]},

    # Temples, Heritage & Tourism
    {"name": "Muktidham Temple, Nashik Road", "tag": "Prominent Temple", "lat": 19.9488, "lon": 73.8382, "keywords": ["muktidham", "muktidham temple", "muktidham mandir"]},
    {"name": "Shree Kalaram Mandir, Panchavati", "tag": "Historic Temple", "lat": 20.0092, "lon": 73.7965, "keywords": ["kalaram", "kalaram mandir", "kalaram temple"]},
    {"name": "Ramkund, Panchavati", "tag": "Sacred Ghat", "lat": 20.0078, "lon": 73.7928, "keywords": ["ramkund", "ram kund", "godavari ghat", "kumbh mela"]},
    {"name": "Sita Gumpha (Caves), Panchavati", "tag": "Historic Cave", "lat": 20.0098, "lon": 73.7972, "keywords": ["sita gumpha", "sita gupha", "caves"]},
    {"name": "Tapovan", "tag": "Sacred Heritage Area", "lat": 20.0040, "lon": 73.8120, "keywords": ["tapovan", "laxman rekha"]},
    {"name": "Kapaleshwar Mahadev Temple", "tag": "Historic Temple", "lat": 20.0075, "lon": 73.7935, "keywords": ["kapaleshwar", "shiva mandir"]},
    {"name": "Someshwar Waterfall & Temple", "tag": "Tourist Landmark", "lat": 20.0320, "lon": 73.7320, "keywords": ["someshwar", "waterfall", "someshwar temple"]},
    {"name": "Navshya Ganapati Mandir, Anandwalli", "tag": "Prominent Temple", "lat": 20.0195, "lon": 73.7390, "keywords": ["navshya ganapati", "ganesh mandir", "anandwalli ganpati"]},
    {"name": "Sundarnarayan Temple", "tag": "Historic Temple", "lat": 20.0070, "lon": 73.7920, "keywords": ["sundarnarayan", "temple"]},
    {"name": "Pandavleni Caves & Buddha Vihar", "tag": "Heritage Monument", "lat": 19.9430, "lon": 73.7530, "keywords": ["pandavleni", "pandav leni", "caves", "dada saheb phalke smarak"]},
    {"name": "Sula Vineyards, Govardhan", "tag": "Tourist Destination", "lat": 20.0064, "lon": 73.6876, "keywords": ["sula", "sula vineyards", "vineyard", "govardhan"]},
    {"name": "York Winery & Tasting Room", "tag": "Winery Landmark", "lat": 20.0040, "lon": 73.6820, "keywords": ["york", "york winery"]},
    {"name": "Gangapur Dam", "tag": "Water Reservoir", "lat": 20.0520, "lon": 73.6750, "keywords": ["gangapur dam", "dam", "backwaters"]},
    {"name": "Trimbakeshwar Jyotirlinga Temple", "tag": "Jyotirlinga Pilgrimage", "lat": 19.9320, "lon": 73.5310, "keywords": ["trimbakeshwar", "trimbak", "jyotirlinga"]},

    # Shopping Malls & Retail Hubs
    {"name": "City Centre Mall (CCM), Untwadi", "tag": "Shopping Mall", "lat": 19.9725, "lon": 73.7635, "keywords": ["ccm", "city centre mall", "city center", "untwadi mall"]},
    {"name": "Pinnacle Mall, Sharanpur Road", "tag": "Shopping Mall", "lat": 20.0005, "lon": 73.7730, "keywords": ["pinnacle", "pinnacle mall"]},
    {"name": "Reliance Centro Mall, College Road", "tag": "Shopping Mall", "lat": 20.0070, "lon": 73.7640, "keywords": ["centro", "reliance mall", "reliance centro"]},
    {"name": "Star Bazaar Mall, Gangapur Road", "tag": "Hypermarket Mall", "lat": 20.0150, "lon": 73.7550, "keywords": ["star bazaar", "star mall"]},
    {"name": "D-Mart Shopping Mall, Indira Nagar", "tag": "Supermarket Hub", "lat": 19.9615, "lon": 73.7780, "keywords": ["dmart", "d-mart indira nagar", "d mart"]},
    {"name": "D-Mart Shopping Mall, Gangapur Road", "tag": "Supermarket Hub", "lat": 20.0250, "lon": 73.7380, "keywords": ["dmart gangapur", "d-mart"]},
    {"name": "D-Mart Hypermarket, Nashik Road", "tag": "Supermarket Hub", "lat": 19.9430, "lon": 73.8290, "keywords": ["dmart nashik road", "dmart jail road"]},
    {"name": "Big Bazaar / Smart Bazaar, Nashik Road", "tag": "Shopping Mall", "lat": 19.9510, "lon": 73.8320, "keywords": ["big bazaar", "smart bazaar", "nashik road mall"]},

    # Colleges & Universities
    {"name": "BYK College of Commerce", "tag": "College Campus", "lat": 20.0060, "lon": 73.7630, "keywords": ["byk", "byk college", "commerce college"]},
    {"name": "KTHM College, Gangapur Road", "tag": "College Campus", "lat": 20.0110, "lon": 73.7680, "keywords": ["kthm", "kthm college"]},
    {"name": "RYK Science College, College Road", "tag": "College Campus", "lat": 20.0050, "lon": 73.7640, "keywords": ["ryk", "ryk college", "science college"]},
    {"name": "KK Wagh College of Engineering, Amrutdham", "tag": "Engineering College", "lat": 20.0190, "lon": 73.8340, "keywords": ["kk wagh", "kkwagh", "engineering college"]},
    {"name": "MET Bhujbal Knowledge City, Adgaon", "tag": "University Campus", "lat": 20.0420, "lon": 73.8470, "keywords": ["met", "bhujbal knowledge city"]},
    {"name": "Sandip University Campus, Mahiravani", "tag": "University", "lat": 19.9650, "lon": 73.6550, "keywords": ["sandip", "sandip university", "sandip foundation"]},
    {"name": "NDMVP Dr. Vasantrao Pawar Medical College, Adgaon", "tag": "Medical College", "lat": 20.0350, "lon": 73.8420, "keywords": ["ndmvp", "medical college", "vasantrao pawar"]},
    {"name": "Government Polytechnic Nashik, Samangaon", "tag": "Polytechnic", "lat": 19.9320, "lon": 73.8480, "keywords": ["government polytechnic", "samangaon polytechnic"]},

    # Major Hospitals
    {"name": "Nashik Civil Hospital (District General)", "tag": "Government Hospital", "lat": 19.9945, "lon": 73.7780, "keywords": ["civil hospital", "civil", "district hospital"]},
    {"name": "Wockhardt Super Speciality Hospital, Mumbai Naka", "tag": "Super Speciality", "lat": 19.9850, "lon": 73.7825, "keywords": ["wockhardt", "wockhardt hospital"]},
    {"name": "Apollo Hospitals, Panchavati", "tag": "Multi-Speciality", "lat": 20.0220, "lon": 73.8080, "keywords": ["apollo", "apollo hospital"]},
    {"name": "Sahyadri Super Speciality Hospital, Wadala Naka", "tag": "Super Speciality", "lat": 19.9875, "lon": 73.7950, "keywords": ["sahyadri", "sahyadri hospital"]},
    {"name": "Ashoka Medicover Hospital, Indira Nagar", "tag": "Multi-Speciality", "lat": 19.9640, "lon": 73.7710, "keywords": ["ashoka medicover", "medicover", "ashoka hospital"]},
    {"name": "Six Sigma Hospital, Mahatma Nagar", "tag": "Multi-Speciality", "lat": 20.0020, "lon": 73.7540, "keywords": ["six sigma", "six sigma hospital"]},
    {"name": "Bytco Multi-Speciality Hospital, Nashik Road", "tag": "Municipal Hospital", "lat": 19.9490, "lon": 73.8370, "keywords": ["bytco hospital", "bytco"]},

    # Parks & Recreation
    {"name": "Indira Nagar Jogging Track", "tag": "Park & Track", "lat": 19.9620, "lon": 73.7850, "keywords": ["jogging track", "indira nagar track", "garden"]},
    {"name": "Mahatma Nagar Ground & Garden", "tag": "Sports Ground", "lat": 20.0020, "lon": 73.7550, "keywords": ["mahatma nagar ground", "cricket ground"]},
    {"name": "Golf Club Ground & Public Park", "tag": "Public Ground", "lat": 19.9980, "lon": 73.7680, "keywords": ["golf club", "golf ground"]},
    {"name": "Goda Park & Riverfront Promenade", "tag": "Riverfront Promenade", "lat": 20.0150, "lon": 73.7610, "keywords": ["goda park", "riverfront", "godavari park"]}
]

def search_catalog(query: str, limit: int = 8) -> List[Dict[str, Any]]:
    """Searches the built-in Nashik catalog with substring and token matching."""
    q = query.strip().lower()
    tokens = [t for t in re.split(r"[\s,]+", q) if len(t) >= 2]
    if not tokens:
        return []

    scored_results = []
    for item in NASHIK_CATALOG:
        name_lower = item["name"].lower()
        score = 0

        # Exact phrase in name
        if q in name_lower:
            score += 50

        # Match tokens in name or keywords
        for tok in tokens:
            if tok in name_lower:
                score += 15
            for kw in item.get("keywords", []):
                if tok in kw:
                    score += 10

        if score > 0:
            scored_results.append((score, {
                "name": item["name"],
                "tag": item["tag"],
                "latitude": item["lat"],
                "longitude": item["lon"],
                "source": "verified_landmark"
            }))

    scored_results.sort(key=lambda x: x[0], reverse=True)
    return [r[1] for r in scored_results[:limit]]
