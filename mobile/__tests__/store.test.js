/**
 * Tests for the zustand stores added in Phase 8 (2026-06-08).
 */
import { useAuthStore } from "../src/store/auth"
import { useConversationsStore } from "../src/store/conversations"
import { useSettingsStore } from "../src/store/settings"

// ── Auth store ────────────────────────────────────────────────────────────
describe("useAuthStore", () => {
  beforeEach(() => {
    useAuthStore.setState({
      user: null,
      loading: false,
      error: null,
      isAuthenticated: false,
    })
  })

  test("initial state is logged out", () => {
    const s = useAuthStore.getState()
    expect(s.user).toBeNull()
    expect(s.isAuthenticated).toBe(false)
    expect(s.loading).toBe(false)
    expect(s.error).toBeNull()
  })

  test("clearError resets error to null", () => {
    useAuthStore.setState({ error: "oops" })
    useAuthStore.getState().clearError()
    expect(useAuthStore.getState().error).toBeNull()
  })

  test("logout clears user and isAuthenticated", () => {
    useAuthStore.setState({ user: { id: 1 }, isAuthenticated: true })
    return useAuthStore.getState().logout().then(() => {
      const s = useAuthStore.getState()
      expect(s.user).toBeNull()
      expect(s.isAuthenticated).toBe(false)
    })
  })
})

// ── Conversations store ───────────────────────────────────────────────────
describe("useConversationsStore", () => {
  beforeEach(() => {
    useConversationsStore.setState({
      items: [],
      selected: null,
      loading: false,
      error: null,
      lastFetchedAt: 0,
    })
  })

  test("add prepends new conversation", () => {
    const { add } = useConversationsStore.getState()
    add({ id: 1, title: "First" })
    add({ id: 2, title: "Second" })
    const items = useConversationsStore.getState().items
    expect(items).toHaveLength(2)
    expect(items[0].id).toBe(2) // most recent first
    expect(items[1].id).toBe(1)
  })

  test("select finds item by id", () => {
    useConversationsStore.setState({
      items: [
        { id: 1, title: "A" },
        { id: 2, title: "B" },
      ],
    })
    useConversationsStore.getState().select(2)
    expect(useConversationsStore.getState().selected).toEqual({ id: 2, title: "B" })
  })

  test("select returns null for missing id", () => {
    useConversationsStore.setState({ items: [{ id: 1 }] })
    useConversationsStore.getState().select(99)
    expect(useConversationsStore.getState().selected).toBeNull()
  })

  test("remove filters items and clears selected if matching", () => {
    useConversationsStore.setState({
      items: [
        { id: 1, title: "A" },
        { id: 2, title: "B" },
      ],
      selected: { id: 1, title: "A" },
    })
    useConversationsStore.getState().remove(1)
    const s = useConversationsStore.getState()
    expect(s.items).toHaveLength(1)
    expect(s.items[0].id).toBe(2)
    expect(s.selected).toBeNull()
  })

  test("remove keeps selected if not matching", () => {
    useConversationsStore.setState({
      items: [
        { id: 1, title: "A" },
        { id: 2, title: "B" },
      ],
      selected: { id: 2, title: "B" },
    })
    useConversationsStore.getState().remove(1)
    const s = useConversationsStore.getState()
    expect(s.items).toHaveLength(1)
    expect(s.selected).toEqual({ id: 2, title: "B" })
  })
})

// ── Settings store ────────────────────────────────────────────────────────
describe("useSettingsStore", () => {
  beforeEach(() => {
    useSettingsStore.setState({
      apiUrl: "http://10.0.2.2:8000",
      theme: "system",
      hapticsEnabled: true,
      pushNotificationsEnabled: true,
      loaded: false,
    })
  })

  test("initial state has defaults", () => {
    const s = useSettingsStore.getState()
    expect(s.apiUrl).toBe("http://10.0.2.2:8000")
    expect(s.theme).toBe("system")
    expect(s.hapticsEnabled).toBe(true)
    expect(s.pushNotificationsEnabled).toBe(true)
    expect(s.loaded).toBe(false)
  })

  test("reset restores defaults and clears loaded", async () => {
    useSettingsStore.setState({ theme: "dark", loaded: true })
    await useSettingsStore.getState().reset()
    const s = useSettingsStore.getState()
    expect(s.theme).toBe("system")
    expect(s.loaded).toBe(true)
  })
})
