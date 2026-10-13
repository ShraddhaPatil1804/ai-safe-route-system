# Nirbhaya Nav - Safety-Aware Navigation System for Women in Nashik

A formula-based, production-grade mobile navigation system built for women in **Nashik, Maharashtra, India**. Inspired by the Google Maps user experience, the app combines real-time GPS tracking, multi-criteria routing, and turn-by-turn voice guidance with transparent road-level safety scoring.

---

## 🌟 Key Features

- **Strictly Formula-Based Safety Engine**:
  - No black-box machine learning or crime datasets.
  - Scores all 137,218 road segments on a transparent 0–100 scale using road lighting hierarchy, natural surveillance (commercial foot traffic), environmental isolation, alcohol venue penalties, and proximity bonuses to emergency facilities.
- **Location-First Google Maps-Style Turn-by-Turn Navigation**:
  - Automatically centers on user's real GPS position.
  - Big turn maneuver cards with countdown distance (*"In 66 m, turn left onto College Road"*).
  - Audible voice announcements (`expo-speech` on mobile, Web Speech API on browser).
  - Live drive simulation mode and next/previous step advancement.
- **Three-Tier Route Hierarchy**:
  - **⚡ Fastest**: Strictly least time along high-speed corridors.
  - **⚖️ Medium (Balanced)**: More safety than fastest, trading a small amount of time to bypass dark or isolated streets.
  - **🛡️ Safest**: Maximum safety score prioritizing street lighting, active commercial avenues, and verified emergency facilities.
- **Universal Nashik Place Search & Geocoding**:
  - Resolves **any** locality, colony, temple, circle, hospital, or street in Nashik (e.g. *Tidke Colony*, *Muktidham*, *Govind Nagar*, *Dwarka Circle*, *Sula Vineyards*, *Kalaram Mandir*, *CCM*).
  - Powered by a 100+ verified Nashik landmarks catalog, 859 PostGIS POIs, named road geometry, and OpenStreetMap live geocoding.
- **859 Verified Safety POIs Across Nashik**:
  - 326 Hospitals, 57 Clinics, 20 Police Stations & Outposts, 19 Shopping Malls, 12 Cafes, 166 Dining & Hospitality venues, 21 Pharmacies.
- **Emergency SOS & Community Reporting**:
  - 1-tap emergency dialer for **112**, **1091** (Women Helpline), **100**, and **108**.
  - Community reporting modal for dark streets, harassment, or isolated hazards.

---

## 🏛️ System Architecture

```
                                  +------------------------------------+
                                  |    Mobile Client (Expo / React Native)
                                  | - Location-First GPS Tracking      |
                                  | - Google Maps Turn-by-Turn HUD    |
                                  | - Voice Guidance (Expo Speech)     |
                                  | - Route Comparison Drawer          |
                                  +-----------------+------------------+
                                                    |
                                          REST APIs (Axios / JSON)
                                                    |
                                  +-----------------v------------------+
                                  |     FastAPI Python Backend         |
                                  | - A* Multi-Criteria Router (NetworkX)|
                                  | - KDTree Spatial Snapping          |
                                  | - Multi-Tier Nashik Place Search   |
                                  | - JWT Authentication & Safety APIs |
                                  +-----------------+------------------+
                                                    |
                                      SQLAlchemy + GeoAlchemy2
                                                    |
                                  +-----------------v------------------+
                                  |   PostgreSQL 16 + PostGIS Spatial  |
                                  | - 137,218 Road Segments with Centroids
                                  | - 52,467 Intersections (Graph Nodes)
                                  | - 859 Verified Nashik POIs (GiST)  |
                                  | - Road Safety Features & Scores    |
                                  +------------------------------------+
```

---

## 🧮 Mathematical Safety Formula

For every road segment $i$, the safety score $S_i \in [0, 100]$ is computed as:

$$S_i = \max\left(0, \min\left(100, 100 - \text{TotalRisk}_i + \text{EmergencyBonus}_i\right)\right)$$

Where:
- $\text{TotalRisk}_i = \text{LightingRisk}_i + \text{IsolationRisk}_i + \text{AlcoholRisk}_i$
- $\text{LightingRisk}_i = 30.0 \times (1.0 - L_i)$ (derived from road hierarchy)
- $\text{IsolationRisk}_i = 15.0 \times \max(0, 1.0 - \text{ActivityCount} / 3.0)$
- $\text{AlcoholRisk}_i = \min(10, 2 \times \text{LiquorShops}) + \min(8, 1.5 \times \text{Bars})$
- $\text{EmergencyBonus}_i = \text{Bonus}_{\text{police}} (\le 8) + \text{Bonus}_{\text{hospital}} (\le 4) + \text{Bonus}_{\text{pharmacy}} (\le 3)$

---

## 🚀 Quick Local Setup

### 1. Prerequisites
- Python 3.10+
- Node.js 18+ and npm
- PostgreSQL 14+ with PostGIS extension enabled

### 2. Backend Setup
```bash
# Clone repository
git clone https://github.com/KhushiNanote/ai-route-system.git
cd ai-route-system

# Create virtual environment
python -m venv venv
source venv/bin/activate    # On Windows: .\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your PostgreSQL credentials

# Start FastAPI server
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```
Swagger API docs available at: `http://localhost:8000/docs`

### 3. Mobile App Setup
```bash
cd mobile

# Install dependencies
npm install

# Start development server
npx expo start --web
```
- Open browser at `http://localhost:8081`
- Or scan QR code using **Expo Go** on Android / iOS.

---

## 📱 Mobile App Deployment Guide

### Option 1: Standalone Android APK (via EAS Build)
EAS Build creates production Android `.apk` files directly in the cloud without needing Android Studio:
```bash
cd mobile

# 1. Install EAS CLI globally
npm install -g eas-cli

# 2. Log in to your Expo account
eas login

# 3. Configure EAS
eas build:configure

# 4. Build standalone Android APK
eas build -p android --profile preview
```
Once the cloud build completes, EAS outputs a direct download link for the `.apk` file that can be installed on any Android phone.

### Option 2: Google Play Store AAB
```bash
cd mobile
eas build -p android --profile production
```

### Option 3: Web Production Export
```bash
cd mobile
npx expo export -p web
```
The output in `mobile/dist/` can be deployed directly to **Vercel**, **Netlify**, or **GitHub Pages**.

---

## ☁️ Backend Cloud Deployment

### Docker Deployment
```bash
# Start PostGIS and FastAPI backend in one command
docker compose up -d --build
```

### Deploy to Render / Railway / AWS EC2
1. Deploy `Dockerfile` as a Web Service.
2. Set Environment Variables:
   - `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`
   - `SECRET_KEY`
3. Point your mobile app's `EXPO_PUBLIC_API_URL` to your live backend domain (e.g. `https://api.nirbhayanav.in`).

---

## 🧪 Automated Testing

Run the end-to-end API test suite:
```bash
python -u scripts/test_api.py
```

Test universal place search and route resolution across Nashik:
```bash
python -u scripts/test_any_input.py
```

---

## 📄 License
MIT License. Built for women's safety in Nashik, Maharashtra, India.
