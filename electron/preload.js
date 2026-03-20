// ==============================
// 🔐 ELECTRON PRELOAD BRIDGE
// ==============================

// Import secure bridge from Electron
const { contextBridge, ipcRenderer } = require("electron")


// ==============================
// 🌐 API CONFIG
// ==============================

// 🔥 Base backend URL (FastAPI)
const BASE_URL = "http://127.0.0.1:8000"


// ==============================
// 🚀 EXPOSE SAFE API TO UI
// ==============================

contextBridge.exposeInMainWorld("api", {

  // ==============================
  // 📡 STREAM ENDPOINT
  // ==============================
  getStreamUrl: (query) => {
    /*
      🎯 Returns streaming endpoint with query param

      Example:
      http://127.0.0.1:8000/stream?q=hello
    */

    // 🔥 Encode query to prevent URL breaking
    const encoded = encodeURIComponent(query || "")

    return `${BASE_URL}/stream?q=${encoded}`
  },


  // ==============================
  // 🧠 MODE SWITCH (FUTURE READY)
  // ==============================
  getStreamUrlWithMode: (query, mode = "adaptive") => {
    /*
      🎯 Supports dynamic AI modes later

      Example:
      /stream?q=hello&mode=interview
    */

    const encodedQuery = encodeURIComponent(query || "")
    const encodedMode = encodeURIComponent(mode)

    return `${BASE_URL}/stream?q=${encodedQuery}&mode=${encodedMode}`
  },


  // ==============================
  // 🩺 HEALTH CHECK (OPTIONAL)
  // ==============================
  getHealthUrl: () => {
    /*
      🎯 Useful to check backend status
    */
    return `${BASE_URL}/health`
  },

  getTranscribeUrl: () => {
    return `${BASE_URL}/transcribe`
  },

  setMode: async (mode) => {
    const response = await fetch(`${BASE_URL}/set-mode?mode=${encodeURIComponent(mode)}`, {
      method: "POST"
    })

    if (!response.ok) {
      throw new Error("Failed to update mode")
    }

    return response.json()
  },

  minimizeWindow: () => ipcRenderer.invoke("window:minimize"),

  restoreWindow: () => ipcRenderer.invoke("window:restore"),

  toggleMaximizeWindow: () => ipcRenderer.invoke("window:toggle-maximize"),

  closeWindow: () => ipcRenderer.invoke("window:close"),

  setStealthMode: (enabled) => ipcRenderer.invoke("window:set-stealth-mode", enabled),

  setUndetectable: (enabled) => ipcRenderer.invoke("window:set-undetectable", enabled)

})
