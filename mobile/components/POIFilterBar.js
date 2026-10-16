import React from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity } from 'react-native';

// Categories in the exact required order:
// 1. All Markers, 2. Police, 3. Hospitals, 4. Pharmacies, 5. Restaurants,
// 6. Cafes, 7. Bus Stops, 8. Banks, 9. Fuel, 10. Parks, 11. Bars
export const FILTER_ITEMS = [
  { id: 'all', label: 'All Markers', icon: '📍' },
  { id: 'police', label: 'Police', icon: '👮' },
  { id: 'hospital', label: 'Hospitals', icon: '🏥' },
  { id: 'pharmacy', label: 'Pharmacies', icon: '💊' },
  { id: 'restaurant', label: 'Restaurants', icon: '🍽️' },
  { id: 'cafe', label: 'Cafes', icon: '☕' },
  { id: 'bus_stop', label: 'Bus Stops', icon: '🚌' },
  { id: 'bank', label: 'Banks', icon: '🏦' },
  { id: 'fuel', label: 'Fuel', icon: '⛽' },
  { id: 'park', label: 'Parks', icon: '🌳' },
  { id: 'bar', label: 'Bars', icon: '🍺' },
];

export default function POIFilterBar({
  selectedCategory,
  onSelectCategory,
  showHeatmap,
  onToggleHeatmap,
}) {
  return (
    <View style={styles.container}>
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.scrollContent}
      >
        {/* POI Category Chips in exact specified order */}
        {FILTER_ITEMS.map((item) => {
          const isSelected = selectedCategory === item.id;
          return (
            <TouchableOpacity
              key={item.id}
              style={[styles.chip, isSelected && styles.chipSelected]}
              onPress={() => onSelectCategory(item.id)}
              activeOpacity={0.7}
            >
              <Text style={styles.chipIcon}>{item.icon}</Text>
              <Text style={[styles.chipText, isSelected && styles.chipTextSelected]}>
                {item.label}
              </Text>
            </TouchableOpacity>
          );
        })}

        {/* Safety Heatmap Toggle Chip */}
        <TouchableOpacity
          style={[styles.chip, styles.heatmapChip, showHeatmap && styles.heatmapChipActive]}
          onPress={onToggleHeatmap}
          activeOpacity={0.7}
        >
          <Text style={styles.chipText}>
            {showHeatmap ? '🛡️ Hide Safety Map' : '🛡️ Safety Layer'}
          </Text>
        </TouchableOpacity>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    paddingVertical: 6,
  },
  scrollContent: {
    paddingHorizontal: 4,
    gap: 8,
    alignItems: 'center',
  },
  chip: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#FFFFFF',
    paddingHorizontal: 12,
    paddingVertical: 7,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: '#E5E7EB',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 2,
    elevation: 2,
    gap: 5,
  },
  chipSelected: {
    backgroundColor: '#1E40AF',
    borderColor: '#1E40AF',
  },
  heatmapChip: {
    backgroundColor: '#ECFDF5',
    borderColor: '#10B981',
  },
  heatmapChipActive: {
    backgroundColor: '#10B981',
    borderColor: '#059669',
  },
  chipIcon: {
    fontSize: 14,
  },
  chipText: {
    fontSize: 12,
    fontWeight: '600',
    color: '#374151',
  },
  chipTextSelected: {
    color: '#FFFFFF',
    fontWeight: '700',
  },
});
