/**
 * Settings store (zustand) — UI preferences and the backend
 * API URL. Persisted to AsyncStorage via apiService so the
 * config survives app restarts.
 */
import { create } from "zustand"
import AsyncStorage from "@react-native-async-storage/async-storage"

const SETTINGS_KEY = "ant-mobile-settings"
const DEFAULTS = {
  apiUrl: "http://10.0.2.2:8000", // Android emulator -> host
  theme: "system", // 'light' | 'dark' | 'system'
  hapticsEnabled: true,
  pushNotificationsEnabled: true,
}

export const useSettingsStore = create((set, get) => ({
  ...DEFAULTS,
  loaded: false,

  load: async () => {
    try {
      const raw = await AsyncStorage.getItem(SETTINGS_KEY)
      if (raw) {
        const stored = JSON.parse(raw)
        set({ ...DEFAULTS, ...stored, loaded: true })
        return
      }
    } catch (e) {
      // Corrupted JSON or storage error — fall back to defaults
    }
    set({ loaded: true })
  },

  set: async (key, value) => {
    set({ [key]: value })
    const current = { ...get() }
    delete current.loaded
    await AsyncStorage.setItem(SETTINGS_KEY, JSON.stringify(current))
  },

  reset: async () => {
    set({ ...DEFAULTS, loaded: true })
    await AsyncStorage.removeItem(SETTINGS_KEY)
  },
}))
