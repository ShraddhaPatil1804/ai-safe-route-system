import React, { useEffect, useRef } from 'react';
import { View, StyleSheet } from 'react-native';

const CATEGORY_STYLES = {
  police: { color: '#1E40AF', emoji: '👮' },
  hospital: { color: '#DC2626', emoji: '🏥' },
  pharmacy: { color: '#059669', emoji: '💊' },
  restaurant: { color: '#EA580C', emoji: '🍽️' },
  cafe: { color: '#D97706', emoji: '☕' },
  bus_stop: { color: '#4F46E5', emoji: '🚌' },
  bank: { color: '#0284C7', emoji: '🏦' },
  fuel: { color: '#D946EF', emoji: '⛽' },
  park: { color: '#16A34A', emoji: '🌳' },
  bar: { color: '#9333EA', emoji: '🍺' },
  other: { color: '#6B7280', emoji: '📍' },
};

export default function MapViewComponent({
  region,
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
  const containerRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const routeLayersRef = useRef([]);
  const markerLayersRef = useRef([]);
  const userMarkerRef = useRef(null);

  useEffect(() => {
    if (typeof window !== 'undefined' && !window.L) {
      const link = document.createElement('link');
      link.rel = 'stylesheet';
      link.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
      document.head.appendChild(link);

      const script = document.createElement('script');
      script.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';
      script.onload = () => initLeafletMap();
      document.body.appendChild(script);
    } else if (typeof window !== 'undefined' && window.L) {
      initLeafletMap();
    }
  }, []);

  const initLeafletMap = () => {
    if (!window.L || !containerRef.current || mapInstanceRef.current) return;

    const map = window.L.map(containerRef.current).setView(
      [region.latitude, region.longitude],
      14
    );

    window.L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© OpenStreetMap contributors | Women Safe Navigation Nashik',
      maxZoom: 19,
    }).addTo(map);

    map.on('click', (e) => {
      if (onMapPress) {
        onMapPress({ latitude: e.latlng.lat, longitude: e.latlng.lng });
      }
    });

    mapInstanceRef.current = map;
    updateLayers();
  };

  const updateLayers = () => {
    const map = mapInstanceRef.current;
    if (!map || !window.L) return;

    // Clear old route layers
    routeLayersRef.current.forEach((l) => map.removeLayer(l));
    routeLayersRef.current = [];

    // Clear old marker layers
    markerLayersRef.current.forEach((m) => map.removeLayer(m));
    markerLayersRef.current = [];

    // 1. User Location / Vehicle Marker
    if (userLocation) {
      const uIcon = window.L.divIcon({
        className: 'user-marker',
        html: `
          <div style="position:relative;display:flex;align-items:center;justify-content:center;">
            <div style="position:absolute;width:34px;height:34px;border-radius:50%;background:rgba(37,99,235,0.25);animation:pulse 1.8s infinite;"></div>
            <div style="background:#2563EB;width:18px;height:18px;border-radius:50%;border:3px solid #FFFFFF;box-shadow:0 2px 6px rgba(0,0,0,0.4);display:flex;align-items:center;justify-content:center;color:#FFF;font-size:10px;font-weight:bold;">▲</div>
          </div>
        `,
        iconSize: [34, 34],
        iconAnchor: [17, 17],
      });
      const m = window.L.marker([userLocation.latitude, userLocation.longitude], { icon: uIcon })
        .addTo(map)
        .bindPopup('<b>Your Live Location</b>');
      markerLayersRef.current.push(m);
      userMarkerRef.current = m;

      if (isNavigating) {
        map.panTo([userLocation.latitude, userLocation.longitude], { animate: true });
      }
    }

    // 2. Destination Marker
    if (destination) {
      const dIcon = window.L.divIcon({
        className: 'dest-marker',
        html: `
          <div style="background:#DC2626;width:30px;height:30px;border-radius:15px;border:3px solid #FFFFFF;box-shadow:0 2px 8px rgba(0,0,0,0.4);display:flex;align-items:center;justify-content:center;color:#FFF;font-size:14px;">
            🎯
          </div>
        `,
        iconSize: [30, 30],
        iconAnchor: [15, 15],
      });
      const m = window.L.marker([destination.latitude, destination.longitude], { icon: dIcon })
        .addTo(map)
        .bindPopup('<b>Destination</b>');
      markerLayersRef.current.push(m);
    }

    // 3. POI Markers with category icons and tap callback
    if (!isNavigating && pois && pois.length > 0) {
      pois.forEach((p) => {
        const style = CATEGORY_STYLES[p.category] || CATEGORY_STYLES.other;
        const isSelected = selectedPoi && selectedPoi.id === p.id && selectedPoi.category === p.category;

        const pIcon = window.L.divIcon({
          className: 'poi-marker',
          html: `<div style="background:${isSelected ? '#F59E0B' : style.color};width:${isSelected ? '30px' : '24px'};height:${isSelected ? '30px' : '24px'};border-radius:${isSelected ? '15px' : '12px'};border:2px solid #FFF;display:flex;align-items:center;justify-content:center;font-size:${isSelected ? '15px' : '12px'};box-shadow:0 2px 6px rgba(0,0,0,0.4);cursor:pointer;">${style.emoji}</div>`,
          iconSize: isSelected ? [30, 30] : [24, 24],
          iconAnchor: isSelected ? [15, 15] : [12, 12],
        });
        const m = window.L.marker([p.latitude, p.longitude], { icon: pIcon })
          .addTo(map);

        m.on('click', (e) => {
          if (window.L && window.L.DomEvent) {
            window.L.DomEvent.stopPropagation(e);
          }
          if (onSelectPOI) {
            onSelectPOI(p);
          }
        });

        markerLayersRef.current.push(m);
      });
    }

    // 4. Routes Polylines
    if (comparisonData) {
      ['fastest', 'safest', 'balanced'].forEach((mKey) => {
        const r = comparisonData[mKey];
        if (!r?.geometry?.coordinates) return;

        const isSelected = mKey === selectedMode;
        const latLngs = r.geometry.coordinates.map(([lon, lat]) => [lat, lon]);

        const poly = window.L.polyline(latLngs, {
          color: isSelected ? (mKey === 'safest' ? '#10B981' : (mKey === 'balanced' ? '#F59E0B' : '#2563EB')) : '#94A3B8',
          weight: isSelected ? 7 : 4,
          opacity: isSelected ? 0.95 : 0.4,
          dashArray: isSelected ? null : '6, 6',
        }).addTo(map);

        routeLayersRef.current.push(poly);

        if (isSelected && !isNavigating && latLngs.length > 0) {
          map.fitBounds(poly.getBounds(), { padding: [50, 50] });
        }
      });
    }

    // 5. Active Navigation Step Segment Highlight
    if (isNavigating && activeStepCoords && activeStepCoords.length > 1) {
      const stepLatLngs = activeStepCoords.map(([lon, lat]) => [lat, lon]);
      const stepPoly = window.L.polyline(stepLatLngs, {
        color: '#FBBF24',
        weight: 10,
        opacity: 0.9,
      }).addTo(map);
      routeLayersRef.current.push(stepPoly);
    }

    // 6. Safety Heatmap
    if (showHeatmap && heatmapData?.features) {
      heatmapData.features.forEach((feat) => {
        if (feat.geometry?.type !== 'LineString') return;
        const latLngs = feat.geometry.coordinates.map(([lon, lat]) => [lat, lon]);
        const poly = window.L.polyline(latLngs, {
          color: feat.properties.color || '#FBBF24',
          weight: 4,
          opacity: 0.7,
        }).addTo(map);
        routeLayersRef.current.push(poly);
      });
    }
  };

  useEffect(() => {
    updateLayers();
  }, [userLocation, destination, comparisonData, selectedMode, pois, selectedPoi, showHeatmap, heatmapData, activeStepCoords, isNavigating]);

  return (
    <View style={styles.container}>
      <div ref={containerRef} style={{ width: '100%', height: '100%', position: 'absolute', top: 0, left: 0 }} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    ...StyleSheet.absoluteFillObject,
  },
});
