/**
 * Auth state (zustand) — wraps the API service to expose
 * login/logout/register + the current user as a hook.
 *
 * Token persistence is delegated to apiService (which writes to
 * AsyncStorage under the hood). This store is a thin layer on top.
 */
import { create } from "zustand"
import apiService from "../services/api"

export const useAuthStore = create((set) => ({
  user: null,
  loading: false,
  error: null,
  isAuthenticated: false,

  login: async (username, password) => {
    set({ loading: true, error: null })
    try {
      const user = await apiService.login(username, password)
      set({ user, loading: false, isAuthenticated: true })
      return user
    } catch (err) {
      set({ error: err.message, loading: false })
      throw err
    }
  },

  register: async (username, email, password) => {
    set({ loading: true, error: null })
    try {
      const user = await apiService.register(username, email, password)
      set({ user, loading: false, isAuthenticated: true })
      return user
    } catch (err) {
      set({ error: err.message, loading: false })
      throw err
    }
  },

  logout: async () => {
    try {
      await apiService.logout()
    } finally {
      set({ user: null, isAuthenticated: false, error: null })
    }
  },

  clearError: () => set({ error: null }),
}))
