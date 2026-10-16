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
                <Text style={styles.title}>Emergency & SOS Hub</Text>
                <Text style={styles.subtitle}>Verified helplines & 24/7 safe havens in Nashik</Text>
              </View>
            </View>
            <TouchableOpacity onPress={onClose} style={styles.closeBtn} activeOpacity={0.7}>
              <Text style={styles.closeBtnText}>✕</Text>
            </TouchableOpacity>
          </View>

          <ScrollView style={styles.content} showsVerticalScrollIndicator={false}>
            {/* Quick SOS Dials */}
            <Text style={styles.sectionHeading}>Emergency Helplines</Text>
            <View style={styles.helplinesGrid}>
              <TouchableOpacity
                style={[styles.helplineBtn, { backgroundColor: '#DC2626' }]}
                onPress={() => handleCall('112')}
                activeOpacity={0.8}
              >
                <Text style={styles.helplineNum}>112</Text>
                <Text style={styles.helplineLabel}>National SOS</Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={[styles.helplineBtn, { backgroundColor: '#DB2777' }]}
                onPress={() => handleCall('1091')}
                activeOpacity={0.8}
              >
                <Text style={styles.helplineNum}>1091</Text>
                <Text style={styles.helplineLabel}>Women Helpline</Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={[styles.helplineBtn, { backgroundColor: '#6C4AB6' }]}
                onPress={() => handleCall('100')}
                activeOpacity={0.8}
              >
                <Text style={styles.helplineNum}>100</Text>
                <Text style={styles.helplineLabel}>Police</Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={[styles.helplineBtn, { backgroundColor: '#059669' }]}
                onPress={() => handleCall('108')}
                activeOpacity={0.8}
              >
                <Text style={styles.helplineNum}>108</Text>
                <Text style={styles.helplineLabel}>Ambulance</Text>
              </TouchableOpacity>
            </View>

            {/* Nearest Facilities */}
            <Text style={[styles.sectionHeading, { marginTop: 20 }]}>Verified Safe Havens Nearby</Text>

            {loading ? (
              <ActivityIndicator size="large" color="#6C4AB6" style={{ marginVertical: 24 }} />
            ) : facilities ? (
              <View style={styles.facilitiesList}>
                {/* 24/7 Pharmacy Safe Haven */}
                {facilities.pharmacy_24h && (
                  <View style={[styles.facilityCard, styles.safeHavenCard]}>
                    <View style={styles.badge24h}>
                      <Text style={styles.badge24hText}>🌟 24/7 Verified Safe Haven</Text>
                    </View>
                    <View style={styles.facilityTop}>
                      <Text style={styles.facilityIcon}>🏪💊</Text>
                      <View style={{ flex: 1 }}>
                        <Text style={styles.facilityName}>{facilities.pharmacy_24h.name}</Text>
                        <Text style={styles.facilityDistance}>
                          {facilities.pharmacy_24h.distance_km} km away ({facilities.pharmacy_24h.distance_meters}m)
                        </Text>
                      </View>
                    </View>
                    <View style={styles.facilityActions}>
                      <TouchableOpacity
                        style={[styles.actionCallBtn, { backgroundColor: '#6C4AB6' }]}
                        onPress={() => handleCall(facilities.pharmacy_24h.phone || '102')}
                      >
                        <Text style={styles.actionCallText}>📞 Call Pharmacy</Text>
                      </TouchableOpacity>
                      <TouchableOpacity
                        style={styles.actionNavBtn}
                        onPress={() => {
                          onClose();
                          onNavigateTo && onNavigateTo(facilities.pharmacy_24h);
                        }}
                      >
                        <Text style={styles.actionNavText}>📍 Navigate to Haven</Text>
                      </TouchableOpacity>
                    </View>
                  </View>
                )}

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
                        onPress={() => handleCall(facilities.police.phone || '112')}
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
                        style={[styles.actionCallBtn, { backgroundColor: '#059669' }]}
                        onPress={() => handleCall(facilities.hospital.phone || '108')}
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

                {/* Regular Pharmacy */}
                {facilities.pharmacy && facilities.pharmacy.name !== facilities.pharmacy_24h?.name && (
                  <View style={styles.facilityCard}>
                    <View style={styles.facilityTop}>
                      <Text style={styles.facilityIcon}>💊</Text>
                      <View style={{ flex: 1 }}>
                        <Text style={styles.facilityName}>{facilities.pharmacy.name}</Text>
                        <Text style={styles.facilityDistance}>
                          {facilities.pharmacy.distance_km} km away ({facilities.pharmacy.distance_meters}m) • {facilities.pharmacy.opening_hours || 'Daytime'}
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
              <Text style={styles.emptyText}>No emergency facility information available.</Text>
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
    backgroundColor: 'rgba(30, 27, 75, 0.65)',
    justifyContent: 'flex-end',
  },
  container: {
    backgroundColor: '#FFFFFF',
    borderTopLeftRadius: 28,
    borderTopRightRadius: 28,
    maxHeight: '85%',
    padding: 20,
    borderWidth: 1,
    borderColor: '#EDE9FE',
    shadowColor: '#4E3486',
    shadowOffset: { width: 0, height: -6 },
    shadowOpacity: 0.2,
    shadowRadius: 16,
    elevation: 16,
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
    gap: 12,
  },
  sosEmoji: {
    fontSize: 30,
  },
  title: {
    fontSize: 20,
    fontWeight: '900',
    color: '#4E3486',
  },
  subtitle: {
    fontSize: 12,
    color: '#6B7280',
    marginTop: 1,
  },
  closeBtn: {
    padding: 8,
    borderRadius: 16,
    backgroundColor: '#F5F3FF',
  },
  closeBtnText: {
    fontSize: 18,
    color: '#7C3AED',
    fontWeight: 'bold',
  },
  sectionHeading: {
    fontSize: 13,
    fontWeight: '800',
    color: '#6C4AB6',
    marginBottom: 10,
    textTransform: 'uppercase',
    letterSpacing: 0.6,
  },
  helplinesGrid: {
    flexDirection: 'row',
    gap: 8,
  },
  helplineBtn: {
    flex: 1,
    borderRadius: 14,
    paddingVertical: 12,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.15,
    shadowRadius: 4,
    elevation: 3,
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
    fontWeight: '700',
  },
  facilitiesList: {
    gap: 12,
    marginBottom: 20,
  },
  facilityCard: {
    backgroundColor: '#F8F7FF',
    borderRadius: 18,
    padding: 14,
    borderWidth: 1.5,
    borderColor: '#EDE9FE',
  },
  safeHavenCard: {
    borderColor: '#C4B5FD',
    backgroundColor: '#FAF5FF',
  },
  badge24h: {
    alignSelf: 'flex-start',
    backgroundColor: '#EDE9FE',
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 8,
    marginBottom: 8,
  },
  badge24hText: {
    color: '#6C4AB6',
    fontSize: 11,
    fontWeight: '800',
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
    fontWeight: '800',
    color: '#1E1B4B',
  },
  facilityDistance: {
    fontSize: 12,
    color: '#6C4AB6',
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
    borderRadius: 12,
    paddingVertical: 9,
    alignItems: 'center',
  },
  actionCallText: {
    color: '#FFFFFF',
    fontWeight: '800',
    fontSize: 12,
  },
  actionNavBtn: {
    flex: 1,
    backgroundColor: '#10B981',
    borderRadius: 12,
    paddingVertical: 9,
    alignItems: 'center',
  },
  actionNavText: {
    color: '#FFFFFF',
    fontWeight: '800',
    fontSize: 12,
  },
  emptyText: {
    textAlign: 'center',
    color: '#6B7280',
    marginVertical: 16,
  },
});
