import React from 'react';
import { StyleSheet, View } from 'react-native';
import MapView, { Marker, Polyline } from 'react-native-maps';

export const CATEGORY_COLORS = {
  police: '#1E40AF',
  hospital: '#DC2626',
  pharmacy: '#059669',
  restaurant: '#EA580C',
  cafe: '#D97706',
  bus_stop: '#4F46E5',
  bank: '#0284C7',
  fuel: '#D946EF',
  park: '#16A34A',
  bar: '#9333EA',
  school: '#8B5CF6',
  college: '#7C3AED',
  shop: '#EC4899',
  mall: '#BE185D',
  supermarket: '#0891B2',
  other: '#6B7280',
};

export const MODE_COLORS = {
  safest: '#10B981',
  fastest: '#3B82F6',
  balanced: '#6C4AB6',
};

export default function MapViewComponent({
  mapRef,
  region,
  onRegionChangeComplete,
  onMapPress,
  userLocation,
  destination,
  comparisonData,
  selectedMode,
  pois,
  selectedPoi,
  onSelectPOI,
  showHeatmap,
  heatmapData,
  activeStepCoords,
  isNavigating,
}) {
  const selectedRoute = comparisonData ? comparisonData[selectedMode] : null;

  return (
    <MapView
      ref={mapRef}
      style={styles.map}
      initialRegion={region}
      onRegionChangeComplete={onRegionChangeComplete}
      onPress={(e) => onMapPress && onMapPress(e.nativeEvent.coordinate)}
      showsUserLocation={true}
      showsMyLocationButton={false}
      followsUserLocation={isNavigating}
    >
      {/* Destination Marker */}
      {destination && (
        <Marker
          coordinate={destination}
          title="Destination"
          pinColor="#EF4444"
        />
      )}

      {/* User Location Marker */}
      {userLocation && (
        <Marker
          coordinate={userLocation}
          title="Your Live Location"
          pinColor="#2563EB"
        />
      )}

      {/* Selected POI Highlight Marker */}
      {selectedPoi && (
        <Marker
          coordinate={{ latitude: selectedPoi.latitude, longitude: selectedPoi.longitude }}
          title={selectedPoi.name || selectedPoi.category}
          pinColor="#F59E0B"
        />
      )}

      {/* POI Markers */}
      {!isNavigating && pois && pois.map((p) => {
        const pinColor = CATEGORY_COLORS[p.category] || '#6B7280';
        return (
          <Marker
            key={`${p.category}-${p.id}`}
            coordinate={{ latitude: p.latitude, longitude: p.longitude }}
            title={p.name || p.category}
            pinColor={pinColor}
            onPress={(e) => {
              e.stopPropagation && e.stopPropagation();
              onSelectPOI && onSelectPOI(p);
            }}
          />
        );
      })}

      {/* Safety Heatmap Polylines */}
      {showHeatmap && heatmapData?.features?.map((feat, idx) => {
        if (feat.geometry?.type !== 'LineString') return null;
        const coords = feat.geometry.coordinates.map(([lon, lat]) => ({
          latitude: lat,
          longitude: lon,
        }));
        return (
          <Polyline
            key={`heat-${idx}`}
            coordinates={coords}
            strokeColor={feat.properties.color || '#FBBF24'}
            strokeWidth={3}
          />
        );
      })}

      {/* Route Polylines */}
      {comparisonData && (
        <>
          {/* Unselected Alternate Routes */}
          {!isNavigating && ['safest', 'fastest', 'balanced'].map((mKey) => {
            if (mKey === selectedMode) return null;
            const r = comparisonData[mKey];
            if (!r?.geometry?.coordinates) return null;
            const coords = r.geometry.coordinates.map(([lon, lat]) => ({
              latitude: lat,
              longitude: lon,
            }));
            return (
              <Polyline
                key={`alt-${mKey}`}
                coordinates={coords}
                strokeColor="#C4B5FD"
                strokeWidth={3.5}
                lineDashPattern={[5, 5]}
              />
            );
          })}

          {/* Selected Active Route */}
          {selectedRoute?.geometry?.coordinates && (
            <Polyline
              coordinates={selectedRoute.geometry.coordinates.map(([lon, lat]) => ({
                latitude: lat,
                longitude: lon,
              }))}
            strokeColor={
              selectedMode === 'safest'
                ? '#10B981'
                : selectedMode === 'balanced'
                ? '#F59E0B'
                : '#2563EB'
            }
              strokeWidth={7}
            />
          )}

          {/* Active Navigation Step Highlight */}
          {isNavigating && activeStepCoords && activeStepCoords.length > 1 && (
            <Polyline
              coordinates={activeStepCoords.map(([lon, lat]) => ({
                latitude: lat,
                longitude: lon,
              }))}
              strokeColor="#FBBF24"
              strokeWidth={10}
            />
          )}
        </>
      )}
    </MapView>
  );
}

const styles = StyleSheet.create({
  map: {
    ...StyleSheet.absoluteFillObject,
  },
});
