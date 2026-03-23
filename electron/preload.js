// ==============================
// ELECTRON PRELOAD BRIDGE
// ==============================
const { contextBridge, ipcRenderer } = require("electron")

// ==============================
// API CONFIG
// ==============================
const BASE_URL = "http://127.0.0.1:8000"

// ==============================
// EXPOSE SAFE API TO UI
// ==============================
contextBridge.exposeInMainWorld("api", {

  // Persistent store
  storeGet: (key) => ipcRenderer.invoke("store:get", key),
  storeSet: (key, value) => ipcRenderer.invoke("store:set", key, value),

  // Get streaming URL for SSE-style responses
  getStreamUrl: (query) => {
    const encoded = encodeURIComponent(query || "")
    return `${BASE_URL}/stream?q=${encoded}`
  },

  // Get streaming URL with mode parameter
  getStreamUrlWithMode: (query, mode = "adaptive", responseStyle = "concise", provider = "ollama") => {
    const encodedQuery = encodeURIComponent(query || "")
    const encodedMode = encodeURIComponent(mode)
    const encodedStyle = encodeURIComponent(responseStyle)
    const encodedProvider = encodeURIComponent(provider)
    return `${BASE_URL}/stream?q=${encodedQuery}&mode=${encodedMode}&style=${encodedStyle}&provider=${encodedProvider}`
  },

  // Health check endpoint
  getHealthUrl: () => `${BASE_URL}/health`,

  // Transcribe endpoint
  getTranscribeUrl: () => `${BASE_URL}/transcribe`,

  // Cloud transcribe endpoint
  getCloudTranscribeUrl: () => `${BASE_URL}/transcribe-cloud`,

  // Set AI mode on backend
  setMode: async (mode) => {
    const response = await fetch(`${BASE_URL}/set-mode?mode=${encodeURIComponent(mode)}`, {
      method: "POST"
    })
    if (!response.ok) throw new Error("Failed to update mode")
    return response.json()
  },

  // Get configured providers
  getProviders: async () => {
    const response = await fetch(`${BASE_URL}/providers`)
    return response.json()
  },

  // Configure provider API key
  configureProvider: async (provider, apiKey) => {
    const response = await fetch(`${BASE_URL}/configure?provider=${encodeURIComponent(provider)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ api_key: apiKey })
    })
    return response.json()
  },

  // Conversation history
  conversationSave: (conversation) => ipcRenderer.invoke("conversation:save", conversation),
  conversationLoad: (id) => ipcRenderer.invoke("conversation:load", id),
  conversationList: () => ipcRenderer.invoke("conversation:list"),
  conversationDelete: (id) => ipcRenderer.invoke("conversation:delete", id),

  // Window controls
  minimizeWindow: () => ipcRenderer.invoke("window:minimize"),
  restoreWindow: () => ipcRenderer.invoke("window:restore"),
  toggleMaximizeWindow: () => ipcRenderer.invoke("window:toggle-maximize"),
  closeWindow: () => ipcRenderer.invoke("window:close"),
  resizeWindow: (width, height) => ipcRenderer.invoke("window:resize", width, height),

  // Stealth mode
  setStealthMode: (enabled) => ipcRenderer.invoke("window:set-stealth-mode", enabled),

  // Screen capture protection
  setUndetectable: (enabled) => ipcRenderer.invoke("window:set-undetectable", enabled),

  // Open logs folder
  openLogs: () => ipcRenderer.invoke("app:open-logs"),

  // Listen for stealth state changes (triggered by shortcuts in main process)
  onStealthStateChanged: (callback) => {
    ipcRenderer.on("stealth:state-changed", (_event, state) => callback(state))
  }


})
