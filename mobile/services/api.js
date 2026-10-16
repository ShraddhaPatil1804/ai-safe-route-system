import axios from 'axios';
import { Platform } from 'react-native';
import storageService from './storage';

// Configurable backend URL: uses EXPO_PUBLIC_API_URL when deploying, or defaults for local dev
export const API_BASE_URL =
  process.env.EXPO_PUBLIC_API_URL ||
  (Platform.OS === 'android' ? 'http://10.0.2.2:8000' : 'http://localhost:8000');

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
});

let authToken = null;

export const setAuthToken = (token) => {
  authToken = token;
  if (token) {
    api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
  } else {
    delete api.defaults.headers.common['Authorization'];
  }
};

export const apiService = {
  // Initialize and restore saved session
  initSession: async () => {
    try {
      const savedToken = await storageService.getToken();
      if (savedToken) {
        setAuthToken(savedToken);
        const profile = await apiService.getProfile();
        await storageService.saveUser(profile);
        return profile;
      }
    } catch (e) {
      console.log('Session restore notice: no active session');
      await storageService.clearAll();
      setAuthToken(null);
    }
    return null;
  },

  // Auth
  signup: async (name, email, password) => {
    const res = await api.post('/auth/signup', { name, email, password });
    if (res.data?.access_token) {
      setAuthToken(res.data.access_token);
      await storageService.saveToken(res.data.access_token);
      if (res.data?.user) {
        await storageService.saveUser(res.data.user);
      }
    }
    return res.data;
  },

  login: async (email, password) => {
    const res = await api.post('/auth/login', { email, password });
    if (res.data?.access_token) {
      setAuthToken(res.data.access_token);
      await storageService.saveToken(res.data.access_token);
      if (res.data?.user) {
        await storageService.saveUser(res.data.user);
      }
    }
    return res.data;
  },

  logout: async () => {
    setAuthToken(null);
    await storageService.clearAll();
  },

  getProfile: async () => {
    const res = await api.get('/auth/me');
    return res.data;
  },

  // Routing
  compareRoutes: async (originLat, originLon, destLat, destLon, timeOfDay = 'day') => {
    const res = await api.get('/routes/compare', {
      params: {
        origin_lat: originLat,
        origin_lon: originLon,
        dest_lat: destLat,
        dest_lon: destLon,
        time_of_day: timeOfDay,
      },
    });
    return res.data;
  },

  getRoute: async (originLat, originLon, destLat, destLon, mode = 'safest', timeOfDay = 'day') => {
    const res = await api.get('/route', {
      params: {
        origin_lat: originLat,
        origin_lon: originLon,
        dest_lat: destLat,
        dest_lon: destLon,
        mode,
        time_of_day: timeOfDay,
      },
    });
    return res.data;
  },

  // POIs
  getPOIs: async (category = null, lat = null, lon = null, radius = 25000) => {
    const params = { limit: 250 };
    if (category && category !== 'all') {
      params.category = category;
    }
    if (lat && lon) {
      params.lat = lat;
      params.lon = lon;
      params.radius_meters = radius;
    }
    const res = await api.get('/pois', { params });
    return res.data;
  },

  getPOICategories: async () => {
    const res = await api.get('/pois/categories');
    return res.data;
  },

  getEmergencyFacilities: async (lat, lon) => {
    const res = await api.get('/pois/emergency', {
      params: { lat, lon },
    });
    return res.data;
  },

  // Safety Heatmap
  getHeatmap: async (minLat = 19.95, minLon = 73.72, maxLat = 20.05, maxLon = 73.85, timeOfDay = 'day') => {
    const res = await api.get('/heatmap', {
      params: { min_lat: minLat, min_lon: minLon, max_lat: maxLat, max_lon: maxLon, limit: 300, time_of_day: timeOfDay },
    });
    return res.data;
  },

  // Places & Geocoding Search
  searchPlaces: async (query, limit = 8) => {
    const res = await api.get('/places/search', {
      params: { q: query, limit },
    });
    return res.data;
  },

  // Reports
  submitReport: async (reportData) => {
    const res = await api.post('/reports', reportData);
    return res.data;
  },

  getReports: async () => {
    const res = await api.get('/reports');
    return res.data;
  },
};

export default apiService;
