// ==============================
// ELECTRON PRELOAD BRIDGE
// ==============================
const { contextBridge, ipcRenderer } = require("electron")

// Native select menus and title tooltips use separate OS popup windows. They do
// not inherit BrowserWindow content protection. Keep these surfaces in the
// document on every desktop page, even when protection is toggled after load.
// Electron 41 supports base-select: native semantics/keyboard handling remain,
// but the picker is rendered in this document's protected top layer.
function installProtectedControls() {
  if (!['file:', 'data:'].includes(location.protocol)) return

  const titles = new WeakMap()
  let tooltip, owner, timer
  const tooltipId = 'ant-protected-tooltip'

  function hideTooltip() {
    clearTimeout(timer)
    if (tooltip?.matches(':popover-open')) tooltip.hidePopover()
    if (owner) {
      const ids = (owner.getAttribute('aria-describedby') || '').split(/\s+/).filter(id => id && id !== tooltipId)
      if (ids.length) owner.setAttribute('aria-describedby', ids.join(' '))
      else owner.removeAttribute('aria-describedby')
    }
    owner = null
  }

  function showTooltip(element, delay = 0) {
    if (!tooltip || !titles.get(element)?.text) return
    hideTooltip()
    owner = element
    timer = setTimeout(() => {
      if (!element.isConnected || owner !== element) return hideTooltip()
      tooltip.textContent = titles.get(element).text
      const ids = new Set((element.getAttribute('aria-describedby') || '').split(/\s+/).filter(Boolean))
      ids.add(tooltipId)
      element.setAttribute('aria-describedby', [...ids].join(' '))
      tooltip.showPopover()
      const rect = element.getBoundingClientRect()
      const box = tooltip.getBoundingClientRect()
      tooltip.style.left = `${Math.max(8, Math.min(rect.left, innerWidth - box.width - 8))}px`
      tooltip.style.top = `${Math.max(8, rect.bottom + box.height + 16 > innerHeight ? rect.top - box.height - 8 : rect.bottom + 8)}px`
    }, delay)
  }

  function moveTitle(element) {
    if (!element.hasAttribute('title')) return
    const text = element.getAttribute('title')
    const previous = titles.get(element)
    // Preserve accessible names for icon-only buttons which relied on title.
    const needsName = element.matches('button, a, input, select, [role="button"]') &&
      !element.hasAttribute('aria-labelledby') && !element.labels?.length && !element.textContent.trim()
    const managesName = previous?.managesName || (needsName && !element.hasAttribute('aria-label'))
    const managesDescription = previous?.managesDescription || !element.hasAttribute('aria-description')
    if (managesName) {
      if (text) element.setAttribute('aria-label', text)
      else element.removeAttribute('aria-label')
    }
    if (managesDescription) {
      if (text) element.setAttribute('aria-description', text)
      else element.removeAttribute('aria-description')
    }
    titles.set(element, { text, managesName, managesDescription })
    element.removeAttribute('title')
    if (owner === element) {
      if (text) showTooltip(element)
      else hideTooltip()
    }
  }

  function scan(node) {
    if (node.nodeType !== Node.ELEMENT_NODE && node !== document) return
    if (node.nodeType === Node.ELEMENT_NODE) moveTitle(node)
    node.querySelectorAll('[title]').forEach(moveTitle)
  }

  // Observe from preload, before page scripts add options or update help text.
  new MutationObserver(records => {
    for (const record of records) {
      if (record.type === 'attributes') moveTitle(record.target)
      else record.addedNodes.forEach(scan)
    }
    if (owner && !owner.isConnected) hideTooltip()
  }).observe(document, { subtree: true, childList: true, attributes: true, attributeFilter: ['title'] })

  document.addEventListener('DOMContentLoaded', () => {
    const style = document.createElement('style')
    style.textContent = `
      select:not([multiple]), select:not([multiple])::picker(select) {
        appearance: base-select !important;
      }
      select:not([multiple]) { background-image: none !important; }
      select:not([multiple])::picker-icon { margin-inline-start: 8px; }
      select:not([multiple])::picker(select) {
        background: #14182a; color: var(--text-main, #f1f5f9);
        border: 1px solid var(--line-bright, #475569); border-radius: 10px;
        padding: 6px; box-shadow: 0 8px 24px #0006; box-sizing: border-box;
        max-block-size: min(360px, calc(100dvh - 24px)); overflow: auto;
        min-inline-size: min(220px, calc(100dvw - 24px));
        max-inline-size: calc(100dvw - 24px); font: inherit;
      }
      select:not([multiple]) option {
        min-block-size: 30px; padding: 6px 10px; border-radius: 6px;
        white-space: normal; overflow-wrap: anywhere;
      }
      select:not([multiple]) option:checked { background: #1e40af; color: #fff; }
      select:not([multiple]) option:disabled { color: #94a3b8; }
      select:not([multiple]) option:not(:disabled):hover { background: #334155; }
      select:not([multiple]) option:focus-visible { outline: 2px solid var(--focus-ring, #93c5fd); outline-offset: -2px; }
      #ant-protected-tooltip {
        position: fixed; inset: auto; margin: 0; padding: 8px 10px;
        max-width: min(320px, calc(100vw - 32px)); box-sizing: border-box;
        background: #14182a; color: #f1f5f9; border: 1px solid #475569;
        border-radius: 6px; box-shadow: 0 4px 12px #0004;
        font: 12px/1.5 system-ui, sans-serif; overflow-wrap: anywhere;
      }
    `
    document.head.append(style)
    tooltip = document.createElement('div')
    tooltip.id = tooltipId
    tooltip.setAttribute('role', 'tooltip')
    tooltip.setAttribute('popover', 'manual')
    document.body.append(tooltip)
    scan(document)
  }, { once: true })

  function titleOwner(target) {
    for (let element = target; element?.nodeType === Node.ELEMENT_NODE; element = element.parentElement) {
      moveTitle(element)
      // An explicit empty title suppresses a parent's tooltip.
      if (titles.has(element)) return titles.get(element).text ? element : null
    }
    return null
  }
  document.addEventListener('pointerover', event => {
    if (tooltip?.contains(event.target)) return
    const element = titleOwner(event.target)
    if (element && element !== owner) showTooltip(element, 350)
  }, true)
  document.addEventListener('pointerout', event => {
    if (owner?.contains(event.relatedTarget) || tooltip?.contains(event.relatedTarget)) return
    hideTooltip()
  }, true)
  document.addEventListener('focusin', event => {
    const element = titleOwner(event.target)
    if (element) showTooltip(element)
  }, true)
  document.addEventListener('focusout', hideTooltip, true)
  document.addEventListener('keydown', event => { if (event.key === 'Escape') hideTooltip() }, true)
  document.addEventListener('pointerdown', hideTooltip, true)
  document.addEventListener('scroll', hideTooltip, true)
  window.addEventListener('resize', hideTooltip)
  window.addEventListener('blur', hideTooltip)
}

installProtectedControls()

// ==============================
// API CONFIG
// ==============================
const BASE_URL = (typeof window !== 'undefined' && window.API_BASE) ? window.API_BASE : 'http://127.0.0.1:8000'

function authSession(operation, value) {
  const result = ipcRenderer.sendSync(`auth:session:${operation}`, value)
  if (result?.error) throw new Error(result.error)
  return result?.value ?? null
}

async function refreshAuthSession() {
  const result = await ipcRenderer.invoke('auth:session:refresh')
  if (result?.error) throw new Error(result.error)
  return result?.value === true
}

// All ANT windows share the main process session; unchecked logins stay in memory.
async function _authHeaders() {
  const session = authSession('get')
  if (session?.refresh_token && session.expires_at <= Date.now() + 30000) await refreshAuthSession()
  const token = authSession('get')?.access_token
  return token ? { 'Authorization': `Bearer ${token}` } : {}
}

// ==============================
// EXPOSE SAFE API TO UI
// ==============================
contextBridge.exposeInMainWorld("api", {

  getAuthSession: () => authSession('get'),
  setAuthSession: value => authSession('set', value),
  refreshAuthSession,
  clearAuthSession: () => authSession('clear'),

  // Subscription credentials stay in the main process; only public status and text cross IPC.
  subscriptions: {
    status: () => ipcRenderer.invoke('subscriptions:status'),
    refresh: () => ipcRenderer.invoke('subscriptions:refresh'),
    connect: id => ipcRenderer.invoke('subscriptions:connect', id),
    connectOllama: () => ipcRenderer.invoke('subscriptions:connectOllama'),
    disconnectOllama: () => ipcRenderer.invoke('subscriptions:disconnectOllama'),
    cancelOllama: () => ipcRenderer.invoke('subscriptions:cancelOllama'),
    addOllamaModel: name => ipcRenderer.invoke('subscriptions:addOllamaModel', name),
    ollamaUsage: () => ipcRenderer.invoke('subscriptions:ollamaUsage'),
    ollamaDownload: () => ipcRenderer.invoke('subscriptions:ollamaDownload'),
    cancelLogin: () => ipcRenderer.invoke('subscriptions:cancelLogin'),
    disconnect: () => ipcRenderer.invoke('subscriptions:disconnect'),
    settings: value => ipcRenderer.invoke('subscriptions:settings', value),
    usage: () => ipcRenderer.invoke('subscriptions:usage'),
    start: (id, input) => ipcRenderer.invoke('subscriptions:start', id, input),
    cancel: id => ipcRenderer.invoke('subscriptions:cancel', id),
    onEvent: callback => {
      const listener = (_event, id, data) => callback(id, data)
      ipcRenderer.on('subscriptions:event', listener)
      return () => ipcRenderer.removeListener('subscriptions:event', listener)
    },
  },

  // Persistent store
  storeGet: (key) => ipcRenderer.invoke("store:get", key),
  storeSet: (key, value) => ipcRenderer.invoke("store:set", key, value),

  // Get streaming URL for SSE-style responses
  getStreamUrl: (query) => {
    const encoded = encodeURIComponent(query || "")
    return `${BASE_URL}/stream?q=${encoded}`
  },

  // Get streaming URL with mode parameter
  getStreamUrlWithMode: (query, mode = "adaptive", responseStyle = "concise", provider = "ollama", context = null, temperature = 0.3) => {
    const encodedQuery = encodeURIComponent(query || "")
    const encodedMode = encodeURIComponent(mode)
    const encodedStyle = encodeURIComponent(responseStyle)
    const encodedProvider = encodeURIComponent(provider)
    let url = `${BASE_URL}/stream?q=${encodedQuery}&mode=${encodedMode}&style=${encodedStyle}&provider=${encodedProvider}&temperature=${temperature}`
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
  getRaceUrl: (query, mode = "race", responseStyle = "concise", context = null, enabledProviders = null, temperature = 0.3) => {
    const encodedQuery = encodeURIComponent(query || "")
    const encodedMode = encodeURIComponent(mode)
    const encodedStyle = encodeURIComponent(responseStyle)
    let url = `${BASE_URL}/stream-race?q=${encodedQuery}&mode=${encodedMode}&style=${encodedStyle}&temperature=${temperature}`
    if (context && Array.isArray(context) && context.length > 0) {
      const encodedContext = encodeURIComponent(JSON.stringify(context))
      url += `&context=${encodedContext}`
    }
    if (Array.isArray(enabledProviders)) {
      url += `&enabled=${encodeURIComponent(enabledProviders.join(","))}`
    }
    return url
  },

  // Cloud transcribe endpoint
  getCloudTranscribeUrl: () => `${BASE_URL}/transcribe-cloud`,

  // Ollama model management
  getOllamaModelsUrl: () => `${BASE_URL}/ollama/models`,
  pullOllamaModel: async (model) => {
    return fetch(`${BASE_URL}/ollama/pull?model=${encodeURIComponent(model)}`, { method: "POST", headers: await _authHeaders() })
  },
  deleteOllamaModel: async (model) => {
    return fetch(`${BASE_URL}/ollama/models/${encodeURIComponent(model)}`, { method: "DELETE", headers: await _authHeaders() })
  },

  // Screenshot capture + multimodal AI
  captureScreenshot: () => ipcRenderer.invoke("window:capture-screenshot"),
  captureScreenshotContext: () => ipcRenderer.invoke("window:capture-screenshot-context"),
  getAskWithImageUrl: () => `${BASE_URL}/ask-with-image`,
  getOcrUrl: () => `${BASE_URL}/ocr`,

  // Screenshot ring buffer (for auto-screenshot)
  overlayGetLatestScreenshot: () => ipcRenderer.invoke("overlay:get-latest-screenshot"),

  // Auto screenshot
  autoScreenshotSetEnabled: (enabled, intervalMs) => ipcRenderer.invoke("auto-screenshot:set-enabled", enabled, intervalMs),
  autoScreenshotGetStatus: () => ipcRenderer.invoke("auto-screenshot:get-status"),

  // Set AI mode on backend
  setMode: async (mode) => {
    const response = await fetch(`${BASE_URL}/set-mode?mode=${encodeURIComponent(mode)}`, {
      method: "POST", headers: await _authHeaders()
    })
    if (!response.ok) throw new Error("Failed to update mode")
    return response.json()
  },

  // Get configured providers
  getProviders: async () => {
    const response = await fetch(`${BASE_URL}/providers`, { headers: await _authHeaders() })
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
  isWindowMaximized: () => ipcRenderer.invoke("window:is-maximized"),
  closeWindow: () => ipcRenderer.invoke("window:close"),
  setConversationCollapsed: (collapsed, height) => ipcRenderer.invoke("window:conversation-collapsed", collapsed, height),
  resizeWindow: (width, height) => ipcRenderer.invoke("window:resize", width, height),
  forceTop: () => ipcRenderer.invoke("window:force-top"),
  onMaximizeChanged: (callback) => {
    ipcRenderer.on("window:maximize-changed", (_event, state) => callback(state))
  },

  // Stealth mode
  setStealthMode: (enabled) => ipcRenderer.invoke("window:set-stealth-mode", enabled),

  // Screen capture protection
  setUndetectable: (enabled) => ipcRenderer.invoke("window:set-undetectable", enabled),
  getStealthState: () => ipcRenderer.invoke("window:get-stealth-state"),

  // Open logs folder
  openLogs: () => ipcRenderer.invoke("app:open-logs"),

  // Save file with dialog
  saveFile: (options) => ipcRenderer.invoke("dialog:save-file", options),

  // Import file with optional decryption
  importFile: (options) => ipcRenderer.invoke("dialog:import-file", options),

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

  // Interviewer channel: system-audio capture lives in the main process
  // because it spawns a native helper (see lib/system-audio.js).
  startSystemAudio: () => ipcRenderer.invoke("system-audio:start"),
  stopSystemAudio: () => ipcRenderer.invoke("system-audio:stop"),
  onSystemAudioData: (callback) => {
    ipcRenderer.removeAllListeners("system-audio:data")
    ipcRenderer.on("system-audio:data", (_event, chunk) => callback(chunk))
  },
  onSystemAudioSilent: (callback) => {
    ipcRenderer.removeAllListeners("system-audio:silent")
    ipcRenderer.on("system-audio:silent", () => callback())
  },
  onSystemAudioError: (callback) => {
    ipcRenderer.removeAllListeners("system-audio:error")
    ipcRenderer.on("system-audio:error", (_event, message) => callback(message))
  },

  // Global Ctrl+Enter — trigger AI from any app
  onTriggerAI: (callback) => {
    ipcRenderer.on("trigger-ai", () => callback())
  },

  // Global Ctrl+Shift+Enter — screen-only AI answer (Cluely stealth answer)
  onTriggerAIScreen: (callback) => {
    ipcRenderer.on("trigger-ai-screen", () => callback())
  },

  // Global Ctrl/Cmd+, — open settings
  onOpenSettings: (callback) => {
    ipcRenderer.on("open-settings", () => callback())
  },

  // Best-effort: bring the main window to focus (used after the open-settings signal)
  focusMainWindow: () => {
    ipcRenderer.send("main:focus")
  },

  // Backend process status and restart
  onBackendDead: (callback) => {
    ipcRenderer.on("backend:dead", (_event, data) => callback(data))
  },
  onBackendStatus: (callback) => {
    ipcRenderer.on("backend:status", (_event, data) => callback(data))
  },
  restartBackend: () => ipcRenderer.invoke("backend:restart"),
  getBackendStatus: () => ipcRenderer.invoke("backend:status"),

  // Document upload and RAG
  getDocumentsUrl: () => `${BASE_URL}/documents`,
  uploadDocument: async (formData) => {
    const response = await fetch(`${BASE_URL}/documents/upload`, {
      method: "POST",
      headers: await _authHeaders(),
      body: formData
    })
    return response.json()
  },
  listDocuments: async () => {
    const response = await fetch(`${BASE_URL}/documents`, { headers: await _authHeaders() })
    return response.json()
  },
  deleteDocument: async (docId) => {
    const response = await fetch(`${BASE_URL}/documents/${encodeURIComponent(docId)}`, {
      method: "DELETE", headers: await _authHeaders()
    })
    return response.json()
  },

  // Speaker diarization
  getTranscribeWithSpeakersUrl: () => `${BASE_URL}/transcribe-with-speakers`,

  // Export/Import
  exportConversation: async (data) => {
    const response = await fetch(`${BASE_URL}/conversations/export`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...await _authHeaders() },
      body: JSON.stringify(data)
    })
    return response.json()
  },
  importConversations: async (formData) => {
    const response = await fetch(`${BASE_URL}/conversations/import`, {
      method: "POST",
      headers: await _authHeaders(),
      body: formData
    })
    return response.json()
  },

  // Sales objection detection
  detectObjections: async (text) => {
    const response = await fetch(`${BASE_URL}/detect-objections`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...await _authHeaders() },
      body: JSON.stringify({ text })
    })
    return response.json()
  },

  // Analytics
  recordAnalytics: async (data) => {
    const response = await fetch(`${BASE_URL}/analytics/record`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...await _authHeaders() },
      body: JSON.stringify(data)
    })
    return response.json()
  },
  getAnalyticsSummary: async (days = 30) => {
    const response = await fetch(`${BASE_URL}/analytics/summary?days=${days}`, { headers: await _authHeaders() })
    return response.json()
  },
  exportAnalytics: async (format = "json") => {
    const response = await fetch(`${BASE_URL}/analytics/export`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...await _authHeaders() },
      body: JSON.stringify({ format })
    })
    return response.json()
  },

  // CRM Webhooks
  sendCRMWebhook: async (crmType, eventType, data) => {
    const response = await fetch(`${BASE_URL}/crm/webhook/${crmType}/${eventType}`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...await _authHeaders() },
      body: JSON.stringify(data)
    })
    return response.json()
  },
  getCRMConfig: async () => {
    const response = await fetch(`${BASE_URL}/crm/config`, { headers: await _authHeaders() })
    return response.json()
  },
  saveCRMConfig: async (config) => {
    const response = await fetch(`${BASE_URL}/crm/config`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...await _authHeaders() },
      body: JSON.stringify(config)
    })
    return response.json()
  },

  // Encrypted local keys, with an explicitly selected local .env copy.
  saveApiKey: (provider, apiKey, syncToEnv) => ipcRenderer.invoke("apiKey:save", { provider, apiKey, syncToEnv }),
  getApiKey: (provider) => ipcRenderer.invoke("apiKey:get", provider),
  hasApiKey: (provider) => ipcRenderer.invoke("apiKey:has", provider),

  // Screen recorder
  getRecordingSources: () => ipcRenderer.invoke("recorder:get-sources"),
  startRecording: (sourceId) => ipcRenderer.invoke("recorder:start", sourceId),
  stopRecording: () => ipcRenderer.invoke("recorder:stop"),
  takeScreenshot: () => ipcRenderer.invoke("recorder:screenshot"),

  // ═══════════════════════════════════════════════════════════════════════════════
  // OVERLAY & SYSTEM FEATURES
  // ═══════════════════════════════════════════════════════════════════════════════

  // Autostart (login item) configuration
  setAutoStart: (enabled, hidden = true) => ipcRenderer.invoke("autostart:set", { enabled, hidden }),
  getAutoStart: () => ipcRenderer.invoke("autostart:get"),

  // Portable mode
  getPortableMode: () => ipcRenderer.invoke("app:portable-mode"),

  // Overlay window controls
  showOverlay: () => ipcRenderer.invoke("overlay:show"),
  hideOverlay: () => ipcRenderer.invoke("overlay:hide"),
  toggleOverlay: () => ipcRenderer.invoke("overlay:toggle"),
  getOverlayState: () => ipcRenderer.invoke("overlay:state"),

  // Caption overlay
  showCaptionOverlay: () => ipcRenderer.invoke("caption:show"),
  hideCaptionOverlay: () => ipcRenderer.invoke("caption:hide"),
  toggleCaptionOverlay: () => ipcRenderer.invoke("caption:toggle"),

  // Interview overlay
  showInterviewOverlay: () => ipcRenderer.invoke("interview-overlay:show"),
  hideInterviewOverlay: () => ipcRenderer.invoke("interview-overlay:hide"),
  toggleInterviewOverlay: () => ipcRenderer.invoke("interview-overlay:toggle"),
  setInterviewOverlayContext: (ctx) => ipcRenderer.invoke("interview-overlay:set-context", ctx),

  // Opacity controls
  setOverlayOpacity: (value) => ipcRenderer.invoke("overlay:set-opacity", value),
  getOverlayOpacity: () => ipcRenderer.invoke("overlay:get-opacity"),

  // Click-through mode
  toggleClickThrough: () => ipcRenderer.invoke("overlay:toggle-click-through"),

  // File drag & drop
  processDroppedFile: (filePath) => ipcRenderer.invoke("overlay:process-file", filePath),
  openFileDialog: () => ipcRenderer.invoke("overlay:open-file-dialog"),

  // Listen for hotkey events
  onToggleMic: (callback) => {
    ipcRenderer.on("hotkey-toggle-mic", () => callback())
  },
  onStartVoice: (callback) => {
    ipcRenderer.on("hotkey-start-voice", () => callback())
  },
  onScreenshot: (callback) => {
    ipcRenderer.on("hotkey-screenshot", () => callback())
  },
  onFileDropped: (callback) => {
    ipcRenderer.on("file-dropped", (_event, fileInfo) => callback(fileInfo))
  },
  onOpacityChanged: (callback) => {
    ipcRenderer.on("overlay-opacity-changed", (_event, value) => callback(value))
  },

  // Generic send/receive for overlay
  send: (channel, ...args) => ipcRenderer.send(channel, ...args),
  invoke: (channel, ...args) => ipcRenderer.invoke(channel, ...args),
  receive: (channel, callback) => {
    ipcRenderer.on(channel, (_event, ...args) => callback(...args))
  }


})
