import React from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity } from 'react-native';

export const FILTER_ITEMS = [
  { id: 'all', label: 'All Markers', icon: '📍' },
  { id: 'police', label: 'Police', icon: '👮' },
  { id: 'hospital', label: 'Hospitals', icon: '🏥' },
  { id: 'pharmacy', label: 'Pharmacies', icon: '💊' },
  { id: 'college', label: 'Colleges', icon: '🏫' },
  { id: 'school', label: 'Schools', icon: '🎒' },
  { id: 'shop', label: 'Shops & Malls', icon: '🛍️' },
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
        {/* Safety Heatmap Toggle Chip */}
        <TouchableOpacity
          style={[styles.chip, styles.heatmapChip, showHeatmap && styles.heatmapChipActive]}
          onPress={onToggleHeatmap}
          activeOpacity={0.7}
        >
          <Text style={styles.chipIcon}>🛡️</Text>
          <Text style={[styles.chipText, showHeatmap && styles.chipTextSelected]}>
            {showHeatmap ? 'Hide Safety Heatmap' : 'Safety Heatmap'}
          </Text>
        </TouchableOpacity>

        {/* POI Category Chips */}
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
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    paddingVertical: 6,
  },
  scrollContent: {
    paddingHorizontal: 2,
    gap: 8,
    alignItems: 'center',
  },
  chip: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#FFFFFF',
    paddingHorizontal: 13,
    paddingVertical: 7,
    borderRadius: 20,
    borderWidth: 1.5,
    borderColor: '#EDE9FE',
    shadowColor: '#6C4AB6',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.08,
    shadowRadius: 4,
    elevation: 2,
    gap: 6,
  },
  chipSelected: {
    backgroundColor: '#6C4AB6',
    borderColor: '#4E3486',
    shadowColor: '#6C4AB6',
    shadowOpacity: 0.25,
    elevation: 3,
  },
  heatmapChip: {
    backgroundColor: '#F5F3FF',
    borderColor: '#C4B5FD',
  },
  heatmapChipActive: {
    backgroundColor: '#10B981',
    borderColor: '#059669',
  },
  chipIcon: {
    fontSize: 13,
  },
  chipText: {
    fontSize: 12,
    fontWeight: '700',
    color: '#4E3486',
  },
  chipTextSelected: {
    color: '#FFFFFF',
    fontWeight: '800',
  },
});
