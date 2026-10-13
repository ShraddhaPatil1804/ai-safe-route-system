import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  Modal,
  TouchableOpacity,
  ScrollView,
  Linking,
  ActivityIndicator,
} from 'react-native';
import apiService from '../services/api';

export default function EmergencyModal({ visible, onClose, userCoords, onNavigateTo }) {
  const [facilities, setFacilities] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (visible && userCoords) {
      loadEmergency();
    }
  }, [visible, userCoords]);

  const loadEmergency = async () => {
    try {
      setLoading(true);
      const data = await apiService.getEmergencyFacilities(userCoords.latitude, userCoords.longitude);
      setFacilities(data);
    } catch (e) {
      console.warn('Error loading emergency facilities:', e);
    } finally {
      setLoading(false);
    }
  };

  const handleCall = (phone) => {
    Linking.openURL(`tel:${phone}`);
  };

  return (
    <Modal visible={visible} animationType="slide" transparent={true} onRequestClose={onClose}>
      <View style={styles.overlay}>
        <View style={styles.container}>
          {/* Header */}
          <View style={styles.header}>
            <View style={styles.titleRow}>
              <Text style={styles.sosEmoji}>🚨</Text>
              <View>
                <Text style={styles.title}>Emergency & SOS</Text>
                <Text style={styles.subtitle}>Instant helpline access & nearest safe facilities</Text>
              </View>
            </View>
            <TouchableOpacity onPress={onClose} style={styles.closeBtn}>
              <Text style={styles.closeBtnText}>✕</Text>
            </TouchableOpacity>
          </View>

          <ScrollView style={styles.content} showsVerticalScrollIndicator={false}>
            {/* Quick SOS Dials */}
            <Text style={styles.sectionHeading}>Emergency Helplines (Nashik / India)</Text>
            <View style={styles.helplinesGrid}>
              <TouchableOpacity
                style={[styles.helplineBtn, { backgroundColor: '#DC2626' }]}
                onPress={() => handleCall('112')}
              >
                <Text style={styles.helplineNum}>112</Text>
                <Text style={styles.helplineLabel}>National SOS</Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={[styles.helplineBtn, { backgroundColor: '#DB2777' }]}
                onPress={() => handleCall('1091')}
              >
                <Text style={styles.helplineNum}>1091</Text>
                <Text style={styles.helplineLabel}>Women Helpline</Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={[styles.helplineBtn, { backgroundColor: '#2563EB' }]}
                onPress={() => handleCall('100')}
              >
                <Text style={styles.helplineNum}>100</Text>
                <Text style={styles.helplineLabel}>Police</Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={[styles.helplineBtn, { backgroundColor: '#059669' }]}
                onPress={() => handleCall('108')}
              >
                <Text style={styles.helplineNum}>108</Text>
                <Text style={styles.helplineLabel}>Ambulance</Text>
              </TouchableOpacity>
            </View>

            {/* Nearest Facilities */}
            <Text style={[styles.sectionHeading, { marginTop: 18 }]}>Nearest Safe Facilities</Text>

            {loading ? (
              <ActivityIndicator size="large" color="#DC2626" style={{ marginVertical: 20 }} />
            ) : facilities ? (
              <View style={styles.facilitiesList}>
                {/* Police Station */}
                {facilities.police && (
                  <View style={styles.facilityCard}>
                    <View style={styles.facilityTop}>
                      <Text style={styles.facilityIcon}>👮</Text>
                      <View style={{ flex: 1 }}>
                        <Text style={styles.facilityName}>{facilities.police.name}</Text>
                        <Text style={styles.facilityDistance}>
                          {facilities.police.distance_km} km away ({facilities.police.distance_meters}m)
                        </Text>
                      </View>
                    </View>
                    <View style={styles.facilityActions}>
                      <TouchableOpacity
                        style={styles.actionCallBtn}
                        onPress={() => handleCall(facilities.police.phone)}
                      >
                        <Text style={styles.actionCallText}>📞 Call Police (112)</Text>
                      </TouchableOpacity>
                      <TouchableOpacity
                        style={styles.actionNavBtn}
                        onPress={() => {
                          onClose();
                          onNavigateTo && onNavigateTo(facilities.police);
                        }}
                      >
                        <Text style={styles.actionNavText}>📍 Navigate Here</Text>
                      </TouchableOpacity>
                    </View>
                  </View>
                )}

                {/* Hospital */}
                {facilities.hospital && (
                  <View style={styles.facilityCard}>
                    <View style={styles.facilityTop}>
                      <Text style={styles.facilityIcon}>🏥</Text>
                      <View style={{ flex: 1 }}>
                        <Text style={styles.facilityName}>{facilities.hospital.name}</Text>
                        <Text style={styles.facilityDistance}>
                          {facilities.hospital.distance_km} km away ({facilities.hospital.distance_meters}m)
                        </Text>
                      </View>
                    </View>
                    <View style={styles.facilityActions}>
                      <TouchableOpacity
                        style={styles.actionCallBtn}
                        onPress={() => handleCall(facilities.hospital.phone)}
                      >
                        <Text style={styles.actionCallText}>📞 Call Hospital (108)</Text>
                      </TouchableOpacity>
                      <TouchableOpacity
                        style={styles.actionNavBtn}
                        onPress={() => {
                          onClose();
                          onNavigateTo && onNavigateTo(facilities.hospital);
                        }}
                      >
                        <Text style={styles.actionNavText}>📍 Navigate Here</Text>
                      </TouchableOpacity>
                    </View>
                  </View>
                )}

                {/* Pharmacy */}
                {facilities.pharmacy && (
                  <View style={styles.facilityCard}>
                    <View style={styles.facilityTop}>
                      <Text style={styles.facilityIcon}>💊</Text>
                      <View style={{ flex: 1 }}>
                        <Text style={styles.facilityName}>{facilities.pharmacy.name}</Text>
                        <Text style={styles.facilityDistance}>
                          {facilities.pharmacy.distance_km} km away ({facilities.pharmacy.distance_meters}m)
                        </Text>
                      </View>
                    </View>
                    <View style={styles.facilityActions}>
                      <TouchableOpacity
                        style={styles.actionNavBtn}
                        onPress={() => {
                          onClose();
                          onNavigateTo && onNavigateTo(facilities.pharmacy);
                        }}
                      >
                        <Text style={styles.actionNavText}>📍 Navigate Here</Text>
                      </TouchableOpacity>
                    </View>
                  </View>
                )}
              </View>
            ) : (
              <Text style={styles.emptyText}>No facility information available.</Text>
            )}
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
  titleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  sosEmoji: {
    fontSize: 28,
  },
  title: {
    fontSize: 20,
    fontWeight: '800',
    color: '#111827',
  },
  subtitle: {
    fontSize: 12,
    color: '#6B7280',
  },
  closeBtn: {
    padding: 8,
  },
  closeBtnText: {
    fontSize: 20,
    color: '#9CA3AF',
    fontWeight: 'bold',
  },
  sectionHeading: {
    fontSize: 14,
    fontWeight: '700',
    color: '#374151',
    marginBottom: 10,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  helplinesGrid: {
    flexDirection: 'row',
    gap: 8,
  },
  helplineBtn: {
    flex: 1,
    borderRadius: 12,
    paddingVertical: 12,
    alignItems: 'center',
  },
  helplineNum: {
    fontSize: 18,
    fontWeight: '900',
    color: '#FFFFFF',
  },
  helplineLabel: {
    fontSize: 10,
    color: '#FFFFFF',
    marginTop: 2,
    fontWeight: '600',
  },
  facilitiesList: {
    gap: 12,
    marginBottom: 20,
  },
  facilityCard: {
    backgroundColor: '#F9FAFB',
    borderRadius: 14,
    padding: 12,
    borderWidth: 1,
    borderColor: '#E5E7EB',
  },
  facilityTop: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    marginBottom: 10,
  },
  facilityIcon: {
    fontSize: 24,
  },
  facilityName: {
    fontSize: 15,
    fontWeight: '700',
    color: '#111827',
  },
  facilityDistance: {
    fontSize: 12,
    color: '#059669',
    fontWeight: '600',
    marginTop: 2,
  },
  facilityActions: {
    flexDirection: 'row',
    gap: 8,
  },
  actionCallBtn: {
    flex: 1,
    backgroundColor: '#DC2626',
    borderRadius: 8,
    paddingVertical: 8,
    alignItems: 'center',
  },
  actionCallText: {
    color: '#FFFFFF',
    fontWeight: '700',
    fontSize: 12,
  },
  actionNavBtn: {
    flex: 1,
    backgroundColor: '#10B981',
    borderRadius: 8,
    paddingVertical: 8,
    alignItems: 'center',
  },
  actionNavText: {
    color: '#FFFFFF',
    fontWeight: '700',
    fontSize: 12,
  },
  emptyText: {
    textAlign: 'center',
    color: '#6B7280',
    marginVertical: 16,
  },
});
