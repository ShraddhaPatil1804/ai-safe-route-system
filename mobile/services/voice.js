import { Platform } from 'react-native';

let Speech = null;
try {
  Speech = require('expo-speech');
} catch (e) {
  // Graceful fallback if expo-speech is unavailable
}

let isMuted = false;

export const voiceService = {
  setMuted: (muted) => {
    isMuted = muted;
    if (muted) {
      voiceService.stop();
    }
  },

  isMuted: () => isMuted,

  speak: (text) => {
    if (isMuted || !text) return;

    try {
      if (Platform.OS === 'web' && typeof window !== 'undefined' && 'speechSynthesis' in window) {
        window.speechSynthesis.cancel();
        const utterance = new window.SpeechSynthesisUtterance(text);
        utterance.lang = 'en-IN'; // Indian English voice preferred
        utterance.rate = 0.95;
        window.speechSynthesis.speak(utterance);
      } else if (Speech && Speech.speak) {
        Speech.stop();
        Speech.speak(text, {
          language: 'en-IN',
          pitch: 1.0,
          rate: 0.95,
        });
      }
    } catch (e) {
      console.warn('Voice guidance warning:', e);
    }
  },

  stop: () => {
    try {
      if (Platform.OS === 'web' && typeof window !== 'undefined' && 'speechSynthesis' in window) {
        window.speechSynthesis.cancel();
      } else if (Speech && Speech.stop) {
        Speech.stop();
      }
    } catch (e) {
      // ignore
    }
  },
};

export default voiceService;
