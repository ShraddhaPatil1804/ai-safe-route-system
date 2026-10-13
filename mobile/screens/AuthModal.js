import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  Modal,
  TouchableOpacity,
  TextInput,
  Alert,
  ActivityIndicator,
} from 'react-native';
import apiService from '../services/api';
import storageService from '../services/storage';

export default function AuthModal({
  visible,
  onClose,
  currentUser,
  onAuthSuccess,
  onLogout,
  initialMode = 'login',
}) {
  const [isLogin, setIsLogin] = useState(initialMode !== 'signup');
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  useEffect(() => {
    if (visible) {
      setErrorMsg('');
      setPassword('');
      setIsLogin(initialMode !== 'signup');
    }
  }, [visible, initialMode]);

  const handleSubmit = async () => {
    setErrorMsg('');
    if (!email.trim() || !password.trim()) {
      setErrorMsg('Please enter both email and password.');
      return;
    }
    if (!isLogin && !name.trim()) {
      setErrorMsg('Please enter your full name.');
      return;
    }
    if (password.length < 6) {
      setErrorMsg('Password must be at least 6 characters.');
      return;
    }

    try {
      setLoading(true);
      let data;
      if (isLogin) {
        data = await apiService.login(email.trim(), password);
      } else {
        data = await apiService.signup(name.trim(), email.trim(), password);
      }

      const user = data.user || { name: name.trim(), email: email.trim() };
      onAuthSuccess && onAuthSuccess(user);
      onClose();
      Alert.alert('Welcome', `Successfully signed in as ${user.name}!`);
    } catch (e) {
      const msg = e.response?.data?.detail || 'Authentication failed. Please verify your credentials.';
      setErrorMsg(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = async () => {
    try {
      setLoading(true);
      await apiService.logout();
      onLogout && onLogout();
      onClose();
      Alert.alert('Signed Out', 'You have been signed out.');
    } catch (e) {
      console.warn('Logout error:', e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal visible={visible} animationType="slide" transparent={true} onRequestClose={onClose}>
      <View style={styles.overlay}>
        <View style={styles.container}>
          <View style={styles.header}>
            <Text style={styles.title}>
              {currentUser ? 'User Account' : (isLogin ? 'Sign In' : 'Create Account')}
            </Text>
            <TouchableOpacity onPress={onClose} style={styles.closeBtn}>
              <Text style={styles.closeBtnText}>✕</Text>
            </TouchableOpacity>
          </View>

          {currentUser ? (
            /* Logged In Profile View */
            <View style={styles.profileBox}>
              <View style={styles.avatarCircle}>
                <Text style={styles.avatarText}>{currentUser.name ? currentUser.name.charAt(0).toUpperCase() : '👤'}</Text>
              </View>
              <Text style={styles.profileName}>{currentUser.name}</Text>
              <Text style={styles.profileEmail}>{currentUser.email}</Text>
              <View style={styles.badge}>
                <Text style={styles.badgeText}>🛡️ Safety Verified Member</Text>
              </View>

              <TouchableOpacity
                style={styles.logoutBtn}
                onPress={handleLogout}
                disabled={loading}
              >
                {loading ? (
                  <ActivityIndicator color="#EF4444" />
                ) : (
                  <Text style={styles.logoutBtnText}>Log Out</Text>
                )}
              </TouchableOpacity>
            </View>
          ) : (
            /* Sign In / Sign Up Form */
            <>
              <Text style={styles.subtitle}>
                {isLogin
                  ? 'Access safety reporting and personalized navigation in Nashik'
                  : 'Join the safety-aware navigation network in Nashik'}
              </Text>

              {errorMsg ? (
                <View style={styles.errorBox}>
                  <Text style={styles.errorText}>⚠️ {errorMsg}</Text>
                </View>
              ) : null}

              {!isLogin && (
                <TextInput
                  style={styles.input}
                  placeholder="Your Full Name (e.g. Priya Sharma)"
                  placeholderTextColor="#9CA3AF"
                  value={name}
                  onChangeText={(t) => { setName(t); setErrorMsg(''); }}
                />
              )}

              <TextInput
                style={styles.input}
                placeholder="Email Address (e.g. priya@example.com)"
                placeholderTextColor="#9CA3AF"
                keyboardType="email-address"
                autoCapitalize="none"
                value={email}
                onChangeText={(t) => { setEmail(t); setErrorMsg(''); }}
              />

              <TextInput
                style={styles.input}
                placeholder="Password (min. 6 characters)"
                placeholderTextColor="#9CA3AF"
                secureTextEntry
                value={password}
                onChangeText={(t) => { setPassword(t); setErrorMsg(''); }}
              />

              <TouchableOpacity
                style={[styles.submitBtn, loading && { opacity: 0.7 }]}
                onPress={handleSubmit}
                disabled={loading}
              >
                {loading ? (
                  <ActivityIndicator color="#FFFFFF" />
                ) : (
                  <Text style={styles.submitBtnText}>{isLogin ? 'Sign In' : 'Create Account'}</Text>
                )}
              </TouchableOpacity>

              <TouchableOpacity
                style={styles.toggleBtn}
                onPress={() => { setIsLogin(!isLogin); setErrorMsg(''); }}
              >
                <Text style={styles.toggleText}>
                  {isLogin ? "Don't have an account? Sign Up" : 'Already have an account? Sign In'}
                </Text>
              </TouchableOpacity>
            </>
          )}
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.65)',
    justifyContent: 'center',
    padding: 20,
  },
  container: {
    backgroundColor: '#FFFFFF',
    borderRadius: 20,
    padding: 22,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.25,
    shadowRadius: 10,
    elevation: 8,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  title: {
    fontSize: 20,
    fontWeight: '800',
    color: '#111827',
  },
  closeBtn: {
    padding: 6,
  },
  closeBtnText: {
    fontSize: 18,
    color: '#9CA3AF',
    fontWeight: 'bold',
  },
  subtitle: {
    fontSize: 12,
    color: '#6B7280',
    marginTop: 4,
    marginBottom: 16,
  },
  errorBox: {
    backgroundColor: '#FEE2E2',
    borderWidth: 1,
    borderColor: '#F87171',
    borderRadius: 10,
    padding: 10,
    marginBottom: 12,
  },
  errorText: {
    color: '#B91C1C',
    fontSize: 12,
    fontWeight: '600',
  },
  input: {
    backgroundColor: '#F9FAFB',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#D1D5DB',
    padding: 13,
    fontSize: 14,
    color: '#111827',
    marginBottom: 12,
  },
  submitBtn: {
    backgroundColor: '#1E40AF',
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: 'center',
    marginTop: 6,
  },
  submitBtnText: {
    color: '#FFFFFF',
    fontSize: 15,
    fontWeight: '700',
  },
  toggleBtn: {
    marginTop: 16,
    alignItems: 'center',
  },
  toggleText: {
    fontSize: 13,
    color: '#2563EB',
    fontWeight: '600',
  },
  profileBox: {
    alignItems: 'center',
    paddingVertical: 16,
  },
  avatarCircle: {
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: '#DBEAFE',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 12,
  },
  avatarText: {
    fontSize: 28,
    fontWeight: '800',
    color: '#1E40AF',
  },
  profileName: {
    fontSize: 18,
    fontWeight: '700',
    color: '#111827',
  },
  profileEmail: {
    fontSize: 13,
    color: '#6B7280',
    marginTop: 2,
    marginBottom: 10,
  },
  badge: {
    backgroundColor: '#DCFCE7',
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 12,
    marginBottom: 20,
  },
  badgeText: {
    color: '#15803D',
    fontSize: 12,
    fontWeight: '700',
  },
  logoutBtn: {
    borderWidth: 1.5,
    borderColor: '#EF4444',
    borderRadius: 12,
    paddingVertical: 10,
    paddingHorizontal: 24,
    alignItems: 'center',
    width: '100%',
  },
  logoutBtnText: {
    color: '#EF4444',
    fontSize: 14,
    fontWeight: '700',
  },
});
