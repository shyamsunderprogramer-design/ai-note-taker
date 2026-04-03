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
  getStreamUrlWithMode: (query, mode = "adaptive", responseStyle = "concise", provider = "ollama", context = null) => {
    const encodedQuery = encodeURIComponent(query || "")
    const encodedMode = encodeURIComponent(mode)
    const encodedStyle = encodeURIComponent(responseStyle)
    const encodedProvider = encodeURIComponent(provider)
    let url = `${BASE_URL}/stream?q=${encodedQuery}&mode=${encodedMode}&style=${encodedStyle}&provider=${encodedProvider}`
    if (context && Array.isArray(context) && context.length > 0) {
      const encodedContext = encodeURIComponent(JSON.stringify(context))
      url += `&context=${encodedContext}`
    }
    return url
  },

  // Health check endpoint
  getHealthUrl: () => `${BASE_URL}/health`,

  // Transcribe endpoint
  getTranscribeUrl: () => `${BASE_URL}/transcribe`,

  // Race mode stream URL — fires all providers, fastest wins
  getRaceUrl: (query, mode = "fast", responseStyle = "concise", context = null, enabledProviders = null) => {
    const encodedQuery = encodeURIComponent(query || "")
    const encodedMode = encodeURIComponent(mode)
    const encodedStyle = encodeURIComponent(responseStyle)
    let url = `${BASE_URL}/stream-race?q=${encodedQuery}&mode=${encodedMode}&style=${encodedStyle}`
    if (context && Array.isArray(context) && context.length > 0) {
      const encodedContext = encodeURIComponent(JSON.stringify(context))
      url += `&context=${encodedContext}`
    }
    if (Array.isArray(enabledProviders)) {
      url += `&enabled=${encodedURIComponent(enabledProviders.join(","))}`
    }
    return url
  },

  // Cloud transcribe endpoint
  getCloudTranscribeUrl: () => `${BASE_URL}/transcribe-cloud`,

  // Ollama model management
  getOllamaModelsUrl: () => `${BASE_URL}/ollama/models`,
  pullOllamaModel: (model) => {
    return fetch(`${BASE_URL}/ollama/pull?model=${encodeURIComponent(model)}`, { method: "POST" })
  },
  deleteOllamaModel: (model) => {
    return fetch(`${BASE_URL}/ollama/models/${encodeURIComponent(model)}`, { method: "DELETE" })
  },

  // Screenshot capture + multimodal AI
  captureScreenshot: () => ipcRenderer.invoke("window:capture-screenshot"),
  getAskWithImageUrl: () => `${BASE_URL}/ask-with-image`,

  // Screenshot ring buffer (for auto-screenshot)
  overlayGetLatestScreenshot: () => ipcRenderer.invoke("overlay:get-latest-screenshot"),

  // Auto screenshot
  autoScreenshotSetEnabled: (enabled, intervalMs) => ipcRenderer.invoke("auto-screenshot:set-enabled", enabled, intervalMs),
  autoScreenshotGetStatus: () => ipcRenderer.invoke("auto-screenshot:get-status"),

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

  // Configure provider API key — sends via JSON body (not URL)
  configureProvider: async (provider, apiKey) => {
    const response = await fetch(`${BASE_URL}/configure`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ provider, api_key: apiKey })
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

  // Save file with dialog
  saveFile: (options) => ipcRenderer.invoke("dialog:save-file", options),

  // Copy text to clipboard (Electron-safe)
  copyToClipboard: (text) => ipcRenderer.invoke("clipboard:write", text),

  // Auto-updater
  checkForUpdate: () => ipcRenderer.invoke("updater:check"),
  downloadUpdate: () => ipcRenderer.invoke("updater:download"),
  installUpdate: () => ipcRenderer.invoke("updater:install"),
  onUpdateAvailable: (callback) => {
    ipcRenderer.on("updater:available", (_event, info) => callback(info))
  },
  onUpdateProgress: (callback) => {
    ipcRenderer.on("updater:progress", (_event, progress) => callback(progress))
  },
  onUpdateDownloaded: (callback) => {
    ipcRenderer.on("updater:downloaded", (_event, info) => callback(info))
  },

  // Listen for stealth state changes (triggered by shortcuts in main process)
  onStealthStateChanged: (callback) => {
    ipcRenderer.on("stealth:state-changed", (_event, state) => callback(state))
  },

  // Global Ctrl+Enter — trigger AI from any app
  onTriggerAI: (callback) => {
    ipcRenderer.on("trigger-ai", () => callback())
  }


})
