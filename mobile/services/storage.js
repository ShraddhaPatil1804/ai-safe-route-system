import { Platform } from 'react-native';
import * as SecureStore from 'expo-secure-store';

const TOKEN_KEY = 'women_nav_auth_token';
const USER_KEY = 'women_nav_auth_user';

export const storageService = {
  saveToken: async (token) => {
    try {
      if (Platform.OS === 'web') {
        if (typeof window !== 'undefined' && window.localStorage) {
          window.localStorage.setItem(TOKEN_KEY, token);
        }
      } else {
        await SecureStore.setItemAsync(TOKEN_KEY, token);
      }
    } catch (e) {
      console.warn('Storage saveToken warning:', e);
    }
  },

  getToken: async () => {
    try {
      if (Platform.OS === 'web') {
        if (typeof window !== 'undefined' && window.localStorage) {
          return window.localStorage.getItem(TOKEN_KEY);
        }
        return null;
      } else {
        return await SecureStore.getItemAsync(TOKEN_KEY);
      }
    } catch (e) {
      console.warn('Storage getToken warning:', e);
      return null;
    }
  },

  removeToken: async () => {
    try {
      if (Platform.OS === 'web') {
        if (typeof window !== 'undefined' && window.localStorage) {
          window.localStorage.removeItem(TOKEN_KEY);
        }
      } else {
        await SecureStore.deleteItemAsync(TOKEN_KEY);
      }
    } catch (e) {
      console.warn('Storage removeToken warning:', e);
    }
  },

  saveUser: async (user) => {
    try {
      const data = JSON.stringify(user);
      if (Platform.OS === 'web') {
        if (typeof window !== 'undefined' && window.localStorage) {
          window.localStorage.setItem(USER_KEY, data);
        }
      } else {
        await SecureStore.setItemAsync(USER_KEY, data);
      }
    } catch (e) {
      console.warn('Storage saveUser warning:', e);
    }
  },

  getUser: async () => {
    try {
      let str = null;
      if (Platform.OS === 'web') {
        if (typeof window !== 'undefined' && window.localStorage) {
          str = window.localStorage.getItem(USER_KEY);
        }
      } else {
        str = await SecureStore.getItemAsync(USER_KEY);
      }
      return str ? JSON.parse(str) : null;
    } catch (e) {
      console.warn('Storage getUser warning:', e);
      return null;
    }
  },

  removeUser: async () => {
    try {
      if (Platform.OS === 'web') {
        if (typeof window !== 'undefined' && window.localStorage) {
          window.localStorage.removeItem(USER_KEY);
        }
      } else {
        await SecureStore.deleteItemAsync(USER_KEY);
      }
    } catch (e) {
      console.warn('Storage removeUser warning:', e);
    }
  },

  clearAll: async () => {
    await storageService.removeToken();
    await storageService.removeUser();
  }
};

export default storageService;
