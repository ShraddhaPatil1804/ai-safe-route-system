import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity, ScrollView } from 'react-native';
import SafetyBadge, { getSafetyColor } from './SafetyBadge';

export default function RouteComparisonCard({
  comparisonData,
  selectedMode,
  onSelectMode,
  onStartNavigation,
  onClose,
}) {
  if (!comparisonData) return null;

  const modes = [
    { key: 'fastest', title: 'FASTEST', subtitle: 'Least Time', icon: '⚡', data: comparisonData.fastest },
    { key: 'balanced', title: 'MEDIUM', subtitle: 'More Safety', icon: '⚖️', data: comparisonData.balanced },
    { key: 'safest', title: 'SAFEST', subtitle: 'Top Safety', icon: '🛡️', data: comparisonData.safest, highlight: true },
  ];

  const activeRoute = comparisonData[selectedMode] || comparisonData.balanced || comparisonData.safest;

  return (
    <View style={styles.cardWrapper}>
      {/* Header */}
      <View style={styles.headerRow}>
        <View>
          <Text style={styles.sheetTitle}>Recommended Routes</Text>
          <Text style={styles.sheetSubtitle}>Compare time vs. safety trade-offs</Text>
        </View>
        {onClose && (
          <TouchableOpacity onPress={onClose} style={styles.closeBtn}>
            <Text style={styles.closeBtnText}>✕</Text>
          </TouchableOpacity>
        )}
      </View>

      {/* Mode Tabs */}
      <View style={styles.modeTabsRow}>
        {modes.map((m) => {
          const isSelected = selectedMode === m.key;
          const rData = m.data;
          if (!rData) return null;

          const color = getSafetyColor(rData.safety_score);

          return (
            <TouchableOpacity
              key={m.key}
              style={[
                styles.tabItem,
                isSelected && styles.tabItemSelected,
                isSelected && m.highlight && styles.tabItemSafestSelected,
              ]}
              onPress={() => onSelectMode(m.key)}
            >
              <Text style={styles.tabIcon}>{m.icon}</Text>
              <Text style={[styles.tabTitle, isSelected && styles.tabTitleSelected]}>
                {m.title}
              </Text>
              <Text style={styles.tabSubtitleText}>{m.subtitle}</Text>
              <Text style={styles.tabTime}>{rData.estimated_time_minutes} min</Text>
              <Text style={styles.tabDist}>{rData.distance_km} km</Text>
              <View style={[styles.miniBadge, { backgroundColor: isSelected ? color : '#E5E7EB' }]}>
                <Text style={[styles.miniBadgeText, { color: isSelected ? '#FFF' : '#374151' }]}>
                  {rData.safety_score}/100
                </Text>
              </View>
            </TouchableOpacity>
          );
        })}
      </View>

      {/* Selected Route Details */}
      {activeRoute && (
        <View style={styles.activeDetailsBox}>
          <View style={styles.activeSummaryRow}>
            <View>
              <Text style={styles.activeTimeText}>
                {activeRoute.estimated_time_minutes} min{' '}
                <Text style={styles.activeDistSub}>({activeRoute.distance_km} km)</Text>
              </Text>
              <Text style={styles.activeModeLabel}>
                Mode:{' '}
                <Text style={{ fontWeight: '700', textTransform: 'capitalize' }}>
                  {activeRoute.route_type}
                </Text>
              </Text>
            </View>

            <SafetyBadge
              score={activeRoute.safety_score}
              level={activeRoute.safety_level}
              size="medium"
            />
          </View>

          {/* Safety Explanations */}
          {activeRoute.explanation && activeRoute.explanation.length > 0 && (
            <View style={styles.explanationSection}>
              <Text style={styles.explanationHeader}>Why this route:</Text>
              {activeRoute.explanation.map((exp, idx) => (
                <View key={idx} style={styles.reasonRow}>
                  <Text style={styles.reasonCheck}>✓</Text>
                  <Text style={styles.reasonText}>{exp}</Text>
                </View>
              ))}
            </View>
          )}

          {/* Navigation Action */}
          <TouchableOpacity
            style={styles.startNavBtn}
            onPress={() => onStartNavigation && onStartNavigation(activeRoute)}
          >
            <Text style={styles.startNavBtnText}>Start Navigation</Text>
          </TouchableOpacity>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  cardWrapper: {
    backgroundColor: '#FFFFFF',
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    padding: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: -3 },
    shadowOpacity: 0.15,
    shadowRadius: 8,
    elevation: 8,
  },
  headerRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  sheetTitle: {
    fontSize: 17,
    fontWeight: '700',
    color: '#111827',
  },
  sheetSubtitle: {
    fontSize: 12,
    color: '#6B7280',
    marginTop: 2,
  },
  closeBtn: {
    padding: 6,
  },
  closeBtnText: {
    fontSize: 18,
    color: '#9CA3AF',
    fontWeight: 'bold',
  },
  modeTabsRow: {
    flexDirection: 'row',
    gap: 8,
    marginBottom: 14,
  },
  tabItem: {
    flex: 1,
    backgroundColor: '#F9FAFB',
    borderRadius: 12,
    paddingVertical: 10,
    paddingHorizontal: 6,
    alignItems: 'center',
    borderWidth: 1.5,
    borderColor: '#E5E7EB',
  },
  tabItemSelected: {
    borderColor: '#2563EB',
    backgroundColor: '#EFF6FF',
  },
  tabItemSafestSelected: {
    borderColor: '#10B981',
    backgroundColor: '#ECFDF5',
  },
  tabIcon: {
    fontSize: 18,
    marginBottom: 2,
  },
  tabTitle: {
    fontSize: 11,
    fontWeight: '700',
    color: '#4B5563',
  },
  tabTitleSelected: {
    color: '#111827',
  },
  tabSubtitleText: {
    fontSize: 9,
    fontWeight: '600',
    color: '#6B7280',
    marginTop: 1,
  },
  tabTime: {
    fontSize: 15,
    fontWeight: '800',
    color: '#111827',
    marginTop: 3,
  },

  tabDist: {
    fontSize: 11,
    color: '#6B7280',
  },
  miniBadge: {
    marginTop: 6,
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 8,
  },
  miniBadgeText: {
    fontSize: 10,
    fontWeight: '700',
  },
  activeDetailsBox: {
    backgroundColor: '#F9FAFB',
    borderRadius: 14,
    padding: 12,
    borderWidth: 1,
    borderColor: '#E5E7EB',
  },
  activeSummaryRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 10,
  },
  activeTimeText: {
    fontSize: 20,
    fontWeight: '800',
    color: '#111827',
  },
  activeDistSub: {
    fontSize: 14,
    fontWeight: '500',
    color: '#6B7280',
  },
  activeModeLabel: {
    fontSize: 12,
    color: '#4B5563',
    marginTop: 2,
  },
  explanationSection: {
    borderTopWidth: 1,
    borderTopColor: '#E5E7EB',
    paddingTop: 8,
    marginBottom: 12,
  },
  explanationHeader: {
    fontSize: 12,
    fontWeight: '700',
    color: '#374151',
    marginBottom: 4,
  },
  reasonRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginTop: 3,
  },
  reasonCheck: {
    color: '#10B981',
    fontWeight: '900',
    fontSize: 13,
  },
  reasonText: {
    fontSize: 12,
    color: '#4B5563',
    flexShrink: 1,
  },
  startNavBtn: {
    backgroundColor: '#10B981',
    borderRadius: 12,
    paddingVertical: 12,
    alignItems: 'center',
    shadowColor: '#10B981',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.3,
    shadowRadius: 4,
    elevation: 3,
  },
  startNavBtnText: {
    color: '#FFFFFF',
    fontSize: 15,
    fontWeight: '700',
  },
});
