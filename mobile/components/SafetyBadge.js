import React from 'react';
import { View, Text, StyleSheet } from 'react-native';

export const getSafetyColor = (score) => {
  if (score >= 80) return '#10B981'; // Green (Very Safe)
  if (score >= 65) return '#059669'; // Emerald (Safe)
  if (score >= 50) return '#D97706'; // Amber/Yellow (Moderate)
  if (score >= 35) return '#EA580C'; // Orange (Risky)
  return '#DC2626'; // Red (High Risk)
};

export const getSafetyBgColor = (score) => {
  if (score >= 80) return '#ECFDF5';
  if (score >= 65) return '#F0FDF4';
  if (score >= 50) return '#FFFBEB';
  if (score >= 35) return '#FFF7ED';
  return '#FEF2F2';
};

export default function SafetyBadge({ score, level, size = 'medium' }) {
  const color = getSafetyColor(score);
  const bgColor = getSafetyBgColor(score);
  const isSmall = size === 'small';

  return (
    <View style={[styles.badgeContainer, { backgroundColor: bgColor, borderColor: color }]}>
      <Text style={[styles.scoreText, { color }, isSmall && styles.scoreTextSmall]}>
        🛡️ {score}/100
      </Text>
      {level ? (
        <Text style={[styles.levelText, { color }, isSmall && styles.levelTextSmall]}>
          {level}
        </Text>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  badgeContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 16,
    borderWidth: 1,
    gap: 6,
  },
  scoreText: {
    fontSize: 13,
    fontWeight: '700',
  },
  scoreTextSmall: {
    fontSize: 11,
  },
  levelText: {
    fontSize: 12,
    fontWeight: '600',
  },
  levelTextSmall: {
    fontSize: 10,
  },
});
