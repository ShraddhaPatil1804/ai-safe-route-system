import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  TextInput,
  ScrollView,
  ActivityIndicator,
  Alert,
  SafeAreaView,
  StatusBar,
  Modal,
} from 'react-native';
import * as Location from 'expo-location';

import apiService from '../services/api';
import voiceService from '../services/voice';
import MapViewComponent from '../components/MapViewComponent';
import POIFilterBar from '../components/POIFilterBar';
import RouteComparisonCard from '../components/RouteComparisonCard';
import NavigationOverlay from '../components/NavigationOverlay';
import EmergencyModal from '../components/EmergencyModal';
import ReportModal from '../components/ReportModal';
import AuthModal from './AuthModal';

// Starting hubs in Nashik for testing/simulation
const NASHIK_HUBS = [
  { name: '📍 Live GPS Location', isGps: true },
  { name: '🚉 Nashik Road Station', lat: 19.953, lon: 73.834 },
  { name: '🏫 College Road (BYK)', lat: 20.005, lon: 73.765 },
  { name: '🛕 Panchavati (Ramkund)', lat: 20.008, lon: 73.793 },
  { name: '🏛️ Indira Nagar', lat: 19.965, lon: 73.775 },
];

export default function MapScreen() {
  // Real GPS & Origin state
  const [realGpsLocation, setRealGpsLocation] = useState(null);
  const [userLocation, setUserLocation] = useState({
    latitude: 19.953,
    longitude: 73.834, // Default hub in Nashik
  });
  const [selectedOriginLocation, setSelectedOriginLocation] = useState({
    latitude: 19.953,
    longitude: 73.834,
  });
  const [originName, setOriginName] = useState('Your Current Location');
  const [locLoading, setLocLoading] = useState(true);
  const [showOriginModal, setShowOriginModal] = useState(false);

  // Destination & search
  const [destination, setDestination] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [showDestList, setShowDestList] = useState(false);
  const [searchResults, setSearchResults] = useState([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [selectedPlaceInfo, setSelectedPlaceInfo] = useState(null);

  // Region
  const [region, setRegion] = useState({
    latitude: 19.985,
    longitude: 73.795,
    latitudeDelta: 0.09,
    longitudeDelta: 0.09,
  });

  // Routing & Time-of-Day
  const [comparisonData, setComparisonData] = useState(null);
  const [selectedMode, setSelectedMode] = useState('safest');
  const [timeOfDay, setTimeOfDay] = useState('day');
  const [calculatingRoutes, setCalculatingRoutes] = useState(false);

  // Turn-by-Turn Navigation state
  const [isNavigating, setIsNavigating] = useState(false);
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [isSimulating, setIsSimulating] = useState(false);

  // POIs & Heatmap
  const [pois, setPois] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [selectedPoi, setSelectedPoi] = useState(null);
  const [showHeatmap, setShowHeatmap] = useState(false);
  const [heatmapData, setHeatmapData] = useState(null);

  // Modals & Auth Session
  const [emergencyVisible, setEmergencyVisible] = useState(false);
  const [reportVisible, setReportVisible] = useState(false);
  const [authVisible, setAuthVisible] = useState(false);
  const [authModalMode, setAuthModalMode] = useState('login');
  const [currentUser, setCurrentUser] = useState(null);

  const openAuth = (mode = 'login') => {
    setAuthModalMode(mode);
    setAuthVisible(true);
  };

  const mapRef = useRef(null);
  const simIntervalRef = useRef(null);

  useEffect(() => {
    fetchInitialUserLocation();
    loadPOIs('all');
    restoreUserSession();

    return () => {
      if (simIntervalRef.current) clearInterval(simIntervalRef.current);
    };
  }, []);

  const restoreUserSession = async () => {
    try {
      const user = await apiService.initSession();
      if (user) {
        setCurrentUser(user);
      }
    } catch (e) {
      console.log('Session check notice:', e);
    }
  };

  // Live Nashik Place Geocoding & Search Debounce
  useEffect(() => {
    const q = searchQuery ? searchQuery.trim() : '';
    if (!q || q.length < 2) {
      setSearchResults([]);
      setSearchLoading(false);
      return;
    }

    const timer = setTimeout(async () => {
      try {
        setSearchLoading(true);
        const data = await apiService.searchPlaces(q, 10);
        setSearchResults(data || []);
      } catch (e) {
        console.log('Nashik place search warning:', e);
      } finally {
        setSearchLoading(false);
      }
    }, 300);

    return () => clearTimeout(timer);
  }, [searchQuery]);

  const fetchInitialUserLocation = async () => {
    try {
      setLocLoading(true);
      const { status } = await Location.requestForegroundPermissionsAsync();
      if (status === 'granted') {
        const loc = await Location.getCurrentPositionAsync({
          accuracy: Location.Accuracy.Balanced,
        });
        const coords = { latitude: loc.coords.latitude, longitude: loc.coords.longitude };
        setRealGpsLocation(coords);

        const inNashik =
          coords.latitude >= 19.5 && coords.latitude <= 20.5 &&
          coords.longitude >= 73.0 && coords.longitude <= 74.5;

        if (inNashik) {
          setUserLocation(coords);
          setSelectedOriginLocation(coords);
          setOriginName('📍 Your Current GPS Location');
          setRegion({ ...coords, latitudeDelta: 0.05, longitudeDelta: 0.05 });
        } else {
          setOriginName('📍 Nashik Road Station (Demo Origin)');
        }
      }
    } catch (e) {
      console.log('Location fetch note:', e);
    } finally {
      setLocLoading(false);
    }
  };

  const handleCurrentLocationPress = async () => {
    try {
      const { status } = await Location.requestForegroundPermissionsAsync();
      if (status !== 'granted') {
        Alert.alert(
          'Location Permission Needed',
          'Please enable location permissions in settings so the app can locate your position in Nashik.'
        );
        return;
      }
      const loc = await Location.getCurrentPositionAsync({
        accuracy: Location.Accuracy.High,
      });
      const coords = { latitude: loc.coords.latitude, longitude: loc.coords.longitude };
      setRealGpsLocation(coords);
      setUserLocation(coords);
      setSelectedOriginLocation(coords);
      setOriginName('📍 Your Current GPS Location');

      if (mapRef.current) {
        mapRef.current.animateToRegion({
          ...coords,
          latitudeDelta: 0.02,
          longitudeDelta: 0.02,
        }, 500);
      }
    } catch (e) {
      Alert.alert('GPS Notice', 'Unable to retrieve your current location. Please verify device GPS is active.');
    }
  };

  const handleSelectOriginHub = (hub) => {
    setShowOriginModal(false);
    let originCoords = null;
    if (hub.isGps && realGpsLocation) {
      originCoords = realGpsLocation;
      setOriginName('📍 Live GPS Location');
    } else if (hub.lat && hub.lon) {
      originCoords = { latitude: hub.lat, longitude: hub.lon };
      setOriginName(hub.name);
    }
    if (originCoords) {
      setUserLocation(originCoords);
      setSelectedOriginLocation(originCoords);
      if (destination) {
        calculateRoutes(originCoords, destination);
      } else if (mapRef.current) {
        mapRef.current.animateToRegion({
          ...originCoords,
          latitudeDelta: 0.05,
          longitudeDelta: 0.05,
        }, 500);
      }
    }
  };

  const loadPOIs = async (category = 'all') => {
    try {
      const data = await apiService.getPOIs(
        category === 'all' ? null : category,
        userLocation.latitude,
        userLocation.longitude,
        25000
      );
      setPois(data || []);
    } catch (e) {
      console.warn('POIs fetch warning:', e);
      setPois([]);
    }
  };

  const handleSelectCategory = (cat) => {
    setSelectedCategory(cat);
    setSelectedPoi(null);
    loadPOIs(cat);
  };

  const handleToggleHeatmap = async () => {
    const next = !showHeatmap;
    setShowHeatmap(next);
    if (next && !heatmapData) {
      try {
        const data = await apiService.getHeatmap();
        setHeatmapData(data);
      } catch (e) {
        console.warn('Heatmap load warning:', e);
      }
    }
  };

  // When a search result is selected: auto-routes to that destination directly
  const handleSelectSearchResult = (place) => {
    const coords = {
      latitude: place.latitude !== undefined ? place.latitude : place.lat,
      longitude: place.longitude !== undefined ? place.longitude : place.lon,
    };

    setShowDestList(false);
    setSelectedPoi(null);
    setSelectedPlaceInfo(null);
    handleSetPlaceAsDestination(coords, place.name);
  };

  // Use place as navigation destination
  const handleSetPlaceAsDestination = (placeCoords, placeName) => {
    setDestination(placeCoords);
    setSearchQuery(placeName || `Destination (${placeCoords.latitude.toFixed(3)}, ${placeCoords.longitude.toFixed(3)})`);
    setSelectedPlaceInfo(null);
    setSelectedPoi(null);
    setUserLocation(selectedOriginLocation);
    calculateRoutes(selectedOriginLocation, placeCoords);
  };

  const handleSelectMarker = (poi) => {
    setComparisonData(null);
    setSelectedPlaceInfo(null);
    setSelectedPoi(poi);
  };

  const handleMapPress = (coords) => {
    if (!isNavigating) {
      setComparisonData(null);
      setSelectedPlaceInfo({
        name: `Pinned Location (${coords.latitude.toFixed(3)}, ${coords.longitude.toFixed(3)})`,
        tag: 'Map Pin',
        address: 'Nashik, Maharashtra',
        latitude: coords.latitude,
        longitude: coords.longitude,
      });
      setSelectedPoi(null);
    }
  };

  const calculateRoutes = async (originCoords, destCoords, overrideTimeOfDay = null) => {
    try {
      setCalculatingRoutes(true);
      setComparisonData(null);
      const activeTime = overrideTimeOfDay || timeOfDay;
      const res = await apiService.compareRoutes(
        originCoords.latitude,
        originCoords.longitude,
        destCoords.latitude,
        destCoords.longitude,
        activeTime
      );
      setComparisonData(res);
      setSelectedMode('safest');
      setCurrentStepIndex(0);

      const safest = res.safest;
      if (safest) {
        voiceService.speak(
          `Safest ${activeTime === 'night' ? 'night-time' : 'daytime'} route found to destination. Estimated travel time ${safest.estimated_time_minutes} minutes, safety score ${safest.safety_score} out of 100.`
        );
      }
    } catch (e) {
      setComparisonData(null);
      Alert.alert('Route Error', 'Could not calculate routes. Please verify destination.');
    } finally {
      setCalculatingRoutes(false);
    }
  };

  const toggleTimeOfDay = () => {
    const nextTime = timeOfDay === 'day' ? 'night' : 'day';
    setTimeOfDay(nextTime);
    if (destination) {
      calculateRoutes(userLocation, destination, nextTime);
    }
  };

  // Turn-by-Turn Navigation Controls
  const handleStartNavigation = (activeRoute) => {
    setIsNavigating(true);
    setCurrentStepIndex(0);
    const steps = activeRoute?.steps || [];
    if (steps.length > 0) {
      voiceService.speak(`Navigation started. ${steps[0].instruction}. Follow the green safety-verified corridor.`);
    }
  };

  const handleExitNavigation = () => {
    setIsNavigating(false);
    setIsSimulating(false);
    if (simIntervalRef.current) clearInterval(simIntervalRef.current);
    voiceService.stop();
    setUserLocation(selectedOriginLocation);
  };

  const handleNextStep = () => {
    const activeRoute = comparisonData?.[selectedMode] || comparisonData?.safest;
    const steps = activeRoute?.steps || [];
    if (currentStepIndex < steps.length - 1) {
      const nextIdx = currentStepIndex + 1;
      setCurrentStepIndex(nextIdx);
      const stepCoords = steps[nextIdx]?.coordinates;
      if (stepCoords && stepCoords.length > 0) {
        setUserLocation({
          latitude: stepCoords[0][1],
          longitude: stepCoords[0][0],
        });
      }
    }
  };

  const handlePrevStep = () => {
    if (currentStepIndex > 0) {
      const prevIdx = currentStepIndex - 1;
      setCurrentStepIndex(prevIdx);
      const activeRoute = comparisonData?.[selectedMode] || comparisonData?.safest;
      const stepCoords = activeRoute?.steps?.[prevIdx]?.coordinates;
      if (stepCoords && stepCoords.length > 0) {
        setUserLocation({
          latitude: stepCoords[0][1],
          longitude: stepCoords[0][0],
        });
      }
    }
  };

  const handleToggleSimulation = () => {
    if (isSimulating) {
      setIsSimulating(false);
      if (simIntervalRef.current) clearInterval(simIntervalRef.current);
    } else {
      setIsSimulating(true);
      const activeRoute = comparisonData?.[selectedMode] || comparisonData?.safest;
      const steps = activeRoute?.steps || [];
      if (steps.length === 0) return;

      let idx = currentStepIndex;
      simIntervalRef.current = setInterval(() => {
        idx += 1;
        if (idx < steps.length) {
          setCurrentStepIndex(idx);
          const stepCoords = steps[idx]?.coordinates;
          if (stepCoords && stepCoords.length > 0) {
            setUserLocation({
              latitude: stepCoords[0][1],
              longitude: stepCoords[0][0],
            });
          }
        } else {
          clearInterval(simIntervalRef.current);
          setIsSimulating(false);
          voiceService.speak('You have reached your destination. Navigation completed.');
        }
      }, 5000);
    }
  };

  const recenter = () => {
    if (mapRef.current) {
      mapRef.current.animateToRegion({
        ...userLocation,
        latitudeDelta: 0.03,
        longitudeDelta: 0.03,
      }, 600);
    }
  };

  const activeRoute = comparisonData ? comparisonData[selectedMode] : null;
  const currentStep = activeRoute?.steps?.[currentStepIndex];
  const activeStepCoords = currentStep?.coordinates || [];

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="dark-content" backgroundColor="#FFFFFF" />

      {/* Map Component */}
      <MapViewComponent
        mapRef={mapRef}
        region={region}
        onRegionChangeComplete={setRegion}
        onMapPress={handleMapPress}
        userLocation={userLocation}
        destination={destination}
        comparisonData={comparisonData}
        selectedMode={selectedMode}
        pois={pois}
        selectedPoi={selectedPoi || selectedPlaceInfo}
        onSelectPOI={handleSelectMarker}
        showHeatmap={showHeatmap}
        heatmapData={heatmapData}
        activeStepCoords={activeStepCoords}
        isNavigating={isNavigating}
      />

      {/* Navigation HUD Overlay */}
      {isNavigating && activeRoute ? (
        <NavigationOverlay
          route={activeRoute}
          currentStepIndex={currentStepIndex}
          onNextStep={handleNextStep}
          onPrevStep={handlePrevStep}
          onExitNavigation={handleExitNavigation}
          isSimulating={isSimulating}
          onToggleSimulation={handleToggleSimulation}
          totalDistanceKm={activeRoute.distance_km}
          totalMinutes={activeRoute.estimated_time_minutes}
        />
      ) : (
        /* Regular Map Exploration View */
        <>
          <View style={styles.topContainer}>
            {/* Top Bar: Origin pill, Day/Night toggle, and Auth buttons/profile */}
            <View style={styles.topBarRow}>
              <View style={styles.topLeftGroup}>
                <TouchableOpacity
                  style={styles.originPill}
                  onPress={() => setShowOriginModal(true)}
                  activeOpacity={0.7}
                >
                  <Text style={styles.originPillText} numberOfLines={1}>
                    {locLoading
                      ? '📡 Locating GPS...'
                      : `🟢 From: ${originName} ▾`}
                  </Text>
                </TouchableOpacity>

                {/* Day / Night Departure Selector */}
                <TouchableOpacity
                  style={[
                    styles.timeTogglePill,
                    timeOfDay === 'night' && styles.timeTogglePillNight,
                  ]}
                  onPress={toggleTimeOfDay}
                  activeOpacity={0.8}
                >
                  <Text
                    style={[
                      styles.timeTogglePillText,
                      timeOfDay === 'night' && styles.timeTogglePillTextNight,
                    ]}
                  >
                    {timeOfDay === 'night' ? '🌙 Night' : '☀️ Day'}
                  </Text>
                </TouchableOpacity>
              </View>

              {currentUser ? (
                <TouchableOpacity
                  style={styles.userProfilePill}
                  onPress={() => openAuth('login')}
                  activeOpacity={0.8}
                >
                  <Text style={styles.userProfilePillText}>👤 {currentUser.name || 'Account'}</Text>
                </TouchableOpacity>
              ) : (
                <View style={styles.authButtonsRow}>
                  <TouchableOpacity
                    style={styles.signInButton}
                    onPress={() => openAuth('login')}
                    activeOpacity={0.8}
                  >
                    <Text style={styles.signInButtonText}>Sign In</Text>
                  </TouchableOpacity>
                  <TouchableOpacity
                    style={styles.signUpButton}
                    onPress={() => openAuth('signup')}
                    activeOpacity={0.8}
                  >
                    <Text style={styles.signUpButtonText}>Register</Text>
                  </TouchableOpacity>
                </View>
              )}
            </View>

            {/* Google Maps Style Location Search Bar */}
            <View style={styles.searchBarWrapper}>
              <Text style={styles.searchIcon}>🔍</Text>
              <TextInput
                style={styles.searchInput}
                placeholder="Search places, roads, landmarks in Nashik..."
                placeholderTextColor="#6B7280"
                value={searchQuery}
                returnKeyType="search"
                onSubmitEditing={() => {
                  if (searchResults.length > 0) {
                    handleSelectSearchResult(searchResults[0]);
                  }
                }}
                onFocus={() => setShowDestList(true)}
                onChangeText={(text) => {
                  setSearchQuery(text);
                  setShowDestList(true);
                }}
              />
              {searchLoading ? (
                <ActivityIndicator size="small" color="#6C4AB6" style={{ marginRight: 6 }} />
              ) : null}
              {searchQuery ? (
                <TouchableOpacity onPress={() => { setSearchQuery(''); setDestination(null); setComparisonData(null); setSearchResults([]); setSelectedPlaceInfo(null); setUserLocation(selectedOriginLocation); }}>
                  <Text style={styles.clearSearchIcon}>✕</Text>
                </TouchableOpacity>
              ) : null}
              <TouchableOpacity style={styles.profileBtn} onPress={() => openAuth('login')}>
                <Text style={styles.profileIcon}>{currentUser ? '👤' : '🔑'}</Text>
              </TouchableOpacity>
            </View>

            {/* POI Filter Chips Directly Below Search Bar */}
            <POIFilterBar
              selectedCategory={selectedCategory}
              onSelectCategory={handleSelectCategory}
              showHeatmap={showHeatmap}
              onToggleHeatmap={handleToggleHeatmap}
            />

            {/* Empty State Banner when category has 0 locations */}
            {selectedCategory !== 'all' && pois.length === 0 && (
              <View style={styles.emptyCategoryBanner}>
                <Text style={styles.emptyCategoryText}>
                  ℹ️ No locations found for "{selectedCategory.replace('_', ' ').toUpperCase()}" in Nashik.
                </Text>
              </View>
            )}

            {/* Suggested Destinations Dropdown */}
            {showDestList && (
              <View style={styles.destDropdown}>
                <Text style={styles.destDropdownHeader}>
                  {searchResults.length > 0
                    ? `Matching Places in Nashik (${searchResults.length})`
                    : 'Popular Destinations in Nashik'}
                </Text>

                <ScrollView style={{ maxHeight: 240 }} keyboardShouldPersistTaps="handled">
                  {searchResults.length > 0 ? (
                    searchResults.map((d, i) => (
                      <TouchableOpacity
                        key={`res-${i}`}
                        style={styles.destItem}
                        onPress={() => handleSelectSearchResult(d)}
                      >
                        <Text style={styles.destItemIcon}>📍</Text>
                        <View style={{ flex: 1 }}>
                          <Text style={styles.destItemName} numberOfLines={1}>{d.name}</Text>
                          <Text style={styles.destItemTag}>{d.tag || 'Location'}</Text>
                        </View>
                      </TouchableOpacity>
                    ))
                  ) : (
                    NASHIK_HUBS.filter(h => !h.isGps).map((h, i) => (
                      <TouchableOpacity
                        key={`hub-${i}`}
                        style={styles.destItem}
                        onPress={() => handleSelectSearchResult(h)}
                      >
                        <Text style={styles.destItemIcon}>📍</Text>
                        <View style={{ flex: 1 }}>
                          <Text style={styles.destItemName}>{h.name}</Text>
                          <Text style={styles.destItemTag}>Transit Landmark</Text>
                        </View>
                      </TouchableOpacity>
                    ))
                  )}
                </ScrollView>
              </View>
            )}
          </View>

          {/* Floating Action Buttons */}
          <View style={[styles.fabColumn, comparisonData ? styles.fabColumnWithRoutes : null]}>
            {/* SOS / Emergency */}
            <TouchableOpacity
              style={[styles.fabBtn, styles.sosFab]}
              onPress={() => setEmergencyVisible(true)}
              activeOpacity={0.8}
            >
              <Text style={styles.fabEmoji}>🚨</Text>
              <Text style={styles.sosFabLabel}>SOS</Text>
            </TouchableOpacity>

            {/* Day / Night Quick Toggle FAB */}
            <TouchableOpacity
              style={[styles.fabBtn, timeOfDay === 'night' ? styles.nightFab : styles.dayFab]}
              onPress={toggleTimeOfDay}
              activeOpacity={0.8}
            >
              <Text style={styles.fabEmoji}>{timeOfDay === 'night' ? '🌙' : '☀️'}</Text>
            </TouchableOpacity>

            {/* Zoom In & Zoom Out Controls */}
            <View style={styles.zoomPill}>
              <TouchableOpacity
                style={styles.zoomBtn}
                onPress={() => mapRef.current?.zoomIn && mapRef.current.zoomIn()}
                activeOpacity={0.7}
              >
                <Text style={styles.zoomBtnText}>＋</Text>
              </TouchableOpacity>
              <View style={styles.zoomDivider} />
              <TouchableOpacity
                style={styles.zoomBtn}
                onPress={() => mapRef.current?.zoomOut && mapRef.current.zoomOut()}
                activeOpacity={0.7}
              >
                <Text style={styles.zoomBtnText}>−</Text>
              </TouchableOpacity>
            </View>

            {/* Report Safety Hazard */}
            <TouchableOpacity
              style={[styles.fabBtn, styles.reportFab]}
              onPress={() => setReportVisible(true)}
              activeOpacity={0.8}
            >
              <Text style={styles.fabEmoji}>⚠️</Text>
            </TouchableOpacity>

            {/* Current Location GPS Button */}
            <TouchableOpacity
              style={[styles.fabBtn, styles.currentLocFab]}
              onPress={handleCurrentLocationPress}
              activeOpacity={0.8}
            >
              <Text style={styles.fabEmoji}>📍</Text>
            </TouchableOpacity>

            {/* Recenter */}
            <TouchableOpacity
              style={[styles.fabBtn, styles.recenterFab]}
              onPress={recenter}
              activeOpacity={0.8}
            >
              <Text style={styles.fabEmoji}>🎯</Text>
            </TouchableOpacity>
          </View>

          {/* Calculating Loading Banner */}
          {calculatingRoutes && (
            <View style={styles.loadingBanner}>
              <ActivityIndicator color="#FFFFFF" size="small" />
              <Text style={styles.loadingText}>Computing Safest, Fastest & Balanced routes...</Text>
            </View>
          )}

          {/* Selected Place / Marker Details Card */}
          {(selectedPlaceInfo || selectedPoi) && !comparisonData && (
            <View style={styles.placeCardContainer}>
              {(() => {
                const item = selectedPlaceInfo || selectedPoi;
                const lat = item.latitude;
                const lon = item.longitude;
                const name = item.name || 'Selected Location';
                const tag = item.tag || item.category?.replace('_', ' ').toUpperCase() || 'Place';
                const distText = item.distance_meters
                  ? `${(item.distance_meters / 1000).toFixed(1)} km away`
                  : null;

                return (
                  <View style={styles.placeCard}>
                    <View style={styles.placeCardHeader}>
                      <View style={{ flex: 1 }}>
                        <Text style={styles.placeCardTitle} numberOfLines={1}>{name}</Text>
                        <Text style={styles.placeCardTag}>{tag}{distText ? ` • ${distText}` : ''}</Text>
                        {item.address ? (
                          <Text style={styles.placeCardAddress} numberOfLines={2}>{item.address}</Text>
                        ) : null}
                      </View>
                      <TouchableOpacity
                        style={styles.placeCardClose}
                        onPress={() => { setSelectedPlaceInfo(null); setSelectedPoi(null); }}
                      >
                        <Text style={styles.placeCardCloseText}>✕</Text>
                      </TouchableOpacity>
                    </View>

                    <TouchableOpacity
                      style={styles.navigateBtn}
                      onPress={() => handleSetPlaceAsDestination({ latitude: lat, longitude: lon }, name)}
                      activeOpacity={0.85}
                    >
                      <Text style={styles.navigateBtnText}>🧭 Set as Destination & Route</Text>
                    </TouchableOpacity>
                  </View>
                );
              })()}
            </View>
          )}

          {/* Floating Route Legend Bar */}
          {comparisonData && (
            <View style={styles.routeLegendContainer}>
              <TouchableOpacity
                style={[styles.legendPill, selectedMode === 'safest' && styles.legendPillActiveSafest]}
                onPress={() => setSelectedMode('safest')}
                activeOpacity={0.8}
              >
                <View style={[styles.legendColorDot, { backgroundColor: '#10B981' }]} />
                <Text style={[styles.legendText, selectedMode === 'safest' && styles.legendTextActive]}>🛡️ Safest</Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={[styles.legendPill, selectedMode === 'fastest' && styles.legendPillActiveFastest]}
                onPress={() => setSelectedMode('fastest')}
                activeOpacity={0.8}
              >
                <View style={[styles.legendColorDot, { backgroundColor: '#3B82F6' }]} />
                <Text style={[styles.legendText, selectedMode === 'fastest' && styles.legendTextActive]}>⚡ Fastest</Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={[styles.legendPill, selectedMode === 'balanced' && styles.legendPillActiveBalanced]}
                onPress={() => setSelectedMode('balanced')}
                activeOpacity={0.8}
              >
                <View style={[styles.legendColorDot, { backgroundColor: '#6C4AB6' }]} />
                <Text style={[styles.legendText, selectedMode === 'balanced' && styles.legendTextActive]}>⚖️ Balanced</Text>
              </TouchableOpacity>
            </View>
          )}

          {/* Bottom Route Comparison Card */}
          {comparisonData && (
            <View style={styles.bottomDrawer}>
              <RouteComparisonCard
                comparisonData={comparisonData}
                selectedMode={selectedMode}
                onSelectMode={setSelectedMode}
                onStartNavigation={handleStartNavigation}
                timeOfDay={timeOfDay}
                onClose={() => {
                  setComparisonData(null);
                  setDestination(null);
                  setSearchQuery('');
                  setUserLocation(selectedOriginLocation);
                }}
              />
            </View>
          )}
        </>
      )}

      {/* Modals */}
      <EmergencyModal
        visible={emergencyVisible}
        onClose={() => setEmergencyVisible(false)}
        userCoords={userLocation}
        onNavigateTo={(facility) => {
          handleSetPlaceAsDestination({
            latitude: facility.latitude,
            longitude: facility.longitude,
          }, facility.name);
        }}
      />

      <ReportModal
        visible={reportVisible}
        onClose={() => setReportVisible(false)}
        userCoords={userLocation}
      />

      <AuthModal
        visible={authVisible}
        onClose={() => setAuthVisible(false)}
        currentUser={currentUser}
        initialMode={authModalMode}
        onAuthSuccess={(u) => setCurrentUser(u)}
        onLogout={() => setCurrentUser(null)}
      />

      {/* Origin Selection Modal */}
      <Modal
        visible={showOriginModal}
        transparent={true}
        animationType="fade"
        onRequestClose={() => setShowOriginModal(false)}
      >
        <TouchableOpacity
          style={styles.modalOverlay}
          activeOpacity={1}
          onPress={() => setShowOriginModal(false)}
        >
          <View style={styles.originModalBox}>
            <Text style={styles.originModalTitle}>Select Starting Location (Origin)</Text>
            <Text style={styles.originModalSubtitle}>Choose starting location for route comparison:</Text>
            {NASHIK_HUBS.map((hub, idx) => (
              <TouchableOpacity
                key={`origin-hub-${idx}`}
                style={[
                  styles.originHubOption,
                  originName === hub.name && styles.originHubOptionSelected,
                ]}
                onPress={() => handleSelectOriginHub(hub)}
              >
                <Text style={styles.originHubOptionText}>{hub.name}</Text>
                {originName === hub.name && <Text style={styles.originHubCheckmark}>✓</Text>}
              </TouchableOpacity>
            ))}
            <TouchableOpacity
              style={styles.originModalCloseBtn}
              onPress={() => setShowOriginModal(false)}
            >
              <Text style={styles.originModalCloseBtnText}>Close</Text>
            </TouchableOpacity>
          </View>
        </TouchableOpacity>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F8F7FF',
  },
  topContainer: {
    position: 'absolute',
    top: 10,
    left: 12,
    right: 12,
    zIndex: 20,
  },
  topBarRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 6,
  },
  topLeftGroup: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    maxWidth: '65%',
  },
  originPill: {
    backgroundColor: '#4E3486',
    paddingHorizontal: 12,
    paddingVertical: 5,
    borderRadius: 14,
    maxWidth: '75%',
    shadowColor: '#4E3486',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.2,
    shadowRadius: 3,
    elevation: 3,
  },
  originPillText: {
    color: '#F8F7FF',
    fontSize: 11,
    fontWeight: '700',
  },
  timeTogglePill: {
    backgroundColor: '#EDE9FE',
    paddingHorizontal: 9,
    paddingVertical: 5,
    borderRadius: 14,
    borderWidth: 1.5,
    borderColor: '#C4B5FD',
    shadowColor: '#6C4AB6',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.15,
    shadowRadius: 2,
    elevation: 2,
  },
  timeTogglePillNight: {
    backgroundColor: '#1E1B4B',
    borderColor: '#6C4AB6',
  },
  timeTogglePillText: {
    fontSize: 10.5,
    fontWeight: '800',
    color: '#6C4AB6',
  },
  timeTogglePillTextNight: {
    color: '#FBBF24',
  },
  authButtonsRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  signInButton: {
    backgroundColor: '#FFFFFF',
    borderWidth: 1.5,
    borderColor: '#6C4AB6',
    paddingHorizontal: 11,
    paddingVertical: 5,
    borderRadius: 14,
    shadowColor: '#6C4AB6',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.12,
    shadowRadius: 3,
    elevation: 2,
  },
  signInButtonText: {
    color: '#6C4AB6',
    fontSize: 11,
    fontWeight: '800',
  },
  signUpButton: {
    backgroundColor: '#6C4AB6',
    paddingHorizontal: 12,
    paddingVertical: 5,
    borderRadius: 14,
    shadowColor: '#6C4AB6',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 3,
    elevation: 3,
  },
  signUpButtonText: {
    color: '#FFFFFF',
    fontSize: 11,
    fontWeight: '800',
  },
  userProfilePill: {
    backgroundColor: '#F5F3FF',
    borderWidth: 1.5,
    borderColor: '#8D72E1',
    paddingHorizontal: 12,
    paddingVertical: 5,
    borderRadius: 14,
    shadowColor: '#6C4AB6',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.15,
    shadowRadius: 3,
    elevation: 2,
  },
  userProfilePillText: {
    color: '#4E3486',
    fontSize: 11,
    fontWeight: '800',
  },
  searchBarWrapper: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#FFFFFF',
    borderRadius: 24,
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderWidth: 1.5,
    borderColor: '#EDE9FE',
    shadowColor: '#6C4AB6',
    shadowOffset: { width: 0, height: 3 },
    shadowOpacity: 0.15,
    shadowRadius: 8,
    elevation: 5,
  },
  searchIcon: {
    fontSize: 16,
    marginRight: 8,
  },
  searchInput: {
    flex: 1,
    fontSize: 14,
    color: '#1E1B4B',
  },
  clearSearchIcon: {
    fontSize: 16,
    color: '#8D72E1',
    paddingHorizontal: 6,
  },
  profileBtn: {
    marginLeft: 6,
    padding: 4,
  },
  profileIcon: {
    fontSize: 20,
  },
  emptyCategoryBanner: {
    backgroundColor: '#F5F3FF',
    borderColor: '#C4B5FD',
    borderWidth: 1.5,
    borderRadius: 16,
    paddingVertical: 6,
    paddingHorizontal: 12,
    marginTop: 4,
  },
  emptyCategoryText: {
    fontSize: 11,
    color: '#6C4AB6',
    fontWeight: '700',
  },
  destDropdown: {
    backgroundColor: '#FFFFFF',
    borderRadius: 20,
    marginTop: 6,
    padding: 10,
    borderWidth: 1.5,
    borderColor: '#EDE9FE',
    shadowColor: '#4E3486',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.18,
    shadowRadius: 10,
    elevation: 6,
  },
  destDropdownHeader: {
    fontSize: 12,
    fontWeight: '800',
    color: '#6C4AB6',
    paddingHorizontal: 6,
    paddingBottom: 6,
    borderBottomWidth: 1,
    borderBottomColor: '#F5F3FF',
    marginBottom: 4,
  },
  destItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 9,
    paddingHorizontal: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#F8F7FF',
  },
  destItemIcon: {
    fontSize: 16,
    marginRight: 10,
  },
  destItemName: {
    fontSize: 13,
    fontWeight: '700',
    color: '#1E1B4B',
  },
  destItemTag: {
    fontSize: 11,
    color: '#8D72E1',
    marginTop: 1,
  },
  fabColumn: {
    position: 'absolute',
    right: 14,
    bottom: 90,
    gap: 10,
    alignItems: 'center',
    zIndex: 15,
  },
  fabBtn: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: '#FFFFFF',
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: '#4E3486',
    shadowOffset: { width: 0, height: 3 },
    shadowOpacity: 0.2,
    shadowRadius: 5,
    elevation: 5,
    borderWidth: 1,
    borderColor: '#EDE9FE',
  },
  sosFab: {
    backgroundColor: '#DC2626',
    borderColor: '#B91C1C',
    width: 52,
    height: 52,
    borderRadius: 26,
  },
  sosFabLabel: {
    fontSize: 9,
    fontWeight: '900',
    color: '#FFFFFF',
    marginTop: -2,
  },
  dayFab: {
    backgroundColor: '#FFFBEB',
    borderColor: '#F59E0B',
  },
  nightFab: {
    backgroundColor: '#1E1B4B',
    borderColor: '#6C4AB6',
  },
  reportFab: {
    backgroundColor: '#F5F3FF',
    borderColor: '#8D72E1',
  },
  currentLocFab: {
    backgroundColor: '#F5F3FF',
    borderColor: '#8D72E1',
    borderWidth: 1.5,
  },
  recenterFab: {
    backgroundColor: '#FFFFFF',
  },
  fabEmoji: {
    fontSize: 20,
  },
  loadingBanner: {
    position: 'absolute',
    top: 130,
    alignSelf: 'center',
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#4E3486',
    paddingHorizontal: 16,
    paddingVertical: 9,
    borderRadius: 20,
    gap: 8,
    zIndex: 25,
    shadowColor: '#4E3486',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.3,
    shadowRadius: 4,
    elevation: 4,
  },
  loadingText: {
    color: '#FFFFFF',
    fontSize: 12,
    fontWeight: '700',
  },
  placeCardContainer: {
    position: 'absolute',
    bottom: 24,
    left: 14,
    right: 14,
    zIndex: 25,
  },
  placeCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 22,
    padding: 16,
    shadowColor: '#4E3486',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.18,
    shadowRadius: 10,
    elevation: 8,
    borderWidth: 1.5,
    borderColor: '#EDE9FE',
  },
  placeCardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 12,
  },
  placeCardTitle: {
    fontSize: 16,
    fontWeight: '800',
    color: '#1E1B4B',
  },
  placeCardTag: {
    fontSize: 12,
    color: '#6C4AB6',
    fontWeight: '700',
    marginTop: 2,
  },
  placeCardAddress: {
    fontSize: 12,
    color: '#6B7280',
    marginTop: 4,
  },
  placeCardClose: {
    padding: 4,
    marginLeft: 8,
    backgroundColor: '#F5F3FF',
    borderRadius: 12,
  },
  placeCardCloseText: {
    fontSize: 14,
    color: '#7C3AED',
    fontWeight: 'bold',
  },
  navigateBtn: {
    backgroundColor: '#6C4AB6',
    borderRadius: 14,
    paddingVertical: 12,
    alignItems: 'center',
    shadowColor: '#6C4AB6',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 4,
    elevation: 3,
  },
  navigateBtnText: {
    color: '#FFFFFF',
    fontSize: 14,
    fontWeight: '800',
  },
  bottomDrawer: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    zIndex: 30,
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
    zIndex: 999,
  },
  originModalBox: {
    width: '100%',
    maxWidth: 380,
    backgroundColor: '#FFFFFF',
    borderRadius: 20,
    padding: 22,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.25,
    shadowRadius: 10,
    elevation: 10,
  },
  originModalTitle: {
    fontSize: 18,
    fontWeight: '800',
    color: '#111827',
    marginBottom: 4,
  },
  originModalSubtitle: {
    fontSize: 13,
    color: '#6B7280',
    marginBottom: 16,
  },
  originHubOption: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: 12,
    paddingHorizontal: 14,
    borderRadius: 12,
    backgroundColor: '#F3F4F6',
    marginBottom: 8,
  },
  originHubOptionSelected: {
    backgroundColor: '#EEF2FF',
    borderColor: '#3B82F6',
    borderWidth: 1.5,
  },
  originHubOptionText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#1F2937',
  },
  originHubCheckmark: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#3B82F6',
  },
  originModalCloseBtn: {
    marginTop: 12,
    paddingVertical: 10,
    borderRadius: 10,
    backgroundColor: '#E5E7EB',
    alignItems: 'center',
  },
  originModalCloseBtnText: {
    fontSize: 14,
    fontWeight: '700',
    color: '#374151',
  },

  fabColumnWithRoutes: {
    bottom: 375,
  },
  zoomPill: {
    backgroundColor: '#FFFFFF',
    borderRadius: 24,
    borderWidth: 1,
    borderColor: '#EDE9FE',
    overflow: 'hidden',
    shadowColor: '#4E3486',
    shadowOffset: { width: 0, height: 3 },
    shadowOpacity: 0.18,
    shadowRadius: 5,
    elevation: 4,
  },
  zoomBtn: {
    width: 48,
    height: 40,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#FFFFFF',
  },
  zoomBtnText: {
    fontSize: 20,
    fontWeight: '700',
    color: '#4E3486',
  },
  zoomDivider: {
    height: 1,
    backgroundColor: '#EDE9FE',
    marginHorizontal: 8,
  },
  routeLegendContainer: {
    position: 'absolute',
    bottom: 350,
    alignSelf: 'center',
    flexDirection: 'row',
    backgroundColor: 'rgba(255, 255, 255, 0.96)',
    paddingHorizontal: 8,
    paddingVertical: 6,
    borderRadius: 22,
    borderWidth: 1.5,
    borderColor: '#EDE9FE',
    gap: 6,
    zIndex: 35,
    shadowColor: '#4E3486',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.22,
    shadowRadius: 6,
    elevation: 7,
  },
  legendPill: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 14,
    backgroundColor: '#F5F3FF',
    gap: 6,
  },
  legendPillActiveSafest: {
    backgroundColor: '#ECFDF5',
    borderWidth: 1.5,
    borderColor: '#10B981',
  },
  legendPillActiveFastest: {
    backgroundColor: '#EFF6FF',
    borderWidth: 1.5,
    borderColor: '#2563EB',
  },
  legendPillActiveBalanced: {
    backgroundColor: '#FFFBEB',
    borderWidth: 1.5,
    borderColor: '#F59E0B',
  },
  legendColorDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
  },
  legendText: {
    fontSize: 12,
    fontWeight: '700',
    color: '#4B5563',
  },
  legendTextActive: {
    color: '#1E1B4B',
    fontWeight: '800',
  },
});
