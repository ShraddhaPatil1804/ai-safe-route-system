import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity, ScrollView } from 'react-native';
import SafetyBadge, { getSafetyColor } from './SafetyBadge';

export default function RouteComparisonCard({
  comparisonData,
  selectedMode,
  onSelectMode,
  onStartNavigation,
  onClose,
  timeOfDay = 'day',
}) {
  if (!comparisonData) return null;

    const modes = [
    {
      key: 'fastest',
      title: 'FASTEST',
      subtitle: 'Least Time',
      icon: '⚡',
      color: '#2563EB',
      bgLight: '#EFF6FF',
      data: comparisonData.fastest,
    },
    {
      key: 'balanced',
      title: 'BALANCED',
      subtitle: 'Time & Safety',
      icon: '⚖️',
      color: '#F59E0B',
      bgLight: '#FFFBEB',
      data: comparisonData.balanced,
    },
    {
      key: 'safest',
      title: 'SAFEST',
      subtitle: 'Top Safety',
      icon: '🛡️',
      color: '#10B981',
      bgLight: '#ECFDF5',
      data: comparisonData.safest,
      highlight: true,
    },
  ];
  const activeRoute =
    comparisonData[selectedMode] ||
    comparisonData.safest ||
    comparisonData.balanced ||
    comparisonData.fastest;

  const activeModeConfig = modes.find((m) => m.key === (activeRoute?.route_type || selectedMode)) || modes[0];

  return (
    <View style={styles.cardContainer}>
      {/* Drag handle / top pill */}
      <View style={styles.dragHandle} />

      {/* Header */}
      <View style={styles.headerRow}>
        <View style={styles.headerTitleWrap}>
          <Text style={styles.sheetTitle}>Safety Route Options</Text>
          <View style={styles.departureBadge}>
            <Text style={styles.departureBadgeText}>
              {timeOfDay === 'night' ? '🌙 Night Routing Active' : '☀️ Day Routing Active'}
            </Text>
          </View>
        </View>
        {onClose && (
          <TouchableOpacity onPress={onClose} style={styles.closeBtn} activeOpacity={0.7}>
            <Text style={styles.closeBtnText}>✕</Text>
          </TouchableOpacity>
        )}
      </View>

      {/* 3 Mode Tabs Row: Safest, Fastest, Balanced */}
      <View style={styles.modeTabsRow}>
        {modes.map((m) => {
          const isSelected = selectedMode === m.key;
          const rData = m.data;
          if (!rData) return null;

          const safetyColor = getSafetyColor(rData.safety_score);

          return (
            <TouchableOpacity
              key={m.key}
              style={[
                styles.tabCard,
                isSelected && {
                  borderColor: m.color,
                  backgroundColor: m.bgLight,
                  transform: [{ scale: 1.02 }],
                  shadowColor: m.color,
                  shadowOpacity: 0.25,
                },
              ]}
              onPress={() => onSelectMode(m.key)}
              activeOpacity={0.8}
            >
              <View style={styles.tabTopRow}>
                <Text style={styles.tabIcon}>{m.icon}</Text>
                {isSelected && (
                  <View style={[styles.activeDot, { backgroundColor: m.color }]} />
                )}
              </View>

              <Text style={[styles.tabTitle, isSelected && { color: m.color }]}>
                {m.title}
              </Text>
              <Text style={styles.tabSubtitleText}>{m.subtitle}</Text>

              <Text style={styles.tabTime}>{rData.estimated_time_minutes} min</Text>
              <Text style={styles.tabDist}>{rData.distance_km} km</Text>

              <View
                style={[
                  styles.miniBadge,
                  { backgroundColor: isSelected ? safetyColor : '#E9D5FF' },
                ]}
              >
                <Text
                  style={[
                    styles.miniBadgeText,
                    { color: isSelected ? '#FFFFFF' : '#4E3486' },
                  ]}
                >
                  🛡️ {rData.safety_score}
                </Text>
              </View>
            </TouchableOpacity>
          );
        })}
      </View>

      {/* Active Route Details */}
      {activeRoute && (
        <ScrollView style={styles.detailsScroll} showsVerticalScrollIndicator={false}>
          <View style={styles.activeDetailsBox}>
            {/* Summary Line */}
            <View style={styles.activeSummaryRow}>
              <View>
                <Text style={styles.activeTimeText}>
                  {activeRoute.estimated_time_minutes} min{' '}
                  <Text style={styles.activeDistSub}>({activeRoute.distance_km} km)</Text>
                </Text>
                <Text style={styles.speedModelNote}>
                  ⚡ Est. driving time based on road speeds (no live traffic)
                </Text>

                <View style={styles.modeIndicatorPill}>
                  <Text
                    style={[
                      styles.modeIndicatorText,
                      { color: activeModeConfig.color },
                    ]}
                  >
                    {activeModeConfig.icon} {activeRoute.route_type?.toUpperCase()} ROUTE
                  </Text>
                </View>
              </View>

              <SafetyBadge
                score={activeRoute.safety_score}
                level={activeRoute.safety_level}
                size="medium"
              />
            </View>

            {/* Risk Factor Breakdown Chips */}
            <View style={styles.factorsGrid}>
              <View style={styles.factorCard}>
                <Text style={styles.factorIcon}>💡</Text>
                <Text style={styles.factorLabel}>Lighting</Text>
                <Text style={styles.factorValue}>
                  {timeOfDay === 'night' ? 'Night Monitored' : 'Well Illuminated'}
                </Text>
              </View>

              <View style={styles.factorCard}>
                <Text style={styles.factorIcon}>👥</Text>
                <Text style={styles.factorLabel}>Surveillance</Text>
                <Text style={styles.factorValue}>
                  {timeOfDay === 'night' ? 'Commercial Open' : 'Colleges & Retail'}
                </Text>
              </View>

              <View style={styles.factorCard}>
                <Text style={styles.factorIcon}>🚨</Text>
                <Text style={styles.factorLabel}>Emergency POI</Text>
                <Text style={styles.factorValue}>Safe Haven Proximity</Text>
              </View>

              <View style={styles.factorCard}>
                <Text style={styles.factorIcon}>📊</Text>
                <Text style={styles.factorLabel}>Crime Status</Text>
                <Text style={styles.factorValue}>Estimated (OSM)</Text>
              </View>
            </View>

            {/* Route Explanations */}
            {activeRoute.explanation && activeRoute.explanation.length > 0 && (
              <View style={styles.explanationSection}>
                <Text style={styles.explanationHeader}>Route Assessment & Trade-offs:</Text>
                {activeRoute.explanation.map((exp, idx) => (
                  <View key={idx} style={styles.reasonRow}>
                    <Text style={[styles.reasonCheck, { color: activeModeConfig.color }]}>✓</Text>
                    <Text style={styles.reasonText}>{exp}</Text>
                  </View>
                ))}
              </View>
            )}

            {/* Transparent Missing Data Notice */}
            <View style={styles.disclaimerBox}>
              <Text style={styles.disclaimerText}>
                ℹ️ <Text style={{ fontWeight: '700' }}>Note:</Text> Safety scores are calculated from street lighting hierarchy, verified OSM emergency POIs (police, 24/7 pharmacies, hospitals), and activity footfall. Missing local crime data is treated as unknown risk.
              </Text>
            </View>

            {/* Navigation CTA */}
            <TouchableOpacity
              style={[styles.startNavBtn, { backgroundColor: '#6C4AB6' }]}
              onPress={() => onStartNavigation && onStartNavigation(activeRoute)}
              activeOpacity={0.85}
            >
              <Text style={styles.startNavBtnText}>🚀 Start Safe Navigation</Text>
            </TouchableOpacity>
          </View>
        </ScrollView>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  cardContainer: {
    backgroundColor: '#FFFFFF',
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    paddingTop: 10,
    paddingHorizontal: 16,
    paddingBottom: 24,
    maxHeight: 460,
    shadowColor: '#4E3486',
    shadowOffset: { width: 0, height: -4 },
    shadowOpacity: 0.15,
    shadowRadius: 12,
    elevation: 12,
    borderWidth: 1,
    borderColor: '#EDE9FE',
  },
  dragHandle: {
    width: 44,
    height: 5,
    borderRadius: 3,
    backgroundColor: '#DDD6FE',
    alignSelf: 'center',
    marginBottom: 8,
  },
  headerRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 10,
  },
  headerTitleWrap: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    flexWrap: 'wrap',
  },
  sheetTitle: {
    fontSize: 18,
    fontWeight: '800',
    color: '#4E3486',
  },
  departureBadge: {
    backgroundColor: '#EDE9FE',
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 12,
  },
  departureBadgeText: {
    fontSize: 11,
    fontWeight: '700',
    color: '#6C4AB6',
  },
  closeBtn: {
    padding: 6,
    borderRadius: 14,
    backgroundColor: '#F5F3FF',
  },
  closeBtnText: {
    fontSize: 16,
    color: '#7C3AED',
    fontWeight: 'bold',
  },
  modeTabsRow: {
    flexDirection: 'row',
    gap: 8,
    marginBottom: 12,
  },
  tabCard: {
    flex: 1,
    backgroundColor: '#F8F7FF',
    borderRadius: 18,
    paddingVertical: 10,
    paddingHorizontal: 6,
    alignItems: 'center',
    borderWidth: 1.5,
    borderColor: '#EDE9FE',
    elevation: 2,
    shadowColor: '#6C4AB6',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
  },
  tabTopRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    width: '100%',
    position: 'relative',
    marginBottom: 4,
  },
  tabIcon: {
    fontSize: 18,
  },
  activeDot: {
    position: 'absolute',
    right: 2,
    top: 2,
    width: 6,
    height: 6,
    borderRadius: 3,
  },
  tabTitle: {
    fontSize: 11,
    fontWeight: '800',
    color: '#4E3486',
  },
  tabSubtitleText: {
    fontSize: 9,
    fontWeight: '600',
    color: '#8D72E1',
    marginTop: 1,
  },
  tabTime: {
    fontSize: 15,
    fontWeight: '900',
    color: '#1E1B4B',
    marginTop: 4,
  },
  tabDist: {
    fontSize: 10,
    color: '#6B7280',
    fontWeight: '500',
  },
  miniBadge: {
    marginTop: 6,
    paddingHorizontal: 7,
    paddingVertical: 2,
    borderRadius: 10,
  },
  miniBadgeText: {
    fontSize: 10,
    fontWeight: '800',
  },
  detailsScroll: {
    maxHeight: 280,
  },
  activeDetailsBox: {
    backgroundColor: '#FBFBFE',
    borderRadius: 18,
    padding: 14,
    borderWidth: 1.5,
    borderColor: '#EDE9FE',
  },
  activeSummaryRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  activeTimeText: {
    fontSize: 22,
    fontWeight: '900',
    color: '#1E1B4B',
  },
  activeDistSub: {
    fontSize: 15,
    fontWeight: '600',
    color: '#6B7280',
  },
  modeIndicatorPill: {
    marginTop: 3,
  },
  modeIndicatorText: {
    fontSize: 11,
    fontWeight: '800',
    letterSpacing: 0.3,
  },
  factorsGrid: {
    flexDirection: 'row',
    gap: 6,
    marginBottom: 12,
  },
  factorCard: {
    flex: 1,
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: 6,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#EDE9FE',
  },
  factorIcon: {
    fontSize: 14,
    marginBottom: 2,
  },
  factorLabel: {
    fontSize: 9,
    fontWeight: '700',
    color: '#6C4AB6',
  },
  factorValue: {
    fontSize: 8.5,
    color: '#4B5563',
    fontWeight: '600',
    textAlign: 'center',
    marginTop: 1,
  },
  speedModelNote: {
    fontSize: 11,
    color: '#6B7280',
    marginTop: 3,
    fontStyle: 'italic',
  },
  explanationSection: {
    borderTopWidth: 1,
    borderTopColor: '#EDE9FE',
    paddingTop: 10,
    marginBottom: 10,
  },
  explanationHeader: {
    fontSize: 12,
    fontWeight: '800',
    color: '#4E3486',
    marginBottom: 4,
  },
  reasonRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 6,
    marginTop: 4,
  },
  reasonCheck: {
    fontWeight: '900',
    fontSize: 13,
    marginTop: 1,
  },
  reasonText: {
    fontSize: 11.5,
    color: '#374151',
    flexShrink: 1,
    lineHeight: 16,
  },
  disclaimerBox: {
    backgroundColor: '#F5F3FF',
    borderRadius: 10,
    padding: 8,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#DDD6FE',
  },
  disclaimerText: {
    fontSize: 10,
    color: '#6C4AB6',
    lineHeight: 14,
  },
  startNavBtn: {
    borderRadius: 14,
    paddingVertical: 13,
    alignItems: 'center',
    shadowColor: '#6C4AB6',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 6,
    elevation: 4,
  },
  startNavBtnText: {
    color: '#FFFFFF',
    fontSize: 15,
    fontWeight: '800',
  },
});
