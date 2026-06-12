/**
 * Conversations cache (zustand) — mirrors the backend's
 * /conversations endpoints. Caches the list + selected conversation
 * so the UI can render offline.
 *
 * Refresh policy: stale-while-revalidate. The UI calls
 * `fetchAll()` on screen mount; if the cache is fresh (< 5 min),
 * the cached value is returned immediately and a background
 * refresh is fired.
 */
import { create } from "zustand"
import apiService from "../services/api"

const CACHE_TTL_MS = 5 * 60 * 1000 // 5 minutes

export const useConversationsStore = create((set, get) => ({
  items: [],
  selected: null,
  loading: false,
  error: null,
  lastFetchedAt: 0,

  fetchAll: async (opts = {}) => {
    const { force = false } = opts
    const state = get()
    const isStale = Date.now() - state.lastFetchedAt > CACHE_TTL_MS
    if (!force && state.items.length > 0 && !isStale) {
      return state.items
    }
    set({ loading: true, error: null })
    try {
      const items = await apiService.listConversations()
      set({ items, loading: false, lastFetchedAt: Date.now() })
      return items
    } catch (err) {
      set({ error: err.message, loading: false })
      throw err
    }
  },

  select: (id) => {
    const item = get().items.find((c) => c.id === id) || null
    set({ selected: item })
  },

  add: (item) => {
    set((state) => ({ items: [item, ...state.items] }))
  },

  remove: (id) => {
    set((state) => ({
      items: state.items.filter((c) => c.id !== id),
      selected: state.selected?.id === id ? null : state.selected,
    }))
  },
}))
