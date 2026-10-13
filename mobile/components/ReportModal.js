import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  Modal,
  TouchableOpacity,
  TextInput,
  ScrollView,
  Alert,
  ActivityIndicator,
} from 'react-native';
import apiService from '../services/api';

const REPORT_TYPES = [
  'Poor Lighting',
  'Isolated Area',
  'Suspicious Activity',
  'Harassment Concern',
  'Road Hazard / Issue',
  'Other Safety Concern',
];

const SEVERITIES = ['Low', 'Medium', 'High', 'Critical'];

export default function ReportModal({ visible, onClose, userCoords, onSuccess }) {
  const [reportType, setReportType] = useState(REPORT_TYPES[0]);
  const [severity, setSeverity] = useState('Medium');
  const [description, setDescription] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async () => {
    if (!userCoords) {
      Alert.alert('Location Required', 'Location coordinates are required to tag this report.');
      return;
    }

    try {
      setSubmitting(true);
      await apiService.submitReport({
        report_type: reportType,
        description: description.trim(),
        severity: severity,
        latitude: userCoords.latitude,
        longitude: userCoords.longitude,
      });

      Alert.alert(
        'Report Submitted',
        'Thank you. Your report has been submitted to the community safety network for review.'
      );
      setDescription('');
      onClose();
      if (onSuccess) onSuccess();
    } catch (e) {
      Alert.alert('Submission Error', 'Failed to submit report. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal visible={visible} animationType="slide" transparent={true} onRequestClose={onClose}>
      <View style={styles.overlay}>
        <View style={styles.container}>
          <View style={styles.header}>
            <View>
              <Text style={styles.title}>Submit Safety Report</Text>
              <Text style={styles.subtitle}>Help keep women safer across Nashik</Text>
            </View>
            <TouchableOpacity onPress={onClose} style={styles.closeBtn}>
              <Text style={styles.closeBtnText}>✕</Text>
            </TouchableOpacity>
          </View>

          <ScrollView showsVerticalScrollIndicator={false}>
            {/* Report Type Picker */}
            <Text style={styles.label}>Safety Concern Type:</Text>
            <View style={styles.typesGrid}>
              {REPORT_TYPES.map((t) => (
                <TouchableOpacity
                  key={t}
                  style={[styles.typeChip, reportType === t && styles.typeChipSelected]}
                  onPress={() => setReportType(t)}
                >
                  <Text style={[styles.typeChipText, reportType === t && styles.typeChipTextSelected]}>
                    {t}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>

            {/* Severity Picker */}
            <Text style={[styles.label, { marginTop: 14 }]}>Severity Level:</Text>
            <View style={styles.severityRow}>
              {SEVERITIES.map((s) => (
                <TouchableOpacity
                  key={s}
                  style={[
                    styles.severityBtn,
                    severity === s && styles.severityBtnSelected,
                    severity === s && s === 'High' && { borderColor: '#EA580C', backgroundColor: '#FFF7ED' },
                    severity === s && s === 'Critical' && { borderColor: '#DC2626', backgroundColor: '#FEF2F2' },
                  ]}
                  onPress={() => setSeverity(s)}
                >
                  <Text
                    style={[
                      styles.severityBtnText,
                      severity === s && { color: s === 'Critical' ? '#DC2626' : '#111827' },
                    ]}
                  >
                    {s}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>

            {/* Description */}
            <Text style={[styles.label, { marginTop: 14 }]}>Description (Optional):</Text>
            <TextInput
              style={styles.textInput}
              placeholder="e.g., Streetlights completely dark along this stretch, narrow alley..."
              placeholderTextColor="#9CA3AF"
              multiline
              numberOfLines={4}
              value={description}
              onChangeText={setDescription}
            />

            {/* Location Tag */}
            {userCoords && (
              <Text style={styles.locNote}>
                📍 Tagged at: {userCoords.latitude.toFixed(4)}, {userCoords.longitude.toFixed(4)}
              </Text>
            )}

            {/* Submit Button */}
            <TouchableOpacity
              style={[styles.submitBtn, submitting && { opacity: 0.7 }]}
              onPress={handleSubmit}
              disabled={submitting}
            >
              {submitting ? (
                <ActivityIndicator color="#FFFFFF" />
              ) : (
                <Text style={styles.submitBtnText}>Submit Safety Report</Text>
              )}
            </TouchableOpacity>
          </ScrollView>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.6)',
    justifyContent: 'flex-end',
  },
  container: {
    backgroundColor: '#FFFFFF',
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    maxHeight: '85%',
    padding: 20,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  title: {
    fontSize: 18,
    fontWeight: '800',
    color: '#111827',
  },
  subtitle: {
    fontSize: 12,
    color: '#6B7280',
    marginTop: 2,
  },
  closeBtn: {
    padding: 8,
  },
  closeBtnText: {
    fontSize: 18,
    color: '#9CA3AF',
    fontWeight: 'bold',
  },
  label: {
    fontSize: 13,
    fontWeight: '700',
    color: '#374151',
    marginBottom: 8,
  },
  typesGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  typeChip: {
    backgroundColor: '#F3F4F6',
    borderRadius: 16,
    paddingHorizontal: 12,
    paddingVertical: 7,
    borderWidth: 1,
    borderColor: '#E5E7EB',
  },
  typeChipSelected: {
    backgroundColor: '#EEF2FF',
    borderColor: '#4F46E5',
  },
  typeChipText: {
    fontSize: 12,
    color: '#4B5563',
    fontWeight: '600',
  },
  typeChipTextSelected: {
    color: '#4F46E5',
    fontWeight: '700',
  },
  severityRow: {
    flexDirection: 'row',
    gap: 8,
  },
  severityBtn: {
    flex: 1,
    backgroundColor: '#F3F4F6',
    borderRadius: 10,
    paddingVertical: 8,
    alignItems: 'center',
    borderWidth: 1.5,
    borderColor: '#E5E7EB',
  },
  severityBtnSelected: {
    borderColor: '#2563EB',
    backgroundColor: '#EFF6FF',
  },
  severityBtnText: {
    fontSize: 12,
    fontWeight: '700',
    color: '#4B5563',
  },
  textInput: {
    backgroundColor: '#F9FAFB',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#D1D5DB',
    padding: 12,
    fontSize: 13,
    color: '#111827',
    textAlignVertical: 'top',
    height: 90,
  },
  locNote: {
    fontSize: 11,
    color: '#6B7280',
    marginTop: 8,
  },
  submitBtn: {
    backgroundColor: '#4F46E5',
    borderRadius: 12,
    paddingVertical: 13,
    alignItems: 'center',
    marginTop: 18,
    marginBottom: 12,
  },
  submitBtnText: {
    color: '#FFFFFF',
    fontSize: 15,
    fontWeight: '700',
  },
});
