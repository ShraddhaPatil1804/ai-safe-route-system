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
  school: { color: '#8B5CF6', emoji: '🎒' },
  college: { color: '#7C3AED', emoji: '🏫' },
  shop: { color: '#EC4899', emoji: '🛍️' },
  mall: { color: '#BE185D', emoji: '🏬' },
  supermarket: { color: '#0891B2', emoji: '🛒' },
  other: { color: '#6B7280', emoji: '📍' },
};

const MODE_COLORS = {
  safest: '#10B981',
  fastest: '#3B82F6',
  balanced: '#6C4AB6',
};

// Injected essential Leaflet CSS to eliminate grey tiles, misalignments, and loading races
const LEAFLET_CORE_CSS = `
  .leaflet-pane, .leaflet-tile, .leaflet-marker-icon, .leaflet-marker-shadow,
  .leaflet-tile-container, .leaflet-pane > svg, .leaflet-pane > canvas,
  .leaflet-zoom-box, .leaflet-image-layer, .leaflet-layer {
    position: absolute; left: 0; top: 0;
  }
  .leaflet-container {
    overflow: hidden; width: 100%; height: 100%; position: absolute; top: 0; left: 0; right: 0; bottom: 0;
    background-color: #F8F7FF; outline: none; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  }
  .leaflet-tile {
    filter: inherit; visibility: inherit; user-select: none; -webkit-user-select: none;
  }
  .leaflet-marker-icon, .leaflet-marker-shadow {
    display: block;
  }
  .leaflet-control-container .leaflet-top,
  .leaflet-control-container .leaflet-bottom {
    position: absolute; z-index: 10; pointer-events: none;
  }
  .leaflet-control {
    pointer-events: auto;
  }
`;

export default function MapViewComponent({
  mapRef,
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
    // 1. Inject Leaflet critical CSS if not already present
    if (typeof document !== 'undefined' && !document.getElementById('leaflet-essential-css')) {
      const styleEl = document.createElement('style');
      styleEl.id = 'leaflet-essential-css';
      styleEl.innerHTML = LEAFLET_CORE_CSS;
      document.head.appendChild(styleEl);
    }

    // 2. Load Leaflet JS & full stylesheet
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

    return () => {
      // Clean up map instance on unmount
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
  }, []);

  const initLeafletMap = () => {
    if (!window.L || !containerRef.current || mapInstanceRef.current) return;

    try {
      const map = window.L.map(containerRef.current, {
        zoomControl: false, // We provide modern integrated zoom controls
        attributionControl: false,
      }).setView(
        [region.latitude || 19.985, region.longitude || 73.795],
        14
      );

      // Standard high-reliability OpenStreetMap tiles with no API key requirement or watermark
      window.L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        subdomains: 'abc',
        maxZoom: 19,
        crossOrigin: true,
      }).addTo(map);

      map.on('click', (e) => {
        if (onMapPress) {
          onMapPress({ latitude: e.latlng.lat, longitude: e.latlng.lng });
        }
      });

      mapInstanceRef.current = map;

      // Expose map controls via mapRef for parent component
      if (mapRef) {
        mapRef.current = {
          animateToRegion: (coords, duration = 500) => {
            if (mapInstanceRef.current) {
              mapInstanceRef.current.flyTo(
                [coords.latitude, coords.longitude],
                15,
                { duration: duration / 1000 }
              );
            }
          },
          zoomIn: () => {
            if (mapInstanceRef.current) mapInstanceRef.current.zoomIn();
          },
          zoomOut: () => {
            if (mapInstanceRef.current) mapInstanceRef.current.zoomOut();
          },
        };
      }

      // Ensure proper dimensions are calculated after DOM attachment
      setTimeout(() => {
        if (mapInstanceRef.current) {
          mapInstanceRef.current.invalidateSize();
        }
      }, 150);

      updateLayers();
    } catch (e) {
      console.warn('Leaflet map initialization warning:', e);
    }
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
            <div style="position:absolute;width:34px;height:34px;border-radius:50%;background:rgba(108,74,182,0.25);animation:pulse 1.8s infinite;"></div>
            <div style="background:#6C4AB6;width:18px;height:18px;border-radius:50%;border:3px solid #FFFFFF;box-shadow:0 2px 6px rgba(0,0,0,0.3);display:flex;align-items:center;justify-content:center;color:#FFF;font-size:10px;font-weight:bold;">▲</div>
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
          <div style="background:#DC2626;width:32px;height:32px;border-radius:16px;border:3px solid #FFFFFF;box-shadow:0 3px 8px rgba(0,0,0,0.35);display:flex;align-items:center;justify-content:center;color:#FFF;font-size:15px;">
            🎯
          </div>
        `,
        iconSize: [32, 32],
        iconAnchor: [16, 16],
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
          html: `<div style="background:${isSelected ? '#6C4AB6' : style.color};width:${isSelected ? '32px' : '26px'};height:${isSelected ? '32px' : '26px'};border-radius:${isSelected ? '16px' : '13px'};border:2.5px solid #FFF;display:flex;align-items:center;justify-content:center;font-size:${isSelected ? '15px' : '12px'};box-shadow:0 2px 6px rgba(0,0,0,0.3);cursor:pointer;transform:${isSelected ? 'scale(1.1)' : 'scale(1)'};transition:all 0.2s;">${p.is_24_7 && p.category === 'pharmacy' ? '🏪' : style.emoji}</div>`,
          iconSize: isSelected ? [32, 32] : [26, 26],
          iconAnchor: isSelected ? [16, 16] : [13, 13],
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

    // 4. Routes Polylines (Safest, Fastest, Balanced)
    if (comparisonData) {
      // Draw unselected routes first, then active selected route on top
      const modesOrder = ['fastest', 'balanced', 'safest'].filter(k => k !== selectedMode);
      if (selectedMode && comparisonData[selectedMode]) {
        modesOrder.push(selectedMode);
      }

      modesOrder.forEach((mKey) => {
        const r = comparisonData[mKey];
        if (!r?.geometry?.coordinates) return;

        const isSelected = mKey === selectedMode;
        const latLngs = r.geometry.coordinates.map(([lon, lat]) => [lat, lon]);
        const routeColor = MODE_COLORS[mKey] || '#6C4AB6';

        const poly = window.L.polyline(latLngs, {
          color: isSelected
            ? (mKey === 'safest'
                ? '#10B981'
                : mKey === 'balanced'
                ? '#F59E0B'
                : '#2563EB')
            : '#C4B5FD',
          weight: isSelected ? 7.5 : 4.0,
          opacity: isSelected ? 0.95 : 0.5,
          dashArray: isSelected ? null : '6, 6',
        }).addTo(map);

        routeLayersRef.current.push(poly);

        if (isSelected && !isNavigating && latLngs.length > 0) {
          map.fitBounds(poly.getBounds(), { padding: [55, 55] });
        }
      });
    }

    // 5. Active Navigation Step Segment Highlight
    if (isNavigating && activeStepCoords && activeStepCoords.length > 1) {
      const stepLatLngs = activeStepCoords.map(([lon, lat]) => [lat, lon]);
      const stepPoly = window.L.polyline(stepLatLngs, {
        color: '#FBBF24',
        weight: 10,
        opacity: 0.95,
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
      <div
        ref={containerRef}
        style={{
          width: '100%',
          height: '100%',
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: '#F8F7FF',
        }}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: '#F8F7FF',
  },
});
