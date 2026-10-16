import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  SafeAreaView,
} from 'react-native';
import voiceService from '../services/voice';
import SafetyBadge from './SafetyBadge';

const MANEUVER_ICONS = {
  depart: '⬆️',
  straight: '⬆️',
  left: '⬅️',
  right: '➡️',
  slight_left: '↖️',
  slight_right: '↗️',
  sharp_left: '↩️',
  sharp_right: '↪️',
  uturn: '🔄',
  arrive: '🏁',
};

export default function NavigationOverlay({
  route,
  currentStepIndex,
  onNextStep,
  onPrevStep,
  onExitNavigation,
  isSimulating,
  onToggleSimulation,
  totalDistanceKm,
  totalMinutes,
}) {
  const [muted, setMuted] = useState(false);

  const steps = route?.steps || [];
  const currentStep = steps[currentStepIndex] || steps[0];
  const nextStep = steps[currentStepIndex + 1];

  useEffect(() => {
    if (currentStep && currentStep.instruction) {
      const announceText = `${currentStep.distance_text ? `In ${currentStep.distance_text}, ` : ''}${currentStep.instruction}`;
      voiceService.speak(announceText);
    }
  }, [currentStepIndex]);

  const toggleMute = () => {
    const next = !muted;
    setMuted(next);
    voiceService.setMuted(next);
  };

  // Deterministic travel-time display (derived from road segment lengths and speed limits)
  const safeMinutes = (typeof totalMinutes === 'number' && !isNaN(totalMinutes)) ? totalMinutes : 1;
  const safeDistance = (typeof totalDistanceKm === 'number' && !isNaN(totalDistanceKm)) ? totalDistanceKm : 0.0;
  const now = new Date();
  const arrivalDate = new Date(now.getTime() + safeMinutes * 60000);
  const arrivalTimeStr = arrivalDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

  const icon = currentStep ? (MANEUVER_ICONS[currentStep.modifier] || '⬆️') : '⬆️';

  return (
    <View style={styles.overlayContainer} pointerEvents="box-none">
      {/* Top Google Maps-style Direction Card */}
      <SafeAreaView style={styles.topSafe}>
        <View style={styles.directionCard}>
          <View style={styles.cardHeader}>
            <View style={styles.maneuverIconBox}>
              <Text style={styles.maneuverIcon}>{icon}</Text>
            </View>

            <View style={styles.instructionTextBox}>
              {currentStep?.distance_text ? (
                <Text style={styles.distanceText}>In {currentStep.distance_text}</Text>
              ) : null}
              <Text style={styles.primaryInstruction} numberOfLines={2}>
                {currentStep?.instruction || 'Proceed along recommended route'}
              </Text>
            </View>

            <TouchableOpacity style={styles.soundBtn} onPress={toggleMute}>
              <Text style={styles.soundBtnText}>{muted ? '🔇' : '🔊'}</Text>
            </TouchableOpacity>
          </View>

          {/* Next Maneuver Preview */}
          {nextStep && (
            <View style={styles.nextManeuverRow}>
              <Text style={styles.nextMiniIcon}>{MANEUVER_ICONS[nextStep.modifier] || '⬆️'}</Text>
              <Text style={styles.nextText} numberOfLines={1}>
                Then: {nextStep.instruction}
              </Text>
            </View>
          )}

          {/* Safety Reassurance Banner */}
          <View style={styles.safetyReassuranceRow}>
            <Text style={styles.reassuranceText}>
              🛡️ Safe Corridor Active: {currentStep?.safety_level || 'Safe'} ({currentStep?.safety_score || 80}/100)
            </Text>
          </View>
        </View>
      </SafeAreaView>

      {/* Center Step Switcher / Simulation Controller */}
      <View style={styles.floatingControlsRow}>
        <TouchableOpacity
          style={[styles.stepNavBtn, currentStepIndex === 0 && styles.stepNavBtnDisabled]}
          onPress={onPrevStep}
          disabled={currentStepIndex === 0}
        >
          <Text style={styles.stepNavBtnText}>◀ Prev</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.simBtn, isSimulating && styles.simBtnActive]}
          onPress={onToggleSimulation}
        >
          <Text style={styles.simBtnText}>
            {isSimulating ? '⏸ Pause Ride' : '▶ Simulate Drive'}
          </Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.stepNavBtn, currentStepIndex >= steps.length - 1 && styles.stepNavBtnDisabled]}
          onPress={onNextStep}
          disabled={currentStepIndex >= steps.length - 1}
        >
          <Text style={styles.stepNavBtnText}>Next ▶</Text>
        </TouchableOpacity>
      </View>

      {/* Bottom Google Maps Summary & Controls */}
      <View style={styles.bottomBar}>
        <View style={styles.tripSummaryRow}>
          <View>
            <Text style={styles.etaText}>
              {safeMinutes} <Text style={styles.minUnit}>min</Text>
            </Text>
            <Text style={styles.distEtaSub}>
              {safeDistance} km • ETA {arrivalTimeStr} (Road speeds)
            </Text>
          </View>

          <SafetyBadge
            score={route?.safety_score || 85}
            level={route?.safety_level || 'Safe'}
            size="small"
          />

          <TouchableOpacity style={styles.exitBtn} onPress={onExitNavigation}>
            <Text style={styles.exitBtnText}>✕ Exit</Text>
          </TouchableOpacity>
        </View>

        {/* Street Progress */}
        <View style={styles.stepProgressRow}>
          <Text style={styles.stepProgressText}>
            Step {currentStepIndex + 1} of {steps.length} • {currentStep?.street_name || 'Current Road'}
          </Text>
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  overlayContainer: {
    ...StyleSheet.absoluteFillObject,
    justifyContent: 'space-between',
    zIndex: 50,
  },
  topSafe: {
    paddingHorizontal: 12,
    paddingTop: 10,
  },
  directionCard: {
    backgroundColor: '#0F766E', // Google Maps navigation deep green
    borderRadius: 16,
    padding: 14,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 8,
  },
  cardHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  maneuverIconBox: {
    width: 52,
    height: 52,
    borderRadius: 26,
    backgroundColor: 'rgba(255, 255, 255, 0.2)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  maneuverIcon: {
    fontSize: 28,
  },
  instructionTextBox: {
    flex: 1,
  },
  distanceText: {
    fontSize: 22,
    fontWeight: '900',
    color: '#FFFFFF',
    letterSpacing: 0.5,
  },
  primaryInstruction: {
    fontSize: 16,
    fontWeight: '700',
    color: '#F0FDFA',
    marginTop: 2,
  },
  soundBtn: {
    padding: 8,
    backgroundColor: 'rgba(255, 255, 255, 0.2)',
    borderRadius: 20,
  },
  soundBtnText: {
    fontSize: 18,
  },
  nextManeuverRow: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(0, 0, 0, 0.2)',
    borderRadius: 8,
    paddingHorizontal: 10,
    paddingVertical: 6,
    marginTop: 10,
    gap: 8,
  },
  nextMiniIcon: {
    fontSize: 14,
  },
  nextText: {
    fontSize: 12,
    color: '#CCFBF1',
    fontWeight: '600',
    flex: 1,
  },
  safetyReassuranceRow: {
    marginTop: 8,
  },
  reassuranceText: {
    fontSize: 11,
    color: '#A7F3D0',
    fontWeight: '700',
  },
  floatingControlsRow: {
    flexDirection: 'row',
    alignSelf: 'center',
    backgroundColor: '#FFFFFF',
    borderRadius: 24,
    paddingHorizontal: 12,
    paddingVertical: 6,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.2,
    shadowRadius: 6,
    elevation: 6,
    gap: 10,
    alignItems: 'center',
  },
  stepNavBtn: {
    paddingVertical: 6,
    paddingHorizontal: 10,
  },
  stepNavBtnDisabled: {
    opacity: 0.3,
  },
  stepNavBtnText: {
    fontSize: 12,
    fontWeight: '700',
    color: '#374151',
  },
  simBtn: {
    backgroundColor: '#2563EB',
    borderRadius: 16,
    paddingVertical: 7,
    paddingHorizontal: 14,
  },
  simBtnActive: {
    backgroundColor: '#DC2626',
  },
  simBtnText: {
    color: '#FFFFFF',
    fontSize: 12,
    fontWeight: '700',
  },
  bottomBar: {
    backgroundColor: '#FFFFFF',
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    paddingHorizontal: 16,
    paddingTop: 14,
    paddingBottom: 24,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: -3 },
    shadowOpacity: 0.15,
    shadowRadius: 8,
    elevation: 8,
  },
  tripSummaryRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  etaText: {
    fontSize: 24,
    fontWeight: '900',
    color: '#059669',
  },
  minUnit: {
    fontSize: 16,
    fontWeight: '600',
    color: '#059669',
  },
  distEtaSub: {
    fontSize: 12,
    color: '#6B7280',
    marginTop: 2,
    fontWeight: '500',
  },
  exitBtn: {
    backgroundColor: '#FEE2E2',
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 20,
  },
  exitBtnText: {
    color: '#DC2626',
    fontWeight: '800',
    fontSize: 13,
  },
  stepProgressRow: {
    borderTopWidth: 1,
    borderTopColor: '#F3F4F6',
    marginTop: 10,
    paddingTop: 6,
  },
  stepProgressText: {
    fontSize: 11,
    color: '#9CA3AF',
    textAlign: 'center',
    fontWeight: '600',
  },
});
