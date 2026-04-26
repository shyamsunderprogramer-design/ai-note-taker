// ═══════════════════════════════════════════════════════════════════════════════
// PERFORMANCE OPTIMIZATIONS
// ═══════════════════════════════════════════════════════════════════════════════

// Debounce function for performance
function debounce(fn, wait) {
  let timeout
  return function(...args) {
    clearTimeout(timeout)
    timeout = setTimeout(() => fn.apply(this, args), wait)
  }
}

// Throttle function for scroll/resize
function throttle(fn, limit) {
  let inThrottle
  return function(...args) {
    if (!inThrottle) {
      fn.apply(this, args)
      inThrottle = true
      setTimeout(() => inThrottle = false, limit)
    }
  }
}

// Lazy load heavy components
const lazyModules = new Map()

async function lazyLoad(moduleName, importFn) {
  if (lazyModules.has(moduleName)) {
    return lazyModules.get(moduleName)
  }
  const module = await importFn()
  lazyModules.set(moduleName, module)
  return module
}

// Intersection Observer for lazy rendering
const lazyObserver = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      entry.target.classList.add('visible')
      lazyObserver.unobserve(entry.target)
    }
  })
}, { rootMargin: '100px' })

// RequestIdleCallback polyfill
const requestIdle = window.requestIdleCallback || ((cb) => setTimeout(cb, 1))

// ═══════════════════════════════════════════════════════════════════════════════
// STATE
// ═══════════════════════════════════════════════════════════════════════════════
var API_BASE = typeof API_BASE !== 'undefined' ? API_BASE : 'http://127.0.0.1:8000'
let isListening = false
let isStarting = false
let isBackendReady = false
let isUndetectable = false
let isProcessing = false  // true while AI is streaming a response
let mediaRecorder = null
let mediaStream = null
let audioChunks = []
let latestBotMessage = null
let currentConversationId = null
let currentMessages = []
let suppressAutoSave = false
let historySortBy = "updatedAt" // "updatedAt" | "createdAt" | "title" | "messageCount"

// Always-on mic state
let alwaysOnActive = false
let alwaysOnEventSource = null
let alwaysOnTranscriptionBuffer = ""
let alwaysOnLastHeardTime = 0
const ALWAYS_ON_SILENCE_THRESHOLD = 2500 // ms of silence before sending to AI

// Waveform visualization state
let waveformAudioCtx = null
let waveformAnalyser = null
let waveformCanvasCtx = null
let waveformAnimationId = null

// Real-time streaming transcription state
let transcribeWs = null      // WebSocket for live transcription
let streamProcessor = null   // ScriptProcessorNode for PCM capture
let partialTranscriptText = "" // Accumulated partial text

// Pre-warmed resources for instant start/stop
let prewarmedMicStream = null
let prewarmedAudioCtx = null

// Speaker diarization state
let speakerDiarizationEnabled = false
let currentSpeakers = []

// Document upload state
let uploadedDocuments = []

// Export/Import state
let exportCurrentConversation = null

// Session timer state
let sessionStartTime = null
let sessionTimerInterval = null
let sessionDurationMinutes = 0
let SESSION_WARNING_THRESHOLD = 45 // Show warning at 45 minutes
let SESSION_MAX_DURATION = 60 // Auto-stop at 60 minutes

// Sales objection handling state
let objectionDetectionEnabled = false
let currentObjections = []

// ═══════════════════════════════════════════════════════════════════════════════
// PLUELY-INSPIRED FEATURES (Autostart, Portable Mode)
// ═══════════════════════════════════════════════════════════════════════════════
let autostartEnabled = false
let autostartHidden = true
let isPortableMode = false

async function initOverlayFeatures() {
  try {
    // Initialize autostart settings
    await initAutostart()

    // Initialize portable mode detection
    await initPortableMode()

    console.log("[Overlay] Features initialized")
  } catch (e) {
    console.error("[Overlay] Failed to initialize features:", e)
  }
}

async function initAutostart() {
  try {
    const autostartToggle = document.getElementById("toggle-autostart")
    const autostartHiddenToggle = document.getElementById("toggle-autostart-hidden")
    const autostartHiddenRow = document.getElementById("autostartHiddenRow")

    // Get current autostart status
    if (window.api?.getAutoStart) {
      const status = await window.api.getAutoStart()
      autostartEnabled = status.enabled
      autostartHidden = status.openAsHidden

      // Update UI
      if (autostartToggle) {
        autostartToggle.checked = autostartEnabled
      }
      if (autostartHiddenToggle) {
        autostartHiddenToggle.checked = autostartHidden
      }
      if (autostartHiddenRow) {
        autostartHiddenRow.style.opacity = autostartEnabled ? "1" : "0.5"
        autostartHiddenRow.style.pointerEvents = autostartEnabled ? "auto" : "none"
      }
    }

    // Setup event listeners
    autostartToggle?.addEventListener("change", async (e) => {
      const enabled = e.target.checked
      autostartEnabled = enabled

      // Enable/disable hidden option
      if (autostartHiddenRow) {
        autostartHiddenRow.style.opacity = enabled ? "1" : "0.5"
        autostartHiddenRow.style.pointerEvents = enabled ? "auto" : "none"
      }

      // Save setting
      if (window.api?.setAutoStart) {
        const result = await window.api.setAutoStart(enabled, autostartHidden)
        if (result.success) {
          showNotification(`Autostart ${enabled ? "enabled" : "disabled"}`, "success")
        } else {
          showNotification("Failed to update autostart settings", "error")
          e.target.checked = !enabled // Revert
        }
      }
    })

    autostartHiddenToggle?.addEventListener("change", async (e) => {
      autostartHidden = e.target.checked

      // Save setting
      if (window.api?.setAutoStart && autostartEnabled) {
        await window.api.setAutoStart(autostartEnabled, autostartHidden)
      }
    })
  } catch (e) {
    console.error("[Overlay] Failed to init autostart:", e)
  }
}

async function initPortableMode() {
  try {
    const portableStatusEl = document.getElementById("portableModeStatus")

    if (window.api?.getPortableMode) {
      const info = await window.api.getPortableMode()
      isPortableMode = info.isPortable

      if (portableStatusEl) {
        if (isPortableMode) {
          portableStatusEl.textContent = "Active - Data stored with app"
          portableStatusEl.style.color = "var(--accent, #22c55e)"
        } else {
          portableStatusEl.textContent = "Not active - Data in user folder"
          portableStatusEl.style.color = "var(--text-dim)"
        }
      }
    } else {
      if (portableStatusEl) {
        portableStatusEl.textContent = "Not available"
      }
    }
  } catch (e) {
    console.error("[Overlay] Failed to init portable mode:", e)
  }
}

// ==============================
// DOM REFS
// ==============================
const stealthBtn = document.getElementById("stealthBtn")
const stealthLabel = document.getElementById("stealthLabel")
const listenBtn = document.getElementById("listenBtn")
const listenLabel = document.getElementById("listenLabel")
const waveformCanvasEl = document.getElementById("waveformCanvas")
const minBtn = document.getElementById("minBtn")
const maxBtn = document.getElementById("maxBtn")
const closeBtn = document.getElementById("closeBtn")
const modeSelect = document.getElementById("modeSelect") // hidden, kept for compatibility
const modelSelect = document.getElementById("modelSelect")
const fontSizeSelect = document.getElementById("fontSizeSelect")
const responseStyleSelect = document.getElementById("responseStyleSelect")
const temperatureSelect = document.getElementById("temperatureSelect")
const contextLengthSelect = document.getElementById("contextLengthSelect")
const tokenLimitSelect = document.getElementById("tokenLimitSelect")
const tokenCounter = document.getElementById("tokenCounter")
const autoSSBtn = document.getElementById("autoSSBtn")
const alwaysOnBtn = document.getElementById("alwaysOnBtn")
const smartModeBtn = document.getElementById("smartModeBtn")
const autoSSDot = document.getElementById("autoSSDot")
const alwaysOnDot = document.getElementById("alwaysOnDot")
const chatArea = document.getElementById("chatArea")
const chatWelcome = document.getElementById("chatWelcome")
const summarizeBtn = document.getElementById("summarizeBtn")
const menuBtn = document.getElementById("menuBtn")
const opacitySlider = document.getElementById("opacitySlider")
const textInput = document.getElementById("textInput")
const historyBtn = document.getElementById("historyBtn")
const historyPanel = document.getElementById("historyPanel")
const historyList = document.getElementById("historyList")
const newChatBtn = document.getElementById("newChatBtn")
const settingsPanel = document.getElementById("settingsPanel")
const closeSettingsBtn = document.getElementById("closeSettingsBtn")
const apiKeyModal = document.getElementById("apiKeyModal")
const apiKeyInput = document.getElementById("apiKeyInput")
const modalProviderName = document.getElementById("modalProviderName")
const modalSave = document.getElementById("modalSave")
const modalCancel = document.getElementById("modalCancel")
const backApiKeyModal = document.getElementById("backApiKeyModal")
const cloudModelSelect = document.getElementById("cloudModelSelect")

// ═══════════════════════════════════════════════════════════════════════════════
// OPACITY SLIDER — adjusts glass background transparency
// ═══════════════════════════════════════════════════════════════════════════════
function updateGlassOpacity(value, skipBackend = false) {
  const f = value / 100 // 0..1
  const root = document.documentElement.style
  root.setProperty("--glass-bg", `rgba(15,23,42,${(0.55 * f + 0.05).toFixed(2)})`)
  root.setProperty("--bg-primary", `rgba(10,14,26,${(0.55 * f + 0.05).toFixed(2)})`)
  root.setProperty("--bg-secondary", `rgba(20,24,40,${(0.5 * f + 0.05).toFixed(2)})`)
  root.setProperty("--bg-tertiary", `rgba(30,35,55,${(0.45 * f + 0.05).toFixed(2)})`)
  root.setProperty("--glass-border", `rgba(255,255,255,${(0.1 * f + 0.02).toFixed(2)})`)
  // Only sync to backend when user directly interacts with the slider
  if (!skipBackend && window.api && window.api.invoke) {
    window.api.invoke("overlay:set-opacity", Math.max(0.1, f))
  }
}

if (opacitySlider) {
  // Restore saved value
  const savedOpacity = localStorage.getItem("ainotetaker_glass_opacity")
  if (savedOpacity !== null) {
    opacitySlider.value = savedOpacity
    updateGlassOpacity(parseInt(savedOpacity))
  }

  opacitySlider.addEventListener("input", (e) => {
    const val = e.target.value
    updateGlassOpacity(parseInt(val))
    localStorage.setItem("ainotetaker_glass_opacity", val)
  })

  // Sync slider when hotkeys change opacity
  if (window.api && window.api.onOpacityChanged) {
    window.api.onOpacityChanged((overlayOpacity) => {
      // overlayOpacity is 0.5-1.0, map to slider 50-100
      const sliderVal = Math.round(overlayOpacity * 100)
      if (opacitySlider.value !== String(sliderVal)) {
        opacitySlider.value = sliderVal
        updateGlassOpacity(sliderVal, true)
        localStorage.setItem("ainotetaker_glass_opacity", sliderVal)
      }
    })
  }
}

// OCR / capture elements
const captureBtn = document.getElementById("captureBtn")
const ocrBadge = document.getElementById("ocrBadge")
const ocrBadgeText = document.getElementById("ocrBadgeText")
const ocrBadgeRemove = document.getElementById("ocrBadgeRemove")

// Ollama Pull elements
const ollamaPullInput = document.getElementById("ollamaPullInput")
const ollamaPullBtn = document.getElementById("ollamaPullBtn")
const ollamaPullStatus = document.getElementById("ollamaPullStatus")

// OCR state
let pendingOcrText = null
let pendingOcrScreenshot = null

// API Key modal handlers
if (modalCancel) modalCancel.addEventListener("click", () => apiKeyModal?.classList.remove("open"))
if (backApiKeyModal) backApiKeyModal.addEventListener("click", () => apiKeyModal?.classList.remove("open"))
if (apiKeyModal) apiKeyModal.addEventListener("click", (e) => { if (e.target === apiKeyModal) apiKeyModal.classList.remove("open") })

// ==============================
// GLOBAL ENTER KEY + F KEY LISTENERS
// ==============================
// Listen for stealth state changes triggered by Alt+D shortcut in main process
window.api.onStealthStateChanged((state) => {
  isUndetectable = state.undetectable
  stealthBtn.classList.toggle("undetectable", state.undetectable)
  stealthLabel.textContent = state.undetectable ? "Undetectable" : "Detectable"
})

// Global Ctrl+Enter — trigger AI from any app (Cluely-style: screen + audio context)
// Sends screenshot directly to vision AI — NO OCR delay
window.api.onTriggerAI(async () => {
  if (isProcessing) return

  // Grab latest transcript from always-on buffer
  const transcript = alwaysOnTranscriptionBuffer.trim()
  if (alwaysOnActive && transcript) {
    alwaysOnTranscriptionBuffer = ""
    alwaysOnLastHeardTime = 0
  }

  // Grab latest screenshot from ring buffer
  let screenshotB64 = null
  try {
    screenshotB64 = await window.api.overlayGetLatestScreenshot()
  } catch {}

  // If we have a screenshot, send it directly to vision AI (no OCR step)
  if (screenshotB64) {
    const query = transcript
      ? `The user said: "${transcript}"\n\nAlso, I can see their screen. Help based on both the conversation and what's on screen.`
      : "Analyze what's on the user's screen and provide helpful context or suggestions."
    streamMessage("user", transcript ? `[Voice] ${transcript.substring(0, 60)}...` : "[Screen] Screen query", { hasScreenshot: true, screenshotB64 })
    setProcessingUI(true)
    try {
      await streamAIResponseWithImage(query, screenshotB64)
    } catch (e) {
      addErrorMessage("Vision AI failed: " + e.message)
      setProcessingUI(false)
    }
    return
  }

  // No screenshot — just send voice transcript
  if (transcript) {
    autoSendToAI(transcript)
  } else if (!isListening) {
    listenBtn.click()
  }
})

// Global Ctrl+Shift+Enter — screen-only AI answer (Cluely stealth answer, no voice)
// Sends screenshot directly to vision AI — NO OCR delay
window.api.onTriggerAIScreen(async () => {
  if (isProcessing) return

  // Grab latest screenshot from ring buffer
  let screenshotB64 = null
  try {
    screenshotB64 = await window.api.overlayGetLatestScreenshot()
  } catch {}

  if (!screenshotB64) {
    addErrorMessage("No screenshot available. Make sure auto-screenshot is running.")
    return
  }

  // Send screenshot directly to vision model — skip OCR entirely
  const query = "Analyze what's on the user's screen. Provide helpful context, suggestions, or answers based on what you see."
  streamMessage("user", "[Screen] Screen-only query", { hasScreenshot: true, screenshotB64 })
  setProcessingUI(true)
  try {
    await streamAIResponseWithImage(query, screenshotB64)
  } catch (e) {
    addErrorMessage("Screen analysis failed: " + e.message)
    setProcessingUI(false)
  }
})

// Backend status monitoring
const backendStatusEl = document.getElementById("backendStatusIndicator")
const backendStatusDot = backendStatusEl?.querySelector(".backend-status-dot")
const backendStatusText = backendStatusEl?.querySelector(".backend-status-text")

function updateBackendStatus(status, data = {}) {
  if (!backendStatusEl) return

  // Remove all status classes
  backendStatusEl.classList.remove("starting", "ready", "error", "dead")
  backendStatusEl.classList.add("visible")

  switch (status) {
    case "starting":
      backendStatusEl.classList.add("starting")
      backendStatusText.textContent = "Starting..."
      break
    case "ready":
      backendStatusEl.classList.add("ready")
      backendStatusText.textContent = "Connected"
      // Hide after 3 seconds when connected
      setTimeout(() => {
        backendStatusEl.classList.remove("visible")
      }, 3000)
      break
    case "error":
      backendStatusEl.classList.add("error")
      if (data.restartAttempt) {
        backendStatusText.textContent = `Restarting (${data.restartAttempt}/${data.maxAttempts})...`
      } else {
        backendStatusText.textContent = "Error"
      }
      break
    case "dead":
      backendStatusEl.classList.add("dead")
      backendStatusText.textContent = "Offline - Click to restart"
      backendStatusEl.style.cursor = "pointer"
      backendStatusEl.onclick = async () => {
        backendStatusText.textContent = "Restarting..."
        await window.api.restartBackend()
      }
      break
  }
}

// Listen for backend status changes
window.api.onBackendStatus((data) => {
  updateBackendStatus(data.status, data)
})

// Check initial backend status
window.api.getBackendStatus().then((status) => {
  updateBackendStatus(status.status, status)
})

document.addEventListener("keydown", (e) => {
  // Tab — auto-answer detected question (Cluely-style dynamic action)
  if (e.key === "Tab") {
    const tag = document.activeElement.tagName.toLowerCase()
    if (tag === "input" || tag === "textarea" || tag === "select") return
    if (activeDynamicAction) {
      e.preventDefault()
      triggerDynamicAction()
      return
    }
  }

  // Escape — close panels
  if (e.key === "Escape") {
    const tag = document.activeElement.tagName.toLowerCase()
    if (tag === "input" || tag === "textarea" || tag === "select") return
    closeHistoryPanel()
    settingsPanel.classList.remove("open")
    return
  }

  // F key — toggle maximize
  if (e.key === "f" || e.key === "F") {
    const tag = document.activeElement.tagName.toLowerCase()
    if (tag === "input" || tag === "textarea" || tag === "select") return
    e.preventDefault()
    maxBtn.click()
    return
  }

  if (e.key === "Enter") {
    const tag = document.activeElement.tagName.toLowerCase()
    if (tag === "input" || tag === "textarea") {
      // Enter in text input = submit text
      e.preventDefault()
      const text = textInput.value.trim()
      if (text) {
        submitText(text)
        textInput.value = ""
      }
      return
    }
    if (tag === "select") return
    // Enter elsewhere = toggle listening / flush always-on buffer
    e.preventDefault()
    if (alwaysOnActive && alwaysOnTranscriptionBuffer.trim()) {
      flushAlwaysOnBuffer()
      return
    }
    if (isListening) {
      stopListening()
    } else {
      listenBtn.click()
    }
  }
})

// ==============================
// HELPERS
// ==============================
function getSelectedMode() {
  return modeSelect ? modeSelect.value : "auto"
}

function getSelectedModel() {
  return modelSelect ? modelSelect.value || "auto" : "auto"
}

function updateProviderRecommendation(mode) {
  const banner = document.getElementById("providerRecommendation")
  const modeName = document.getElementById("recModeName")
  const container = document.getElementById("recProviders")
  if (!banner || !modeName || !container) return

  const recommendations = {
    adaptive:   { label: "Adaptive", providers: ["OpenAI", "Anthropic", "Google"] },
    auto:       { label: "Auto", providers: ["OpenAI", "Anthropic", "Google"] },
    fast:       { label: "Fast", providers: ["Groq", "Google Gemini", "DeepSeek"] },
    cloud:      { label: "Cloud", providers: ["OpenAI", "Anthropic", "Google", "Groq"] },
    universal:  { label: "Universal", providers: ["OpenAI", "Anthropic", "Google"] },
    interview:  { label: "Interview", providers: ["Anthropic", "OpenAI", "Ollama Local"] },
    reasoning:  { label: "Reasoning", providers: ["Anthropic", "OpenAI o-series", "DeepSeek"] },
    code:       { label: "Code", providers: ["Anthropic", "OpenAI", "DeepSeek Coder"] },
    turbo:      { label: "Turbo", providers: ["Groq", "Google Gemini Flash", "GPT-4o Mini"] },
    instant:    { label: "Instant", providers: ["Groq", "Google Gemini Flash", "Llama 3.2 1B"] }
  }

  const rec = recommendations[mode] || recommendations.adaptive
  modeName.textContent = rec.label
  container.innerHTML = rec.providers.map(p =>
    `<span class="provider-chip"><span class="provider-chip-dot"></span>${p}</span>`
  ).join("")

  // Animate in
  banner.style.opacity = "0"
  banner.style.transform = "translateY(-4px)"
  requestAnimationFrame(() => {
    banner.style.transition = "opacity 0.25s ease, transform 0.25s ease"
    banner.style.opacity = "1"
    banner.style.transform = "translateY(0)"
  })
}

function getSelectedResponseStyle() {
  return responseStyleSelect?.value || "concise"
}

function getSelectedTemperature() {
  return parseFloat(temperatureSelect?.value || "0.3")
}

function renderModelBadge(msg, displayName) {
  if (!msg || !msg.element || !displayName) return
  const label = msg.element.querySelector(".msg-label")
  if (!label) return
  let badge = label.querySelector(".model-badge")
  if (!badge) {
    badge = document.createElement("span")
    badge.className = "model-badge streaming-badge"
    label.appendChild(badge)
  }
  badge.textContent = `[${displayName}]`
}

function setListeningUI(listening) {
  isListening = listening
  if (listening) {
    listenBtn.classList.add("listening")
    listenLabel.textContent = "Stop"
  } else {
    listenBtn.classList.remove("listening")
    listenLabel.textContent = "Start"
  }
}

function getSelectedContextLength() {
  return parseInt(contextLengthSelect?.value || "3", 10)
}

function getSelectedTokenLimit() {
  return parseInt(tokenLimitSelect?.value || "128000", 10)
}

function estimateTokens(text) {
  if (!text) return 0
  // Rough estimation: ~1 token per 0.75 words
  const wordCount = text.trim().split(/\s+/).length
  return Math.ceil(wordCount / 0.75)
}

function getContextMessages() {
  const contextLength = getSelectedContextLength()
  if (contextLength === 0) return null

  const tokenLimit = getSelectedTokenLimit()
  const recentMessages = currentMessages.slice(-contextLength * 2)

  // Build context within token limit
  const contextMsgs = []
  let totalTokens = 0

  // Iterate in reverse (oldest first) and add until token limit
  for (let i = 0; i < recentMessages.length; i++) {
    const msg = recentMessages[i]
    const msgTokens = estimateTokens(msg.text)
    if (totalTokens + msgTokens > tokenLimit) break
    totalTokens += msgTokens
    contextMsgs.push(msg)
  }

  // Update token counter
  if (tokenCounter) {
    const limitDisplay = tokenLimit >= 1000 ? Math.round(tokenLimit / 1000) + "K" : tokenLimit
    tokenCounter.textContent = `~${Math.round(totalTokens)} / ${limitDisplay}`
    tokenCounter.style.display = contextLength > 0 ? "inline" : "none"
  }

  return contextMsgs.length > 0 ? contextMsgs : null
}

function setProcessingUI(processing) {
  isProcessing = processing
  if (processing) {
    listenBtn.classList.add("listening", "processing")
    listenBtn.disabled = true
    listenLabel.textContent = "Processing..."
  } else {
    listenBtn.classList.remove("listening", "processing")
    listenBtn.disabled = false
    listenLabel.textContent = "Start"
  }
}

// ==============================
// CONVERSATION HISTORY HELPERS
// ==============================
function generateTitle(firstMessageText) {
  const text = firstMessageText.trim()
  if (text.length <= 60) return text
  return text.substring(0, 57) + "..."
}

function formatLists(text) {
  if (!text) return text
  const lines = text.split("\n")
  const result = []
  let inList = false
  let listType = null // 'ol', 'ul', null

  for (const line of lines) {
    const trimmed = line.trim()
    const numberedMatch = trimmed.match(/^(\d+)\.\s+(.*)/)
    const bulletMatch = trimmed.match(/^[-*]\s+(.*)/)
    const letteredMatch = trimmed.match(/^([a-z])\.\s+(.*)/)

    if (numberedMatch || letteredMatch) {
      if (!inList || listType !== "ol") {
        if (inList) result.push(listType === "ol" ? "</ol>" : "</ul>")
        result.push("<ol class='chat-list'>")
        inList = true
        listType = "ol"
      }
      const content = numberedMatch ? numberedMatch[2] : letteredMatch[2]
      result.push(`<li>${content}</li>`)
    } else if (bulletMatch) {
      if (!inList || listType !== "ul") {
        if (inList) result.push(listType === "ol" ? "</ol>" : "</ul>")
        result.push("<ul class='chat-list'>")
        inList = true
        listType = "ul"
      }
      result.push(`<li>${bulletMatch[1]}</li>`)
    } else {
      if (inList) {
        result.push(listType === "ol" ? "</ol>" : "</ul>")
        inList = false
        listType = null
      }
      result.push(line)
    }
  }

  if (inList) {
    result.push(listType === "ol" ? "</ol>" : "</ul>")
  }

  return result.join("\n")
}

function formatDate(timestamp) {
  if (!timestamp) return ""
  const d = new Date(timestamp)
  const now = new Date()
  const diffMs = now - d
  const diffMin = Math.floor(diffMs / 60000)
  const diffHr = Math.floor(diffMs / 3600000)
  const diffDay = Math.floor(diffMs / 86400000)

  if (diffMin < 1) return "Just now"
  if (diffMin < 60) return `${diffMin}m ago`
  if (diffHr < 24) return `${diffHr}h ago`
  if (diffDay === 1) return `Yesterday ${d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`
  if (diffDay < 7) return d.toLocaleDateString([], { weekday: "short", hour: "2-digit", minute: "2-digit" })
  if (d.toDateString() === now.toDateString()) {
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
  }
  return d.toLocaleDateString() + " " + d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
}

async function saveCurrentConversation() {
  if (currentMessages.length === 0) return
  const firstUserMsg = currentMessages.find(m => m.role === "user")
  const title = firstUserMsg ? generateTitle(firstUserMsg.text) : "Untitled"

  // Load existing conversation to preserve pinned state
  let pinned = false
  if (currentConversationId) {
    try {
      const existing = await window.api.conversationLoad(currentConversationId)
      if (existing) pinned = !!existing.pinned
    } catch {}
  }

  const conversation = {
    id: currentConversationId,
    title,
    pinned,
    messages: currentMessages,
    mode: getSelectedMode(),
    isAutoScreenshot: autoSSBtn?.classList.contains("active"),
    isAlwaysOnMic: alwaysOnActive,
    savedAt: Date.now()
  }

  try {
    const saved = await window.api.conversationSave(conversation)
    currentConversationId = saved.id

    // Auto-ingest into cognitive graph
    ingestConversationToGraph(saved)
  } catch (err) {
    console.error("[Conversation] Save error:", err)
  }
}

// Auto-ingest conversation into cognitive graph
async function ingestConversationToGraph(conversation) {
  try {

    // Check if cognitive graph is available
    const statusRes = await fetch(`${API_BASE}/cognitive-graph/status`)
    const status = await statusRes.json()

    if (!status.connected) {
      console.log('[CognitiveGraph] Neo4j not connected, skipping ingestion')
      return
    }

    // Prepare data for ingestion
    const ingestData = {
      title: conversation.title || 'Untitled Interview',
      user_id: 'default',
      updatedAt: conversation.savedAt || Date.now(),
      duration_ms: 0, // Could calculate from timestamps
      messages: conversation.messages || []
    }

    // Ingest the conversation
    const response = await fetch(`${API_BASE}/cognitive-graph/ingest/${conversation.id}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(ingestData)
    })

    const result = await response.json()
    console.log('[CognitiveGraph] Auto-ingested conversation:', result)

    // Also extract entities from the conversation content
    const fullText = conversation.messages?.map(m => m.content || m.text || '').join(' ') || ''
    if (fullText.length > 50) {
      const extractRes = await fetch(`${API_BASE}/extract-entities`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: fullText })
      })
      const extractData = await extractRes.json()
      console.log('[CognitiveGraph] Extracted entities:', extractData?.entities || 'none')
    }
  } catch (err) {
    console.error('[CognitiveGraph] Auto-ingestion failed:', err)
    // Don't throw - this is background enrichment, shouldn't block saving
  }
}

function loadConversationIntoUI(conversation) {
  chatArea.innerHTML = ""
  currentMessages = []
  currentConversationId = conversation.id
  suppressAutoSave = true

  // Restore session metadata
  if (conversation.mode) {
    const modeTag = document.querySelector(".mode-tag")
    if (modeTag) modeTag.textContent = conversation.mode
  }

  // Restore auto-screenshot state
  if (conversation.isAutoScreenshot) {
    autoSSBtn?.classList.add("active")
    if (autoSSDot) autoSSDot.style.display = "block"
    window.api.autoScreenshotSetEnabled(true, 5000)
  } else {
    autoSSBtn?.classList.remove("active")
    if (autoSSDot) autoSSDot.style.display = "none"
  }

  // Restore always-on mic state
  if (conversation.isAlwaysOnMic) {
    alwaysOnActive = true
    alwaysOnBtn?.classList.add("active")
    if (alwaysOnDot) alwaysOnDot.style.display = "block"
  } else {
    alwaysOnActive = false
    alwaysOnBtn?.classList.remove("active")
    if (alwaysOnDot) alwaysOnDot.style.display = "none"
  }

  conversation.messages.forEach(msg => {
    if (msg.role === "user") {
      addMessage("user", msg.text)
    } else {
      addMessage("assistant", msg.text)
    }
    // Keep currentMessages in sync for context on next query
    currentMessages.push({ role: msg.role, text: msg.text, timestamp: msg.timestamp || Date.now() })
  })

  suppressAutoSave = false
  hideSummarizeButton()
  renderHistoryList()
}

function clearConversation() {
  // Clear current chat
  currentMessages = []
  if (chatArea) {
    chatArea.innerHTML = ""
    if (chatWelcome) {
      chatArea.appendChild(chatWelcome)
    }
  }
  hideSummarizeButton()
}

function startNewConversation() {
  currentConversationId = null
  currentMessages = []
  if (chatArea) chatArea.innerHTML = ""
  if (chatWelcome && chatArea) {
    chatArea.appendChild(chatWelcome)
  }
  // Remove active state from history list
  document.querySelectorAll(".history-item.active").forEach(el => el.classList.remove("active"))
  hideSummarizeButton()
  closeHistoryPanel()
}

function resumeConversation(conversation) {
  // Add messages to current chat without clearing
  removeWelcome()
  // Fix: set currentConversationId so new messages update the resumed conversation
  currentConversationId = conversation.id
  conversation.messages.forEach(msg => {
    const item = document.createElement("div")
    item.className = "chat-message " + msg.role
    const label = msg.role === "user" ? "You" : "AI"
    const bubble = document.createElement("div")
    bubble.className = "msg-bubble"
    setBubbleText(bubble, msg.text)
    item.innerHTML = `<span class="msg-label">${label}</span>`
    item.appendChild(bubble)
    chatArea.appendChild(item)
    currentMessages.push(msg)
  })
  // Update active state in history list
  renderHistoryList()
  scrollChat()
}

function copyConversation(conversation) {
  const text = conversation.messages.map(msg => {
    const label = msg.role === "user" ? "You:" : "AI:"
    return `${label} ${msg.text}`
  }).join("\n\n")

  // Use clipboard API with fallback for Electron
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text).then(() => {
      showToast("Conversation copied!")
    }).catch(err => {
      console.error("Clipboard API error:", err)
      fallbackCopyText(text)
    })
  } else {
    fallbackCopyText(text)
  }
}

function fallbackCopyText(text) {
  // Fallback using textarea selection for Electron compatibility
  const textarea = document.createElement("textarea")
  textarea.value = text
  textarea.style.position = "fixed"
  textarea.style.left = "-9999px"
  textarea.style.top = "0"
  textarea.setAttribute("readonly", "")
  document.body.appendChild(textarea)
  textarea.select()
  try {
    const success = document.execCommand("copy")
    showToast(success ? "Conversation copied!" : "Copy failed")
  } catch (err) {
    console.error("Fallback copy error:", err)
    showToast("Copy failed")
  } finally {
    document.body.removeChild(textarea)
  }
}

function showFullScreenshot(b64) {
  const existing = document.querySelector(".screenshot-modal")
  if (existing) existing.remove()
  const modal = document.createElement("div")
  modal.className = "screenshot-modal"
  modal.innerHTML = `<button class="screenshot-modal-close">&#x2715;</button><img src="data:image/png;base64,${b64}" alt="Full screenshot" />`
  modal.querySelector(".screenshot-modal-close").addEventListener("click", () => modal.remove())
  modal.addEventListener("click", (e) => { if (e.target === modal) modal.remove() })
  document.body.appendChild(modal)
}

function showToast(message, type = "success") {
  const existing = document.querySelector(".toast-message")
  if (existing) existing.remove()
  const toast = document.createElement("div")
  toast.className = "toast-message"
  toast.textContent = message
  const bg = type === "info" ? "rgba(0,0,0,0.8)" : "#22c55e"
  toast.style.cssText = "position:fixed;bottom:80px;left:50%;transform:translateX(-50%);background:" + bg + ";color:#fff;padding:8px 16px;border-radius:8px;font-size:13px;z-index:9999;animation:fadeOut 2s forwards"
  document.body.appendChild(toast)
  setTimeout(() => toast.remove(), 2000)
}

function exportConversation(conversation) {
  const overlay = document.createElement("div")
  overlay.style.cssText = "position:fixed;inset:0;background:rgba(0,0,0,0.6);display:flex;align-items:center;justify-content:center;z-index:999999"
  overlay.innerHTML = `
    <div style="background:#1a1d2e;border:1px solid rgba(255,255,255,0.12);border-radius:16px;padding:24px;width:360px;display:flex;flex-direction:column;gap:14px;box-shadow:0 16px 64px rgba(0,0,0,0.6)">
      <div style="display:flex;align-items:center;justify-content:space-between">
        <div style="font-size:1.1em;font-weight:700;color:#fff">Export Conversation</div>
        <button id="exportClose" style="background:none;border:none;color:rgba(255,255,255,0.4);font-size:1.2em;cursor:pointer;padding:4px;line-height:1">&times;</button>
      </div>

      <div style="font-size:0.85em;color:rgba(255,255,255,0.5);background:rgba(255,255,255,0.04);padding:10px 12px;border-radius:10px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${escapeHtml(conversation.title)}</div>

      <div style="display:flex;flex-direction:column;gap:6px">
        <div style="font-size:0.8em;font-weight:600;color:rgba(255,255,255,0.5);text-transform:uppercase;letter-spacing:0.08em">Format</div>
        <div style="display:flex;gap:8px">
          <label style="flex:1;display:flex;align-items:center;gap:8px;padding:10px 12px;border:1px solid rgba(255,255,255,0.1);border-radius:10px;cursor:pointer;transition:all 0.15s;background:rgba(59,130,246,0.1);border-color:rgba(59,130,246,0.4)">
            <input type="radio" name="exportFormat" value="txt" checked style="accent-color:#3b82f6">
            <span style="font-size:0.9em;color:#fff">TXT</span>
          </label>
          <label style="flex:1;display:flex;align-items:center;gap:8px;padding:10px 12px;border:1px solid rgba(255,255,255,0.1);border-radius:10px;cursor:pointer;transition:all 0.15s">
            <input type="radio" name="exportFormat" value="csv" style="accent-color:#3b82f6">
            <span style="font-size:0.9em;color:#fff">CSV</span>
          </label>
          <label style="flex:1;display:flex;align-items:center;gap:8px;padding:10px 12px;border:1px solid rgba(255,255,255,0.1);border-radius:10px;cursor:pointer;transition:all 0.15s">
            <input type="radio" name="exportFormat" value="json" style="accent-color:#3b82f6">
            <span style="font-size:0.9em;color:#fff">JSON</span>
          </label>
        </div>
      </div>

      <div style="display:flex;flex-direction:column;gap:6px">
        <div style="display:flex;align-items:center;justify-content:space-between">
          <div style="font-size:0.8em;font-weight:600;color:rgba(255,255,255,0.5);text-transform:uppercase;letter-spacing:0.08em">Encryption</div>
          <label style="position:relative;display:inline-flex;align-items:center;cursor:pointer">
            <input type="checkbox" id="exportEncrypt" style="width:0;height:0;opacity:0;position:absolute">
            <div id="encryptToggle" style="width:36px;height:20px;background:rgba(255,255,255,0.1);border-radius:10px;position:relative;transition:background 0.2s">
              <div style="width:16px;height:16px;background:#fff;border-radius:50%;position:absolute;top:2px;left:2px;transition:transform 0.2s"></div>
            </div>
          </label>
        </div>
        <input type="password" id="exportKey" placeholder="Enter encryption password" disabled style="width:100%;padding:10px 12px;border:1px solid rgba(255,255,255,0.1);border-radius:10px;background:rgba(255,255,255,0.04);color:#fff;font-size:0.9em;outline:none;box-sizing:border-box;opacity:0.4;transition:opacity 0.2s">
      </div>

      <button id="exportBtn" style="width:100%;padding:12px;border:none;border-radius:12px;background:linear-gradient(135deg,rgba(59,130,246,0.8),rgba(37,99,235,0.8));color:#fff;font-size:1em;font-weight:600;cursor:pointer;box-shadow:0 4px 16px rgba(59,130,246,0.3);transition:all 0.2s">Export File</button>
    </div>
  `
  document.body.appendChild(overlay)

  const close = () => overlay.remove()
  const closeBtn = overlay.querySelector("#exportClose")
  const encryptToggle = overlay.querySelector("#encryptToggle")
  const encryptCheckbox = overlay.querySelector("#exportEncrypt")
  const encryptInput = overlay.querySelector("#exportKey")
  const formatRadios = overlay.querySelectorAll('input[name="exportFormat"]')
  const exportBtn = overlay.querySelector("#exportBtn")

  closeBtn.addEventListener("click", close)
  overlay.addEventListener("click", (e) => { if (e.target === overlay) close() })

  // Toggle encryption
  encryptCheckbox.addEventListener("change", () => {
    const on = encryptCheckbox.checked
    encryptToggle.style.background = on ? "rgba(59,130,246,0.6)" : "rgba(255,255,255,0.1)"
    encryptToggle.querySelector("div").style.transform = on ? "translateX(16px)" : ""
    encryptInput.disabled = !on
    encryptInput.style.opacity = on ? "1" : "0.4"
    if (on) encryptInput.focus()
  })

  // Format radio highlight
  formatRadios.forEach(radio => {
    radio.addEventListener("change", () => {
      formatRadios.forEach(r => {
        const label = r.closest("label")
        label.style.background = r.checked ? "rgba(59,130,246,0.1)" : ""
        label.style.borderColor = r.checked ? "rgba(59,130,246,0.4)" : ""
      })
    })
  })

  // Build content based on format
  function buildContent(format) {
    const title = conversation.title
    const date = new Date(conversation.updatedAt || conversation.createdAt).toLocaleString()
    const msgs = conversation.messages

    if (format === "txt") {
      const lines = [`${title}`, `${"=".repeat(title.length)}`, ``, `Exported: ${date}`, ``]
      msgs.forEach(msg => {
        const label = msg.role === "user" ? "You" : "AI"
        const mode = msg.mode ? ` [${msg.mode}]` : ""
        lines.push(`${label}${mode}:`)
        lines.push(`${msg.text}`)
        lines.push("")
      })
      return lines.join("\n")
    }

    if (format === "csv") {
      const escape = (s) => `"${String(s).replace(/"/g, '""')}"`
      const rows = [["Timestamp", "Role", "Mode", "Message"]]
      msgs.forEach(msg => {
        rows.push([
          new Date(msg.timestamp).toLocaleString(),
          msg.role,
          msg.mode || "",
          msg.text
        ])
      })
      return rows.map(row => row.map(escape).join(",")).join("\n")
    }

    if (format === "json") {
      return JSON.stringify({ title, date, messages: msgs }, null, 2)
    }
  }

  exportBtn.addEventListener("click", async () => {
    const format = document.querySelector('input[name="exportFormat"]:checked').value
    const encrypt = encryptCheckbox.checked
    const key = encryptInput.value

    if (encrypt && !key) {
      encryptInput.style.borderColor = "rgba(239,68,68,0.6)"
      encryptInput.focus()
      return
    }

    const content = buildContent(format)
    const ext = format === "json" ? "json" : format
    const filename = `${conversation.title.replace(/[^a-z0-9]/gi, "_")}.${ext}`
    const filters = format === "txt"
      ? [{ name: "Text Files", extensions: ["txt"] }]
      : format === "csv"
      ? [{ name: "CSV Files", extensions: ["csv"] }]
      : [{ name: "JSON Files", extensions: ["json"] }]

    exportBtn.textContent = "Exporting..."
    exportBtn.disabled = true

    const result = await window.api.saveFile({ defaultPath: filename, filters, content, encryptionKey: key || null })

    if (result.success) {
      close()
      showToast(`Exported to ${filename}`)
    } else if (result.error) {
      exportBtn.textContent = "Export Failed"
      exportBtn.disabled = false
      setTimeout(() => { exportBtn.textContent = "Export File" }, 2000)
    } else {
      close()
    }
  })
}

function renameConversation(conversation) {
  // Create custom rename dialog (native prompt doesn't work well with frameless windows)
  const overlay = document.createElement("div")
  overlay.style.cssText = "position:fixed;inset:0;background:rgba(0,0,0,0.5);display:flex;align-items:center;justify-content:center;z-index:999999"
  overlay.innerHTML = `
    <div style="background:#1a1d2e;border:1px solid rgba(255,255,255,0.1);border-radius:16px;padding:24px;width:320px;display:flex;flex-direction:column;gap:12px;box-shadow:0 8px 32px rgba(0,0,0,0.5)">
      <div style="font-size:1.1em;font-weight:700;color:#fff">Rename conversation</div>
      <input type="text" id="renameInput" value="${escapeHtml(conversation.title)}" style="width:100%;padding:10px 12px;border:1px solid rgba(255,255,255,0.15);border-radius:10px;background:rgba(255,255,255,0.05);color:#fff;font-size:0.95em;outline:none;box-sizing:border-box" />
      <div style="display:flex;gap:8px;justify-content:flex-end">
        <button id="renameCancel" style="padding:8px 16px;border:1px solid rgba(255,255,255,0.1);border-radius:10px;background:transparent;color:rgba(255,255,255,0.7);cursor:pointer;font-size:0.9em">Cancel</button>
        <button id="renameOk" style="padding:8px 16px;border:none;border-radius:10px;background:linear-gradient(135deg,rgba(59,130,246,0.7),rgba(37,99,235,0.7));color:#fff;cursor:pointer;font-size:0.9em;font-weight:600">Rename</button>
      </div>
    </div>
  `
  document.body.appendChild(overlay)

  const input = overlay.querySelector("#renameInput")
  const okBtn = overlay.querySelector("#renameOk")
  const cancelBtn = overlay.querySelector("#renameCancel")

  input.focus()
  input.select()

  const closeDialog = () => overlay.remove()

  okBtn.addEventListener("click", () => {
    const newTitle = input.value.trim()
    closeDialog()
    if (!newTitle || newTitle === conversation.title) return
    const updated = { ...conversation, title: newTitle, updatedAt: Date.now() }
    window.api.conversationSave(updated).then(() => {
      renderHistoryList()
      showToast("Renamed!")
    })
  })

  cancelBtn.addEventListener("click", closeDialog)
  overlay.addEventListener("click", (e) => { if (e.target === overlay) closeDialog() })
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") okBtn.click()
    if (e.key === "Escape") closeDialog()
  })
}

async function pinConversation(id) {
  const conv = await window.api.conversationLoad(id)
  if (!conv) return
  const updated = { ...conv, pinned: !conv.pinned, updatedAt: Date.now() }
  await window.api.conversationSave(updated)
  renderHistoryList()
}

function deleteConversation(id) {
  const confirmed = confirm("Delete this conversation? This cannot be undone.")
  if (!confirmed) return
  window.api.conversationDelete(id).then(() => {
    if (currentConversationId === id) {
      startNewConversation()
    }
    renderHistoryList()
  })
}

// Panel backdrop removed - no dark overlay
function updatePanelBackdrop() {
  // Backdrop disabled to prevent black screen on small windows
}

function closeHistoryPanel() {
  historyPanel.classList.remove("open")
  updatePanelBackdrop()
  // Reset scroll when closing
  const historyList = document.getElementById("historyList")
  if (historyList) {
    historyList.scrollTop = 0
  }
}

// ==============================
// TIME GROUPING HELPERS
// ==============================
function getTimeGroup(timestamp) {
  if (!timestamp) return null
  const d = new Date(timestamp)
  const now = new Date()
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const yesterday = new Date(today.getTime() - 86400000)
  const weekAgo = new Date(today.getTime() - 7 * 86400000)
  const msgDate = new Date(d.getFullYear(), d.getMonth(), d.getDate())

  if (msgDate.getTime() >= today.getTime()) return "Today"
  if (msgDate.getTime() >= yesterday.getTime()) return "Yesterday"
  if (msgDate.getTime() >= weekAgo.getTime()) return "This Week"
  return "Earlier"
}

function highlightText(text, query) {
  if (!query) return escapeHtml(text)
  const escaped = escapeHtml(text)
  const regex = new RegExp("(" + query.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + ")", "gi")
  return escaped.replace(regex, '<span class="history-highlight">$1</span>')
}

// ==============================
// RENDER HISTORY LIST (flagship)
// ==============================
async function renderHistoryList() {
  const list = await window.api.conversationList()
  const searchQuery = (document.getElementById("historySearch")?.value || "").toLowerCase().trim()

   // Show loading state with spinner
  if (historyList) {
    historyList.innerHTML = `
      <div class="history-loading">
        <div class="history-loading-spinner"></div>
        <div>Loading conversations...</div>
      </div>
    `
  }

  // Load full conversations for search + preview snippets
  let searchMatches = null
  if (searchQuery) {
    // Limit search to most recent 50 conversations to prevent UI freeze
    const limitedList = list.slice(0, 50)
    const allConvs = await Promise.all(limitedList.map(c => window.api.conversationLoad(c.id)))
    searchMatches = {}
    allConvs.forEach(conv => {
      if (!conv) return
      const ql = searchQuery.toLowerCase()
      const titleMatch = conv.title.toLowerCase().includes(ql)
      const msgMatch = conv.messages?.find(m => m.text.toLowerCase().includes(ql))
      if (titleMatch || msgMatch) {
        searchMatches[conv.id] = { conv, msgMatch }
      }
    })
  }

  // Filter by search
  let filtered = list
  if (searchQuery && searchMatches) {
    filtered = list.filter(c => searchMatches[c.id])
  }

  // Separate pinned and unpinned
  const pinned = filtered.filter(c => c.pinned)
  const unpinned = filtered.filter(c => !c.pinned)

  // Sort
  const sortKey = historySortBy
  const sortFn = (a, b) => {
    if (sortKey === "title") return a.title.localeCompare(b.title)
    if (sortKey === "messageCount") return (b.messageCount || 0) - (a.messageCount || 0)
    return (b[sortKey] || 0) - (a[sortKey] || 0)
  }

  const sortedPinned = pinned.sort(sortFn)
  // Limit unpinned to prevent UI freeze (show max 100 conversations)
  const sortedUnpinned = unpinned.sort(sortFn).slice(0, 100)

  // Group each list
  const groupConversations = (convs) => {
    const groups = {}
    convs.forEach(conv => {
      const group = getTimeGroup(conv.updatedAt)
      if (!groups[group]) groups[group] = []
      groups[group].push(conv)
    })
    return groups
  }

  const pinnedGroups = groupConversations(sortedPinned)
  const unpinnedGroups = groupConversations(sortedUnpinned)

  // Update count badge
  const countEl = document.getElementById("historyCount")
  if (countEl) {
    countEl.textContent = filtered.length > 0 ? `(${filtered.length})` : ""
  }

  historyList.innerHTML = ""

  if (filtered.length === 0) {
    const icon = searchQuery ? "&#128270;" : "&#10022;"
    const msg = searchQuery ? "No matches found" : "No conversations yet"
    historyList.innerHTML = `
      <div class="history-empty">
        <div class="history-empty-icon">${icon}</div>
        <div>${msg}</div>
      </div>
    `
    return
  }

  // Render a group section
  const renderGroup = (groupName, convs, isPinnedSection) => {
    if (convs.length === 0) return

    const groupHeader = document.createElement("div")
    groupHeader.className = "history-group-header"
    groupHeader.textContent = groupName + (isPinnedSection ? "  (Pinned)" : "")
    historyList.appendChild(groupHeader)

    convs.forEach(conv => {
      const isActive = conv.id === currentConversationId
      const msgCount = conv.messageCount || 0
      const lastMsg = conv.messages?.slice(-1)[0]
      const mode = lastMsg?.mode || "adaptive"
      const firstUserMsg = conv.messages?.find(m => m.role === "user")

      // Build preview: prefer user question, then AI answer
      let preview = ""
      let previewRole = ""
      if (searchQuery && searchMatches && searchMatches[conv.id]) {
        const match = searchMatches[conv.id].msgMatch
        if (match) {
          const idx = match.text.toLowerCase().indexOf(searchQuery.toLowerCase())
          const start = Math.max(0, idx - 30)
          const end = Math.min(match.text.length, idx + searchQuery.length + 30)
          preview = (start > 0 ? "…" : "") + match.text.substring(start, end).replace(/\n/g, " ") + (end < match.text.length ? "…" : "")
          previewRole = match.role || "user"
        }
      } else if (firstUserMsg) {
        // Show first user question as preview (most informative)
        preview = firstUserMsg.text.substring(0, 80).replace(/\n/g, " ").trim() + (firstUserMsg.text.length > 80 ? "…" : "")
        previewRole = "user"
      } else if (conv.messages && conv.messages.length > 0) {
        const lastAssistant = [...conv.messages].reverse().find(m => m.role === "assistant")
        if (lastAssistant) {
          preview = lastAssistant.text.substring(0, 80).replace(/\n/g, " ").trim() + (lastAssistant.text.length > 80 ? "…" : "")
          previewRole = "assistant"
        }
      }

      // Mode badge initials
      const modeBadge = {
        adaptive: "A", auto: "A", fast: "F", cloud: "C",
        universal: "U", interview: "I", reasoning: "R", code: "C",
        turbo: "T", instant: "I"
      }
      const icon = modeBadge[mode] || "?"
      const previewLabel = previewRole === "user" ? "You" : "AI"

      const item = document.createElement("div")
      item.className = "history-item" + (isActive ? " active" : "")
      item.setAttribute("data-id", conv.id)

      item.innerHTML = `
        <div class="history-item-checkbox" style="display: none;" title="Select">
          <div class="checkbox-box"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/></svg></div>
        </div>
        <div class="history-item-icon">${icon}</div>
        <div class="history-item-content">
          <div class="history-item-top">
            ${conv.pinned ? '<span class="pin-icon" title="Pinned"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="17" x2="12" y2="22"/><path d="M5 17h14v-4H5v4z"/><path d="M15 7V5H9v2"/><path d="M12 7v5"/></svg></span>' : ''}
            <div class="history-item-title">${highlightText(conv.title, searchQuery)}</div>
          </div>
          ${preview ? `<div class="history-item-preview"><span class="preview-role-label">${previewLabel}:</span> ${highlightText(preview, searchQuery)}</div>` : ""}
          <div class="history-item-meta">
            <span class="history-item-date">${formatDate(conv.updatedAt)}</span>
            <span class="history-item-msg-count">${msgCount} msg${msgCount !== 1 ? "s" : ""}</span>
            <span class="history-item-mode">${mode}</span>
          </div>
        </div>
        <div class="history-item-actions">
          <button class="history-icon-btn" data-action="resume" data-id="${conv.id}" title="Resume">&#9654;</button>
          <button class="history-icon-btn" data-action="pin" data-id="${conv.id}" title="${conv.pinned ? 'Unpin' : 'Pin'}">${conv.pinned ? "&#9650;" : "&#9651;"}</button>
          <button class="history-icon-btn history-menu-btn" data-id="${conv.id}" title="More">&#8226;&#8226;&#8226;</button>
        </div>
      `
      historyList.appendChild(item)
    })
  }

  // Render pinned groups first
  if (sortedPinned.length > 0) {
    Object.keys(pinnedGroups).forEach(group => renderGroup(group, pinnedGroups[group], true))
  }

  // Render unpinned groups
  Object.keys(unpinnedGroups).forEach(group => renderGroup(group, unpinnedGroups[group], false))

   // Show limited message if there are more conversations
  if (unpinned.length > 100) {
    const limitedMsg = document.createElement("div")
    limitedMsg.className = "history-info-message"
    limitedMsg.innerHTML = `
      <div style="padding: 12px; text-align: center; color: var(--text-dim); font-size: 0.8em; opacity: 0.8; border-top: 1px solid var(--line); margin-top: 8px;">
        Showing <b>100</b> of <b>${unpinned.length}</b> conversations
        <br/>
        <span style="font-size: 0.9em; opacity: 0.7;">Use search to find older ones</span>
      </div>
    `
    historyList.appendChild(limitedMsg)
  }

  // Ensure scroll is at top after rendering
  historyList.scrollTop = 0
}

// ==============================
// HISTORY DROPDOWN — EVENT DELEGATION
// ==============================
let openDropdown = null

document.addEventListener("click", (e) => {
  // Menu button clicked — toggle dropdown
  const menuBtn = e.target.closest(".history-menu-btn")
  if (menuBtn) {
    e.stopPropagation()
    e.preventDefault()
    const item = menuBtn.closest(".history-item")
    const convId = item?.getAttribute("data-id")
    const convData = item ? { convId, item } : null

    // Remove any existing portal dropdowns
    document.querySelectorAll(".history-dropdown-portal").forEach(d => d.remove())

    if (openDropdown) {
      openDropdown = null
      return
    }

    // Create dropdown as portal in body (avoids stacking context clipping)
    const dropdown = document.createElement("div")
    dropdown.className = "history-dropdown history-dropdown-portal"
    dropdown.dataset.convId = convId
    dropdown.innerHTML = `
      <button class="history-dropdown-item" data-action="resume" data-id="${convId}"><span class="history-dropdown-icon">&#9654;</span>Resume</button>
      <button class="history-dropdown-item" data-action="rename" data-id="${convId}"><span class="history-dropdown-icon">&#9998;</span>Rename</button>
      <button class="history-dropdown-item" data-action="export" data-id="${convId}"><span class="history-dropdown-icon">&#9142;</span>Export</button>
      <button class="history-dropdown-item" data-action="copy" data-id="${convId}"><span class="history-dropdown-icon">&#9094;</span>Copy</button>
      <div class="app-menu-separator"></div>
      <button class="history-dropdown-item danger" data-action="delete" data-id="${convId}"><span class="history-dropdown-icon">&#128465;</span>Delete</button>
    `

    // Smart position dropdown to stay within viewport
    const rect = menuBtn.getBoundingClientRect()
    const dropdownRect = dropdown.getBoundingClientRect()
    const dropdownWidth = 150
    const dropdownHeight = 180 // approximate
    const padding = 10

    let top, left

    // Check available space on all sides
    const spaceBelow = window.innerHeight - rect.bottom
    const spaceAbove = rect.top
    const spaceRight = window.innerWidth - rect.right
    const spaceLeft = rect.left

    // Prefer below, but if not enough space, show above
    if (spaceBelow >= dropdownHeight + padding || spaceBelow > spaceAbove) {
      top = rect.bottom + 4
    } else {
      top = rect.top - dropdownHeight - 4
    }

    // Prefer left of button (inside panel), but if not enough space, show right
    if (spaceLeft >= dropdownWidth + padding) {
      left = rect.left - dropdownWidth - 4
    } else if (spaceRight >= dropdownWidth + padding) {
      left = rect.right + 4
    } else {
      // Center it if neither side has enough space
      left = Math.max(padding, (window.innerWidth - dropdownWidth) / 2)
    }

    // Final bounds check
    left = Math.max(padding, Math.min(left, window.innerWidth - dropdownWidth - padding))
    top = Math.max(padding, Math.min(top, window.innerHeight - dropdownHeight - padding))

    dropdown.style.top = top + "px"
    dropdown.style.left = left + "px"
    dropdown.style.right = "auto"

    document.body.appendChild(dropdown)
    requestAnimationFrame(() => dropdown.classList.add("open"))
    openDropdown = dropdown
    return
  }

  // Dropdown item clicked — handle action
  const dropdownItem = e.target.closest(".history-dropdown-item")
  if (dropdownItem) {
    e.stopPropagation()
    const action = dropdownItem.getAttribute("data-action")
    const id = dropdownItem.getAttribute("data-id")

    if (action === "resume") {
      document.querySelectorAll(".history-dropdown.open").forEach(d => d.remove())
      openDropdown = null
      window.api.conversationLoad(id).then(full => {
        if (full) { loadConversationIntoUI(full); closeHistoryPanel() }
      })
    } else if (action === "pin") {
      document.querySelectorAll(".history-dropdown.open").forEach(d => d.remove())
      openDropdown = null
      pinConversation(id)
    } else if (action === "rename") {
      // Don't remove dropdown yet - prompt needs it as parent
      window.api.conversationLoad(id).then(full => {
        document.querySelectorAll(".history-dropdown.open").forEach(d => d.remove())
        openDropdown = null
        if (full) renameConversation(full)
      })
    } else if (action === "export") {
      document.querySelectorAll(".history-dropdown.open").forEach(d => d.remove())
      openDropdown = null
      window.api.conversationLoad(id).then(full => { if (full) exportConversation(full) })
    } else if (action === "copy") {
      document.querySelectorAll(".history-dropdown.open").forEach(d => d.remove())
      openDropdown = null
      window.api.conversationLoad(id).then(full => { if (full) copyConversation(full) })
    } else if (action === "delete") {
      document.querySelectorAll(".history-dropdown.open").forEach(d => d.remove())
      openDropdown = null
      deleteConversation(id)
    }
    return
  }

  // Inline resume/pin button clicked
  const inlineBtn = e.target.closest(".history-item-actions .history-icon-btn:not(.history-menu-btn)")
  if (inlineBtn) {
    e.stopPropagation()
    const action = inlineBtn.getAttribute("data-action")
    const id = inlineBtn.getAttribute("data-id")
    if (action === "resume") {
      window.api.conversationLoad(id).then(full => {
        if (full) { loadConversationIntoUI(full); closeHistoryPanel() }
      })
    } else if (action === "pin") {
      pinConversation(id)
    }
    return
  }

  // Click on history item body — resume conversation OR toggle selection
  const historyItem = e.target.closest(".history-item")
  if (historyItem && !e.target.closest("button")) {
    // Check if in selection mode
    if (selectionMode) {
      // Toggle selection
      historyItem.classList.toggle("selected")
      const checkbox = historyItem.querySelector('.history-item-checkbox .checkbox-box')
      if (checkbox) {
        checkbox.innerHTML = historyItem.classList.contains('selected')
          ? '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><polyline points="9 12 12 15 17 9"/></svg>'
          : '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/></svg>'
      }
      // Update clear chat button text based on selection
      const selectedCount = document.querySelectorAll('.history-item.selected').length
      if (clearChatBtn) {
        clearChatBtn.innerHTML = selectedCount > 0
          ? `<span><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;margin-right:4px"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg></span>Delete (${selectedCount})`
          : '<span><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;margin-right:4px"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg></span>Clear Chat'
      }
    } else {
      // Normal mode - load conversation
      const id = historyItem.getAttribute("data-id")
      if (id) {
        window.api.conversationLoad(id).then(full => {
          if (full) { loadConversationIntoUI(full); closeHistoryPanel() }
        })
      }
    }
    return
  }

  // Clicked elsewhere — close any open dropdown
  if (openDropdown) {
    openDropdown.remove()
    openDropdown = null
  }
})
function removeWelcome() {
  if (chatWelcome && chatWelcome.parentNode) {
    chatWelcome.parentNode.removeChild(chatWelcome)
  }
}

function scrollChat() {
  requestAnimationFrame(() => {
    chatArea.scrollTop = chatArea.scrollHeight
  })
}

function addMessage(role, text) {
  removeWelcome()

  const msg = document.createElement("div")
  msg.className = "chat-message " + role

  const label = role === "user" ? "You" : "AI"
  const bubble = document.createElement("div")
  bubble.className = "msg-bubble"

  // Add loading state for empty assistant messages
  if (role === "assistant" && (!text || text === "")) {
    msg.classList.add("loading")
    bubble.innerHTML = '<span class="loading-indicator"><span class="dot"></span><span class="dot"></span><span class="dot"></span></span>'
  } else {
    setBubbleText(bubble, text)
  }

  msg.innerHTML = `<span class="msg-label">${label}</span><span class="msg-time">${new Date().toLocaleTimeString()}</span>`
  msg.appendChild(bubble)

  // Add copy button for assistant messages
  if (role === "assistant") {
    const actions = document.createElement("div")
    actions.className = "msg-actions"
    const copyBtn = document.createElement("button")
    copyBtn.className = "msg-copy-btn"
    copyBtn.textContent = "Copy"
    copyBtn.addEventListener("click", () => {
      // Get text from bubble's data attribute or innerText
      let textToCopy = bubble.dataset.fullText || bubble.innerText || text || ""
      textToCopy = textToCopy.replace(/\[.*?\]\s*$/, "").trim()
      textToCopy = textToCopy.replace(/^AI:\s*/i, "").trim()
      if (!textToCopy) {
        copyBtn.textContent = "Empty"
        setTimeout(() => { copyBtn.textContent = "Copy" }, 1000)
        return
      }
      window.api.copyToClipboard(textToCopy).then(() => {
        copyBtn.textContent = "Copied"
        copyBtn.classList.add("copied")
        setTimeout(() => { copyBtn.textContent = "Copy"; copyBtn.classList.remove("copied") }, 1500)
      }).catch(() => {
        copyBtn.textContent = "Error"
        setTimeout(() => { copyBtn.textContent = "Copy" }, 1000)
      })
    })
    actions.appendChild(copyBtn)

    // Add Read button for TTS (browser SpeechSynthesis)
    const readBtn = document.createElement("button")
    readBtn.className = "msg-read-btn"
    readBtn.textContent = "Read"
    readBtn.addEventListener("click", () => {
      const textToSpeak = bubble.dataset.fullText || bubble.innerText || text || ""
      if (!textToSpeak.trim()) return
      if (window.speechSynthesis.paused) {
        window.speechSynthesis.resume()
        readBtn.textContent = "Pause"
        return
      }
      if (window.speechSynthesis.speaking) {
        window.speechSynthesis.cancel()
        readBtn.textContent = "Read"
        return
      }
      const utterance = new SpeechSynthesisUtterance(textToSpeak)
      utterance.rate = 1.2
      utterance.onend = () => { readBtn.textContent = "Read" }
      utterance.onerror = () => { readBtn.textContent = "Read" }
      window.speechSynthesis.speak(utterance)
      readBtn.textContent = "Pause"
    })
    actions.appendChild(readBtn)

    msg.appendChild(actions)
  }

  chatArea.appendChild(msg)

  scrollChat()

  // Track message and auto-save (skip during history load)
  if (!suppressAutoSave) {
    const modeTag = document.querySelector(".mode-tag")
    const currentMode = modeTag ? modeTag.textContent.replace(/[\[\]]/g, "").trim() : "adaptive"
    currentMessages.push({ role, text, timestamp: Date.now(), mode: currentMode })
    saveCurrentConversation()
  }

  return msg
}

function addErrorMessage(text) {
  removeWelcome()

  const msg = document.createElement("div")
  msg.className = "chat-message error"

  const bubble = document.createElement("div")
  bubble.className = "msg-bubble"
  bubble.textContent = text

  msg.innerHTML = `<span class="msg-label">Error</span>`
  msg.appendChild(bubble)
  chatArea.appendChild(msg)

  scrollChat()
  return msg
}

/**
 * Escape HTML entities to prevent XSS attacks.
 * Handles special characters: &, <, >, ", ', `
 */
function escapeHtml(text) {
  if (!text) return ""
  const str = String(text)
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;")
    .replace(/`/g, "&#x60;")
}

/**
 * Sanitize URL to prevent XSS.
 * Returns empty string if URL is invalid or uses dangerous protocols.
 */
function sanitizeUrl(url) {
  if (!url || typeof url !== "string") return ""
  try {
    const parsed = new URL(url)
    // Only allow safe protocols
    const safeProtocols = ["http:", "https:", "ftp:", "mailto:"]
    if (!safeProtocols.includes(parsed.protocol)) {
      return ""
    }
    return url
  } catch {
    return ""
  }
}

/**
 * Validate and sanitize user input.
 * Returns the sanitized input or empty string if invalid.
 */
function sanitizeInput(text) {
  if (!text || typeof text !== "string") return ""
  // Remove null bytes and control characters (except newline, tab)
  // Don't trim() here — formatMessage handles that for text content
  // but we need to preserve markers like {{CODE_BLOCK_0}}
  return text.replace(/[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]/g, "")
}

// Copy code block from a code block's copy button (called from onclick)
function copyCodeBlock(btn) {
  const pre = btn.closest(".code-block")
  if (!pre) return
  const code = pre.querySelector(".code-content")
  if (!code) return
  const tmp = document.createElement("div")
  tmp.innerHTML = code.innerHTML
  const text = tmp.textContent || tmp.innerText || ""
  navigator.clipboard.writeText(text).then(() => {
    btn.textContent = "Copied!"
    setTimeout(() => { btn.textContent = "Copy" }, 1500)
  }).catch(() => {
    fallbackCopyText(text)
    btn.textContent = "Copied!"
    setTimeout(() => { btn.textContent = "Copy" }, 1500)
  })
}

// Detect language from code content if not specified
function detectCodeLanguage(code) {
  const trimmed = code.trim()
  if (trimmed.startsWith("apiVersion:") || trimmed.includes("Kind:") || trimmed.includes("metadata:")) return "yaml"
  else if (trimmed.startsWith("import ") || trimmed.startsWith("package ")) return "java"
  else if (trimmed.startsWith("from ") || trimmed.startsWith("import ") && trimmed.includes("def ")) return "python"
  else if (trimmed.includes("function") || trimmed.includes("const ") || trimmed.includes("let ") || trimmed.includes("=>")) return "javascript"
  else if (trimmed.includes("public class") || trimmed.includes("namespace ") || trimmed.includes("using System")) return "csharp"
  else if (trimmed.includes("func ") && trimmed.includes("package ")) return "go"
  else if (trimmed.includes("fn ") && trimmed.includes("let mut")) return "rust"
  else if (trimmed.includes("<") && trimmed.includes(">") && (trimmed.includes("/>") || trimmed.includes("</"))) return "xml"
  else if (trimmed.startsWith("{") && trimmed.includes(":")) return "json"
  return "code"
}

// Simple YAML syntax highlighter - works without hljs language detection
function highlightYAML(code) {
  if (!code) return ""
  const escaped = escapeHtml(code)
  const lines = escaped.split("\n")
  const result = []

  for (const line of lines) {
    // Match: key: value (with optional indent)
    const keyMatch = line.match(/^(\s*)([a-zA-Z_][a-zA-Z0-9_-]*)(\s*:\s*)(.*)/)
    if (keyMatch) {
      const [, indent, key, colon, value] = keyMatch
      let highlighted = `${indent}<span class="yaml-key">${key}</span>${colon}`

      if (value) {
        // Check if value is quoted string
        const strMatch = value.match(/^(['"])(.*)(\1)\s*$/)
        if (strMatch) {
          highlighted += `<span class="yaml-string">${strMatch[1]}${strMatch[2]}${strMatch[1]}</span>`
        }
        // Check if number
        else if (/^-?\d+\.?\d*$/.test(value.trim())) {
          highlighted += `<span class="yaml-number">${value.trim()}</span>`
        }
        // Check if boolean or null
        else if (/^(true|false|null|yes|no)$/i.test(value.trim())) {
          highlighted += `<span class="yaml-bool">${value.trim()}</span>`
        }
        // Otherwise it's a plain value (string)
        else {
          highlighted += `<span class="yaml-string">${value}</span>`
        }
      }
      result.push(highlighted)
    }
    // Match: - list item (dash at start of line after indent)
    else if (line.match(/^(\s*)-\s+/)) {
      result.push(line.replace(/^(\s*)(-\s+)(.*)/, '$1<span class="yaml-dash">$2</span><span class="yaml-string">$3</span>'))
    }
    // Regular text line
    else {
      result.push(line)
    }
  }

  return result.join("\n")
}

// Helper to highlight code using hljs (already loaded locally)
function highlightCode(code, lang) {
  // For YAML, use our custom highlighter for better results
  if (lang === "yaml") {
    return highlightYAML(code)
  }

  if (window.hljs && window.hljs.highlight) {
    try {
      const result = window.hljs.highlight(code, { language: lang, ignoreIllegals: true })
      return result.value
    } catch (e) {
      // Fall back to YAML highlighter for k8s-like content
      if (code.includes("apiVersion:") || code.includes("Kind:") || code.includes("metadata:")) {
        return highlightYAML(code)
      }
      return escapeHtml(code)
    }
  }
  // Fall back to YAML highlighter
  if (code.includes("apiVersion:") || code.includes("Kind:") || code.includes("metadata:")) {
    return highlightYAML(code)
  }
  return escapeHtml(code)
}

// ==============================
// INDUSTRIAL-GRADE MESSAGE FORMATTING ENGINE
// ==============================

/**
 * Full message formatter — handles code blocks, headings, lists,
 * paragraphs, blockquotes, and inline markdown (bold, italic, code).
 */
function formatMessage(rawText) {
  if (!rawText) return ""

  // Sanitize input first
  const sanitizedText = sanitizeInput(rawText)

  // Step 1: Extract code blocks BEFORE any text processing
  const codeBlocks = []
  const codeBlockLangs = []
  // Regex: capture optional language tag, then code until closing ```
  let text = sanitizedText.replace(/```([a-zA-Z0-9_+\-.]{0,20})\s*([\s\S]*?)```/g, (_, lang, code) => {
    codeBlocks.push(code)
    // Validate language tag: reject concatenated words like "pythondef"
    let cleanLang = (lang || "").toLowerCase().trim()
    // Heuristic: if the code starts without whitespace and the lang looks like lang+keyword, it's invalid
    const commonKeywords = /def|class|func|function|const|let|var|import|from|if|for|while|return|struct|interface|impl|fn|pub|use|package/
    if (cleanLang.length > 15 || (cleanLang.length > 3 && commonKeywords.test(cleanLang))) {
      cleanLang = ""
    }
    codeBlockLangs.push(cleanLang || "code")
    return `§K8CODE${codeBlocks.length - 1}K8§`
  })

  // Step 2: Process inline code (must be before other replacements)
  text = text.replace(/`([^`]+)`/g, (_, code) => `<code class="inline-code">${escapeHtml(code)}</code>`)

  // Step 3: Bold, italic, strikethrough
  text = text.replace(/\*\*\*([\s\S]+?)\*\*\*/g, "<strong>$1</strong>")
  text = text.replace(/\*\*([\s\S]+?)\*\*/g, "<strong>$1</strong>")
  text = text.replace(/\*([\s\S]+?)\*/g, "<em>$1</em>")
  text = text.replace(/___([\s\S]+?)___/g, "<strong>$1</strong>")
  text = text.replace(/__([\s\S]+?)__/g, "<strong>$1</strong>")
  text = text.replace(/_(?![_\s])([\s\S]+?)_(?![_\s])/g, "<em>$1</em>")
  text = text.replace(/~~([\s\S]+?)~~/g, "<del>$1</del>")

  // Step 4: Headings
  text = text.replace(/^###\s*(.+)$/gm, "<h4>$1</h4>")
  text = text.replace(/^##\s*(.+)$/gm, "<h3>$1</h3>")
  text = text.replace(/^#\s*(.+)$/gm, "<h2>$1</h2>")

  // Step 5: Blockquotes
  text = text.replace(/^&gt; (.+)$/gm, "<blockquote>$1</blockquote>")

  // Step 6: Horizontal rules
  text = text.replace(/^---+$/gm, "<hr>")
  text = text.replace(/^\*\*\*+$/gm, "<hr>")

  // Step 7: Inline links [text](url) - with URL sanitization
  text = text.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (_, text, url) => {
    const safeUrl = sanitizeUrl(url)
    if (!safeUrl) {
      return escapeHtml(text) // Return plain text if URL is unsafe
    }
    return `<a href="${escapeHtml(safeUrl)}" target="_blank" rel="noopener noreferrer">${escapeHtml(text)}</a>`
  })

  // Step 8: Parse lists (bullet and numbered)
  text = parseLists(text)

  // Step 9: Restore code blocks as multi-line code with syntax highlighting
  for (let i = 0; i < codeBlocks.length; i++) {
    const code = codeBlocks[i]
    const lang = codeBlockLangs[i] || detectCodeLanguage(code.trim())
    const highlighted = highlightCode(code.trim(), lang)
    const codeHtml = `<pre class="code-block"><code class="hljs language-${lang}">${highlighted}</code></pre>`
    text = text.replace(`§K8CODE${i}K8§`, codeHtml)
  }

  // Step 10: Paragraphs — split on double newlines but preserve code blocks
  const paragraphParts = []
  // Split but keep track of code block markers
  const parts = text.split(/\n\n+/)
  for (const part of parts) {
    const trimmed = part.trim()
    if (!trimmed) continue
    // Already wrapped in block-level tag?
    if (trimmed.startsWith("<h") || trimmed.startsWith("<ul") || trimmed.startsWith("<ol") ||
        trimmed.startsWith("<blockquote") || trimmed.startsWith("<pre") || trimmed.startsWith("<hr")) {
      paragraphParts.push(trimmed)
    } else {
      // Check if this contains code blocks
      if (trimmed.includes("<pre class=\"code-block\"")) {
        paragraphParts.push(trimmed)
      } else {
        paragraphParts.push(`<p>${trimmed.replace(/\n/g, "<br>")}</p>`)
      }
    }
  }
  text = paragraphParts.join("\n")

  return text
}

/**
 * Parse bullet and numbered lists into proper HTML.
 */
function parseLists(text) {
  const lines = text.split("\n")
  const result = []
  let inList = false
  let listType = null

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]
    const trimmed = line.trim()

    // Check for list item (space after number is optional)
    const bulletMatch = trimmed.match(/^[-*+]\s+(.*)/)
    const numberedMatch = trimmed.match(/^(\d+)\.\s*(.*)/)
    const letteredMatch = trimmed.match(/^([a-z])\.\s*(.*)/)

    if (bulletMatch) {
      if (!inList || listType !== "ul") {
        if (inList) result.push(listType === "ul" ? "</ul>" : "</ol>")
        result.push("<ul class='chat-list'>")
        inList = true
        listType = "ul"
      }
      const content = bulletMatch[1]
        .replace(/\*\*([\s\S]+?)\*\*/g, "<strong>$1</strong>")
        .replace(/\*([\s\S]+?)\*/g, "<em>$1</em>")
        .replace(/`([^`]+)`/g, `<code class="inline-code">$1</code>`)
      result.push(`<li>${content}</li>`)
    } else if (numberedMatch || letteredMatch) {
      if (!inList || listType !== "ol") {
        if (inList) result.push(listType === "ul" ? "</ul>" : "</ol>")
        result.push("<ol class='chat-list'>")
        inList = true
        listType = "ol"
      }
      const rawContent = numberedMatch ? (numberedMatch[2] || "") : (letteredMatch[2] || "")
      const content = rawContent
        .replace(/\*\*([\s\S]+?)\*\*/g, "<strong>$1</strong>")
        .replace(/\*([\s\S]+?)\*/g, "<em>$1</em>")
        .replace(/`([^`]+)`/g, `<code class="inline-code">$1</code>`)
      if (content.trim()) result.push(`<li>${content}</li>`)
    } else {
      if (inList) {
        result.push(listType === "ul" ? "</ul>" : "</ol>")
        inList = false
        listType = null
      }
      result.push(line)
    }
  }

  if (inList) {
    result.push(listType === "ul" ? "</ul>" : "</ol>")
  }

  return result.join("\n")
}

/**
 * Typing effect — appends a single word to the bubble's visible text node
 * without full re-render. Returns the new visible text length.
 */
function typeWord(bubble, word) {
  if (!bubble._typingNode) {
    bubble._typingNode = document.createTextNode("")
    bubble._typingCursor = document.createElement("span")
    bubble._typingCursor.className = "typing-cursor"
    bubble._typingCursor.textContent = "\u00A0"
    bubble.innerHTML = ""
    bubble.appendChild(bubble._typingNode)
    bubble.appendChild(bubble._typingCursor)
  }
  bubble._typingNode.textContent += word + " "
  bubble._typingCursor.textContent = "\u00A0"
  return bubble._typingNode.textContent.length
}

/**
 * Finalize bubble after streaming — replace typing nodes with full HTML.
 */
function finalizeBubble(bubble, html) {
  bubble._typing = false
  bubble._textNode = null
  bubble._cursorSpan = null
  // Remove loading class from message element to stop spinner animation
  const msgEl = bubble.closest(".chat-message")
  if (msgEl) msgEl.classList.remove("loading")
  // Store the plain text for copy button before setting HTML
  const tempDiv = document.createElement("div")
  tempDiv.innerHTML = html
  bubble.dataset.fullText = tempDiv.textContent || tempDiv.innerText || ""
  bubble.innerHTML = html
}

/**
 * Helper to set text with formatting.
 * During streaming (showCursor=true): raw text + blinking cursor.
 * On final render: full formatMessage() formatting once.
 */
function setBubbleText(bubble, text, showCursor = false) {
  if (!text && text !== 0) {
    bubble.innerHTML = ""
    return
  }

  const loadingIndicator = bubble.querySelector(".loading-indicator")
  if (loadingIndicator) loadingIndicator.remove()

  // During streaming: apply basic formatting with cursor
  if (showCursor) {
    if (!bubble._typing) {
      bubble._typing = true
      bubble.innerHTML = ""
      bubble._cursorSpan = document.createElement("span")
      bubble._cursorSpan.className = "typing-cursor"
      bubble._cursorSpan.textContent = "\u00A0"
    }
    // Apply basic formatting even during streaming
    bubble.innerHTML = formatMessage(text) + " "
    bubble.appendChild(bubble._cursorSpan)
    // Store raw text for copy button
    bubble.dataset.fullText = text
    return
  }

  // Final: full formatting
  finalizeBubble(bubble, formatMessage(text))
}

// ==============================
// BATCHED DOM UPDATE UTILITIES
// ==============================
let _pendingText = ''
let _rafId = null

function batchUpdateBubble(text) {
  _pendingText += text
  if (!_rafId) {
    _rafId = requestAnimationFrame(() => {
      if (typeof setBubbleText === 'function' && latestBotMessage) {
        setBubbleText(latestBotMessage.bubble, _pendingText, true)
      }
      scrollChat()
      _pendingText = ''
      _rafId = null
    })
  }
}

let _saveTimeout = null
function debouncedSave() {
  if (_saveTimeout) clearTimeout(_saveTimeout)
  _saveTimeout = setTimeout(() => {
    saveCurrentConversation()
    _saveTimeout = null
  }, 3000)
}

// ==============================
// SSE STREAMING — READER + DISPATCH
// ==============================

/**
 * Parse SSE event data from a buffer.
 * Returns an array of {event, data} objects as buffer is consumed.
 */
function parseSSEEvents(buffer) {
  const events = []
  // Normalize line endings
  const text = buffer.replace(/\r\n/g, "\n").replace(/\r/g, "\n")
  const lines = text.split("\n")
  buffer = ""

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]
    if (line === "" || line === undefined) {
      continue
    }
    if (line.startsWith("event:")) {
      const eventType = line.slice(6).trim()
      // Read the next line as data
      if (i + 1 < lines.length) {
        const dataLine = lines[++i]
        if (dataLine.startsWith("data:")) {
          const dataStr = dataLine.slice(5).trim()
          try {
            const data = JSON.parse(dataStr)
            events.push({ event: eventType, data })
          } catch {
            events.push({ event: eventType, data: { raw: dataStr } })
          }
        }
      }
    } else if (line.startsWith("data:")) {
      const dataStr = line.slice(5).trim()
      try {
        const data = JSON.parse(dataStr)
        events.push({ event: "message", data })
      } catch {
        events.push({ event: "message", data: { raw: dataStr } })
      }
    } else if (!line.startsWith(":") && line.trim()) {
      // Partial line — keep in buffer for next iteration
      buffer += line + "\n"
    }
  }
  return { events, buffer }
}

/**
 * Parse SSE events from a fetch ReadableStream.
 * Yields raw event objects as they arrive.
 */
// Robust SSE parser — yields {event, data} objects from a fetch ReadableStream
async function* SSEStream(reader, decoder, signal) {
  let buffer = ""
  const LINE_FEED = 10
  let eventType = "message"

  try {
    while (true) {
      if (signal?.aborted) break

      let readPromise
      const abortHandler = () => {
        if (readPromise) readPromise.cancel?.()
      }
      signal?.addEventListener("abort", abortHandler)

      let result
      try {
        result = await reader.read()
      } catch(err) {
        signal?.removeEventListener("abort", abortHandler)
        if (err.message?.includes("aborted")) {
          yield { event: "stream-done", data: {} }
          break
        }
        throw err
      }
      signal?.removeEventListener("abort", abortHandler)

      const { done, value } = result

      if (done) {
        // Yield any remaining buffer content (might be a partial last event)
        if (buffer.trim()) {
          const line = buffer.trim()
          if (line.startsWith("data:")) {
            try {
              yield { event: eventType, data: JSON.parse(line.slice(5).trim()) }
            } catch {}
          }
        }
        // Always yield a special done event so the caller knows stream ended
        yield { event: "stream-done", data: {} }
        break
      }

      buffer += decoder.decode(value, { stream: true })

      // Process complete lines
      while (buffer.includes(LINE_FEED)) {
        if (signal?.aborted) break

        const lfIndex = buffer.indexOf(LINE_FEED)
        const line = buffer.slice(0, lfIndex)
        buffer = buffer.slice(lfIndex + 1)

        if (!line.trim() || line.startsWith(":")) continue

        if (line.startsWith("event:")) {
          eventType = line.slice(6).trim()
          continue
        }

        if (line.startsWith("data:")) {
          const dataStr = line.slice(5).trim()
          try {
            yield { event: eventType, data: JSON.parse(dataStr) }
          } catch (e) {
            console.warn("[SSE] Bad JSON:", dataStr, e.message)
          }
        } else {
          // Partial line — put it back and wait for more data
          buffer = line + "\n" + buffer
          break
        }
      }
    }
  } catch (err) {
    if (err.message !== "aborted") {
      console.error("[SSE] Stream error:", err)
      yield { event: "stream-error", data: { message: err.message } }
    }
  }
}

// ==============================
// STREAM AI RESPONSE (SSE-AWARE)
// ==============================
// Parse SSE events from a complete text body (non-streaming)
function parseSSEFromText(text) {
  const events = []
  if (!text) return events

  // Split on double newlines (SSE message separator)
  const messages = text.split(/\n\n+/)
  let eventType = "message"

  for (const msg of messages) {
    const lines = msg.split("\n")
    eventType = "message"
    let dataStr = ""

    for (const line of lines) {
      if (line.startsWith("event:")) {
        eventType = line.slice(6).trim()
      } else if (line.startsWith("data:")) {
        dataStr = line.slice(5).trim()
        try {
          const data = JSON.parse(dataStr)
          events.push({ event: eventType, data })
        } catch {}
      }
    }
  }
  return events
}

async function streamAIResponse(query) {
  const requestStartTime = Date.now()
  const mode = getSelectedMode()
  const responseStyle = getSelectedResponseStyle()
  const selectedModel = modelSelect ? modelSelect.value : "auto"
  // Cloud models use dashes (e.g. openai-gpt-4o); local Ollama models use colons (e.g. gemma4:latest)
  const isCloudModel = selectedModel && selectedModel !== "auto" && selectedModel.includes("-") && !selectedModel.includes(":")
  const isLocalModel = selectedModel && selectedModel !== "auto" && selectedModel.includes(":")
  const provider = isCloudModel ? selectedModel : (isLocalModel ? selectedModel : "ollama")

  // If "auto" is selected, race all configured providers — fastest wins
  if (selectedModel === "auto") {
    await streamAIRace(query)
    return
  }

  // If the selected model is disabled, warn and fall back to auto-race
  if (isModelDisabled(selectedModel)) {
    addErrorMessage(`${selectedModel} is disabled. Falling back to auto-race.`)
    await streamAIRace(query)
    return
  }
  const contextMessages = getContextMessages()
  const temperature = getSelectedTemperature()
  const streamUrl = window.api.getStreamUrlWithMode(query, mode, responseStyle, provider, contextMessages, temperature)

  const controller = new AbortController()
  const timeoutId = setTimeout(() => {
    console.warn("[streamAIResponse] Timeout — aborting fetch")
    controller.abort()
  }, 60000)

  // Create assistant message with loading animation BEFORE fetch
  streamMessage("assistant", "")

  try {
    const response = await fetch(streamUrl, { signal: controller.signal })
    clearTimeout(timeoutId)

    if (!response.ok) {
      addErrorMessage("AI stream failed")
      setProcessingUI(false)
      return
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ""
    let modelName = null
    let modelProvider = null
    let modelDisplay = null
    let accumulatedText = ""

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split("\n")
      buffer = lines.pop()

      for (const line of lines) {
        if (line.startsWith("event:")) continue
        if (line.startsWith("data:")) {
          const dataStr = line.slice(5).trim()
          let data
          try { data = JSON.parse(dataStr) } catch { continue }

          if (data.type === "error") {
            if (latestBotMessage) {
              setBubbleText(latestBotMessage.bubble,
                `<span class="error-text">Error: ${escapeHtml(data.message || "Unknown error")}</span>`)
            }
            latestBotMessage = null
            setProcessingUI(false)
            return
          }

          if (data.type === "meta") {
            modelName = data.model || modelName
            modelProvider = data.provider || modelProvider
            modelDisplay = data.display || modelDisplay
            if (latestBotMessage) {
              latestBotMessage.modelName = modelDisplay || modelName
              latestBotMessage.modelProvider = modelProvider
              latestBotMessage.modelDisplay = modelDisplay || modelName
              renderModelBadge(latestBotMessage, latestBotMessage.modelDisplay)
            }
            continue
          }

          if (data.type === "chunk") {
            accumulatedText += data.content
            if (latestBotMessage) {
              latestBotMessage.accumulatedText = accumulatedText
              const displayText = accumulatedText
                .replace(/^AI:\s*/i, "")
                .replace(/\[MODEL:[^\]]*\]\s*/g, "")
                .replace(/^Paragraph\s*\d+:\s*/gim, "")
                .replace(/^Conversation history:\s*/gim, "")
                .replace(/^(You|AI)\s*:\s*/gim, "")

              if (displayText.trim() && latestBotMessage.element) {
                latestBotMessage.element.classList.remove("loading")
                const loadingIndicator = latestBotMessage.bubble.querySelector(".loading-indicator")
                if (loadingIndicator) loadingIndicator.remove()
              }

              batchUpdateBubble(displayText)
            }
            continue
          }

          if (data.type === "done") break
        }
      }
    }

    // Final cleanup for non-race mode
    if (latestBotMessage) {
      // Flush any pending batch update
      if (_rafId) {
        cancelAnimationFrame(_rafId)
        _rafId = null
        if (typeof setBubbleText === 'function') {
          setBubbleText(latestBotMessage.bubble, _pendingText, true)
        }
        _pendingText = ''
      }
      let finalText = accumulatedText
        .replace(/^AI:\s*/i, "")
        .replace(/\[MODEL:[^\]]*\]\s*/g, "")
        .replace(/^Paragraph\s*\d+:\s*/gim, "")
        .replace(/^Conversation history:\s*/gim, "")
        .replace(/^(You|AI)\s*:\s*/gim, "")

      latestBotMessage.accumulatedText = finalText
      finalizeBubble(latestBotMessage.bubble, formatMessage(finalText))

      if (latestBotMessage.modelDisplay) {
        const label = latestBotMessage.element.querySelector(".msg-label")
        if (label) {
          let badge = label.querySelector(".model-badge")
          if (!badge) {
            badge = document.createElement("span")
            badge.className = "model-badge"
            label.appendChild(badge)
          }
          badge.classList.remove("streaming-badge")
          badge.textContent = `[${latestBotMessage.modelDisplay}]`
          // Add response time
          const elapsed = Date.now() - requestStartTime
          let timeBadge = label.querySelector(".time-badge")
          if (!timeBadge) {
            timeBadge = document.createElement("span")
            timeBadge.className = "model-badge time-badge"
            label.appendChild(timeBadge)
          }
          timeBadge.textContent = `${(elapsed / 1000).toFixed(1)}s`
        }
      }

      if (!suppressAutoSave) {
        const modeTag = document.querySelector(".mode-tag")
        const currentMode = modeTag ? modeTag.textContent.replace(/[\[\]]/g, "").trim() : "adaptive"
        currentMessages.push({ role: "assistant", text: finalText, timestamp: Date.now(), mode: currentMode })
        debouncedSave()
      }

      latestBotMessage = null
    }

    showSummarizeButton()
    setProcessingUI(false)
  } catch (e) {
    clearTimeout(timeoutId)
    console.error("AI stream error:", e)
    addErrorMessage("AI response failed")
    if (latestBotMessage) latestBotMessage = null
    setProcessingUI(false)
  }
}

// ==============================
// STREAM AI RESPONSE WITH IMAGE (Vision)
// ==============================
async function streamAIResponseWithImage(query, screenshotB64) {
  const mode = getSelectedMode()
  const responseStyle = getSelectedResponseStyle()
  const selectedModel = modelSelect ? modelSelect.value : "auto"
  const contextMessages = getContextMessages()
  const requestStartTime = Date.now()

  // When auto-selected, use race mode to get fastest cloud vision response
  const provider = selectedModel !== "auto" ? selectedModel : "auto"

  // Get enabled providers for vision race (only vision-capable providers)
  const VISION_PROVIDERS = ["openai", "anthropic", "google", "groq"]
  const enabledProviders = []

  let backendProviders = {}
  try {
    backendProviders = await window.api.getProviders()
  } catch (e) {
    console.warn("Could not fetch providers from backend", e)
  }

  const storedResults = await Promise.all(
    VISION_PROVIDERS.map(p => window.api.storeGet("provider_" + p))
  )
  const visionLocalKeyResults = await Promise.all(
    VISION_PROVIDERS.map(async p => {
      try { return (await window.api.hasApiKey(p)).hasKey } catch { return false }
    })
  )
  for (let i = 0; i < VISION_PROVIDERS.length; i++) {
    const p = VISION_PROVIDERS[i]
    const stored = storedResults[i] || {}
    const hasKey = !!backendProviders[p] || visionLocalKeyResults[i]
    if (stored.enabled !== false && hasKey) {
      enabledProviders.push(p)
    }
  }
  // Always include Ollama as fallback
  enabledProviders.push("ollama")

  const formData = new FormData()
  formData.append("query", query)
  // Force race mode when auto-selected for fastest vision response
  formData.append("mode", selectedModel === "auto" ? "race" : mode)
  formData.append("style", responseStyle)
  formData.append("provider", provider)
  formData.append("temperature", getSelectedTemperature())
  if (contextMessages) {
    formData.append("context", JSON.stringify(contextMessages))
  }
  if (screenshotB64) {
    formData.append("image_b64", screenshotB64)
  }
  // Pass enabled providers so backend knows which keys are available
  if (enabledProviders.length > 0) {
    formData.append("enabled", enabledProviders.join(","))
  }

  // Add auth headers explicitly
  const visionHeaders = {}
  try {
    const token = localStorage.getItem('ainotetaker_auth_token')
    if (token) visionHeaders['Authorization'] = `Bearer ${token}`
  } catch {}

  // Create assistant message with loading animation BEFORE fetch
  streamMessage("assistant", "")

  try {
    const response = await fetch(window.api.getAskWithImageUrl(), {
      method: "POST",
      headers: visionHeaders,
      body: formData
    })

    if (!response.ok) {
      if (response.status === 401) {
        addErrorMessage("Session expired. Please log in again.")
        if (window.AuthHelper) { AuthHelper.clearToken(); AuthHelper.ensureAuth() }
      } else {
        addErrorMessage("Vision AI stream failed")
      }
      setProcessingUI(false)
      return
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ""
    let accumulatedText = ""

    let visionDescription = ""
    let visionBubble = null

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split("\n")
      buffer = lines.pop()

      for (const line of lines) {
        if (line.startsWith("event:")) continue
        if (line.startsWith("data:")) {
          const dataStr = line.slice(5).trim()
          let data
          try { data = JSON.parse(dataStr) } catch { continue }

          if (data.type === "error") {
            if (latestBotMessage) {
              setBubbleText(latestBotMessage.bubble,
                `<span class="error-text">Error: ${escapeHtml(data.message || "Unknown error")}</span>`)
            }
            latestBotMessage = null
            setProcessingUI(false)
            return
          }

          // Vision description — Step 1 of two-step pipeline
          if (data.type === "vision") {
            visionDescription += data.content
            // Show vision description in a subtle sub-bubble
            if (latestBotMessage && latestBotMessage.bubble) {
              const visionEl = latestBotMessage.bubble.querySelector(".vision-context") || (() => {
                const el = document.createElement("div")
                el.className = "vision-context"
                el.innerHTML = '<span class="vision-label">&#128247; Screen</span><div class="vision-text"></div>'
                latestBotMessage.bubble.insertBefore(el, latestBotMessage.bubble.firstChild)
                return el
              })()
              const textEl = visionEl.querySelector(".vision-text")
              if (textEl) textEl.textContent = visionDescription
              requestAnimationFrame(scrollChat)
            }
            continue
          }

          // Vision description complete — Step 1 done, collapse vision section
          if (data.type === "vision_done") {
            if (latestBotMessage && latestBotMessage.bubble) {
              const visionEl = latestBotMessage.bubble.querySelector(".vision-context")
              if (visionEl) visionEl.classList.add("collapsed")
            }
            continue
          }

          if (data.type === "meta") {
            if (latestBotMessage) {
              latestBotMessage.modelName = data.model
              latestBotMessage.modelProvider = data.provider
              latestBotMessage.modelDisplay = data.model
              renderModelBadge(latestBotMessage, latestBotMessage.modelDisplay)
            }
            continue
          }

          if (data.type === "chunk") {
            accumulatedText += data.content
            if (latestBotMessage) {
              latestBotMessage.accumulatedText = accumulatedText
              batchUpdateBubble(accumulatedText)
            }
            continue
          }

          if (data.type === "done") break
        }
      }
    }

    // Finalize
    if (latestBotMessage) {
      // Flush any pending batch update
      if (_rafId) {
        cancelAnimationFrame(_rafId)
        _rafId = null
        if (typeof setBubbleText === 'function') {
          setBubbleText(latestBotMessage.bubble, _pendingText, true)
        }
        _pendingText = ''
      }
      latestBotMessage.accumulatedText = accumulatedText
      finalizeBubble(latestBotMessage.bubble, formatMessage(accumulatedText))

      const label = latestBotMessage.element.querySelector(".msg-label")
      if (label) {
        let badge = label.querySelector(".model-badge")
        if (!badge) {
          badge = document.createElement("span")
          badge.className = "model-badge"
          label.appendChild(badge)
        }
        badge.classList.remove("streaming-badge")
        badge.textContent = `[${latestBotMessage.modelDisplay || provider}]`
        const elapsed = Date.now() - requestStartTime
        let timeBadge = label.querySelector(".time-badge")
        if (!timeBadge) {
          timeBadge = document.createElement("span")
          timeBadge.className = "model-badge time-badge"
          label.appendChild(timeBadge)
        }
        timeBadge.textContent = `${(elapsed / 1000).toFixed(1)}s`
      }

      if (!suppressAutoSave) {
        const modeTag = document.querySelector(".mode-tag")
        const currentMode = modeTag ? modeTag.textContent.replace(/[\[\]]/g, "").trim() : "adaptive"
        currentMessages.push({ role: "assistant", text: accumulatedText, timestamp: Date.now(), mode: currentMode })
        debouncedSave()
      }

      latestBotMessage = null
    }

    showSummarizeButton()
    setProcessingUI(false)
  } catch (e) {
    console.error("Vision AI stream error:", e)
    addErrorMessage("Vision AI response failed")
    if (latestBotMessage) latestBotMessage = null
    setProcessingUI(false)
  }
}

// ==============================
// STREAM AI RESPONSE — RACE MODE
// First provider to respond wins
// ==============================

async function streamAIRace(query) {
  const mode = getSelectedMode()
  const responseStyle = getSelectedResponseStyle()
  const contextMessages = getContextMessages()
  const requestStartTime = Date.now()

  // Get enabled providers - check both UI toggle (local storage) and backend API key status
  const CLOUD_PROVIDERS = ["openai", "anthropic", "google", "xai", "deepseek", "groq", "ollama-cloud", "perplexity"]
  const enabledProviders = []

  // Get which providers have API keys from backend
  let backendProviders = {}
  try {
    backendProviders = await window.api.getProviders()
  } catch (e) {
    console.warn("Could not fetch providers from backend", e)
  }

  // Fetch all provider toggles in parallel (instead of sequential await)
  const storedResults = await Promise.all(
    CLOUD_PROVIDERS.map(p => window.api.storeGet("provider_" + p))
  )
  // Fetch local key status in parallel too
  const localKeyResults = await Promise.all(
    CLOUD_PROVIDERS.map(async p => {
      try { return (await window.api.hasApiKey(p)).hasKey } catch { return false }
    })
  )
  for (let i = 0; i < CLOUD_PROVIDERS.length; i++) {
    const p = CLOUD_PROVIDERS[i]
    const stored = storedResults[i] || {}
    const hasKeyBackend = !!backendProviders[p]
    const hasKeyLocal = localKeyResults[i]
    const hasKey = hasKeyBackend || hasKeyLocal
    // Check if toggle is enabled AND provider has an API key (backend or local)
    if (stored.enabled !== false && hasKey) {
      // Check if all models for this provider are disabled
      const providerModels = (PROVIDER_META[p] || {}).models || []
      const allModelsDisabled = providerModels.length > 0 && providerModels.every(m => isModelDisabled(m.value))
      if (!allModelsDisabled) {
        enabledProviders.push(p)
      }
    }
  }
  // Always include local ollama as fallback (will be used if all clouds fail)
  enabledProviders.push("ollama")

  const BASE_URL = API_BASE
  const encodedQuery = encodeURIComponent(query || "")
  // Race mode uses minimal prompt for sub-second first-byte — always override to "race"
  const encodedMode = encodeURIComponent("race")
  const encodedStyle = encodeURIComponent(responseStyle)
  const temperature = getSelectedTemperature()
  let raceUrl = `${BASE_URL}/stream-race?q=${encodedQuery}&mode=${encodedMode}&style=${encodedStyle}&temperature=${temperature}`
  if (contextMessages && Array.isArray(contextMessages) && contextMessages.length > 0) {
    raceUrl += `&context=${encodeURIComponent(JSON.stringify(contextMessages))}`
  }
  if (enabledProviders.length > 0) {
    raceUrl += `&enabled=${encodeURIComponent(enabledProviders.join(","))}`
  }
  const controller = new AbortController()
  const timeoutId = setTimeout(() => {
    console.warn("[streamAIRace] Timeout — aborting fetch")
    controller.abort()
  }, 60000)

  // Create assistant message — use minimal racing indicator instead of loading dots
  // for instant feedback feel (sub-second first-byte optimization)
  streamMessage("assistant", "", { racingMode: true })

  // Show race progress indicator — provider badges that highlight the winner
  let raceIndicator = null
  if (latestBotMessage && latestBotMessage.element) {
    const label = latestBotMessage.element.querySelector(".msg-label")
    if (label) {
      raceIndicator = document.createElement("span")
      raceIndicator.className = "race-indicator"
      // Show badges for each enabled cloud provider (excluding ollama fallback)
      const cloudRacers = enabledProviders.filter(p => p !== "ollama")
      if (cloudRacers.length > 1) {
        raceIndicator.innerHTML = cloudRacers
          .map(p => `<span class="race-badge" data-provider="${p}">${p}</span>`)
          .join("")
        label.appendChild(raceIndicator)
      } else {
        raceIndicator = null
      }
    }
  }

  try {
    const response = await fetch(raceUrl, { signal: controller.signal })
    clearTimeout(timeoutId)

    if (!response.ok) {
      addErrorMessage("Race stream failed")
      setProcessingUI(false)
      return
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ""
    let modelName = null
    let modelProvider = null
    let modelDisplay = null
    let accumulatedText = ""

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split("\n")
      buffer = lines.pop() // Keep incomplete last line in buffer

      for (const line of lines) {
        if (line.startsWith("event:")) {
          continue
        }
        if (line.startsWith("data:")) {
          const dataStr = line.slice(5).trim()
          let data
          try {
            data = JSON.parse(dataStr)
          } catch {
            continue
          }

          if (data.type === "meta") {
            modelName = data.model || modelName
            modelProvider = data.provider || modelProvider
            modelDisplay = data.display || modelDisplay
            if (latestBotMessage) {
              latestBotMessage.modelName = modelDisplay || modelName
              latestBotMessage.modelProvider = modelProvider
              latestBotMessage.modelDisplay = modelDisplay || modelName
              renderModelBadge(latestBotMessage, latestBotMessage.modelDisplay)
            }
            // Highlight winner in race indicator
            if (raceIndicator && modelProvider) {
              raceIndicator.querySelectorAll(".race-badge").forEach(badge => {
                if (badge.dataset.provider === modelProvider) {
                  badge.classList.add("winner")
                } else {
                  badge.classList.add("loser")
                }
              })
            }
            continue
          }

          if (data.type === "chunk") {
            accumulatedText += data.content
            if (latestBotMessage) {
              latestBotMessage.accumulatedText = accumulatedText

              const displayText = accumulatedText
                .replace(/^AI:\s*/i, "")
                .replace(/\[MODEL:[^\]]*\]\s*/g, "")
                .replace(/^Paragraph\s*\d+:\s*/gim, "")
                .replace(/^Conversation history:\s*/gim, "")
                .replace(/^(You|AI)\s*:\s*/gim, "")

              // Remove loading state when we have content
              if (displayText.trim() && latestBotMessage.element) {
                latestBotMessage.element.classList.remove("loading")
                const loadingIndicator = latestBotMessage.bubble.querySelector(".loading-indicator")
                if (loadingIndicator) loadingIndicator.remove()
              }

              batchUpdateBubble(displayText)
            }
            continue
          }

          if (data.type === "done") {
            break
          }

          if (data.type === "error") {
            if (latestBotMessage) {
              setBubbleText(latestBotMessage.bubble,
                `<span class="error-text">Error: ${escapeHtml(data.message || "Unknown error")}</span>`)
            }
            latestBotMessage = null
            setProcessingUI(false)
            return
          }
        }
      }
    }

    // Final cleanup
    if (latestBotMessage) {
      let finalText = accumulatedText
        .replace(/^AI:\s*/i, "")
        .replace(/\[MODEL:[^\]]*\]\s*/g, "")
        .replace(/^Paragraph\s*\d+:\s*/gim, "")
        .replace(/^Conversation history:\s*/gim, "")
        .replace(/^(You|AI)\s*:\s*/gim, "")

      latestBotMessage.accumulatedText = finalText
      // Finalize with formatted HTML
      finalizeBubble(latestBotMessage.bubble, formatMessage(finalText))

      if (latestBotMessage.modelDisplay) {
        const label = latestBotMessage.element.querySelector(".msg-label")
        if (label) {
          let badge = label.querySelector(".model-badge")
          if (!badge) {
            badge = document.createElement("span")
            badge.className = "model-badge"
            label.appendChild(badge)
          }
          badge.classList.remove("streaming-badge")
          badge.textContent = `[${latestBotMessage.modelDisplay}]`
          // Add response time
          const elapsed = Date.now() - requestStartTime
          let timeBadge = label.querySelector(".time-badge")
          if (!timeBadge) {
            timeBadge = document.createElement("span")
            timeBadge.className = "model-badge time-badge"
            label.appendChild(timeBadge)
          }
          timeBadge.textContent = `${(elapsed / 1000).toFixed(1)}s`
        }
      }

      if (!suppressAutoSave) {
        const modeTag = document.querySelector(".mode-tag")
        const currentMode = modeTag ? modeTag.textContent.replace(/[\[\]]/g, "").trim() : "adaptive"
        currentMessages.push({ role: "assistant", text: finalText, timestamp: Date.now(), mode: currentMode })
        debouncedSave()
      }

      latestBotMessage = null
    }

    showSummarizeButton()
    setProcessingUI(false)
  } catch (e) {
    clearTimeout(timeoutId)
    console.error("Race stream error:", e)
    addErrorMessage("AI race response failed")
    if (latestBotMessage) {
      latestBotMessage = null
    }
    setProcessingUI(false)
  }
}

// ==============================
// STREAM MESSAGE (message element factory)
// ==============================
function streamMessage(role, text, opts = {}) {
  removeWelcome()

  // If streaming an assistant message, accumulate
  if (latestBotMessage && latestBotMessage.role === "assistant") {
    latestBotMessage.accumulatedText = (latestBotMessage.accumulatedText || "") + text
    const displayText = latestBotMessage.accumulatedText
      .replace(/^AI:\s*/i, "")
      .replace(/\[MODEL:[^\]]*\]\s*/g, "")

    // Remove loading class when we have actual content
    if (displayText.trim()) {
      latestBotMessage.element.classList.remove("loading")
      const loadingIndicator = latestBotMessage.bubble.querySelector(".loading-indicator")
      if (loadingIndicator) loadingIndicator.remove()
    }

    setBubbleText(latestBotMessage.bubble, displayText)
    scrollChat()
    return latestBotMessage.element
  }

  const msg = document.createElement("div")
  msg.className = "chat-message " + role

  const label = role === "user" ? "You" : "AI"
  const bubble = document.createElement("div")
  bubble.className = "msg-bubble"

  // Add loading state for empty assistant messages
  if (role === "assistant" && (!text || text === "")) {
    if (opts.racingMode) {
      // Racing mode: subtle pulse, no animated dots — instant visual feedback
      msg.classList.add("loading", "racing")
      bubble.innerHTML = '<span class="racing-indicator"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg></span>'
    } else {
      msg.classList.add("loading")
      bubble.innerHTML = '<span class="loading-indicator"><span class="dot"></span><span class="dot"></span><span class="dot"></span></span>'
    }
  } else {
    setBubbleText(bubble, text)
  }

  // Show screenshot indicator on user message
  if (role === "user" && opts.hasScreenshot) {
    const ssIndicator = document.createElement("span")
    ssIndicator.className = "screenshot-indicator"
    if (opts.screenshotB64) {
      // With preview — click to view
      ssIndicator.title = "Click to view screenshot"
      ssIndicator.dataset.fullB64 = opts.screenshotB64
      ssIndicator.addEventListener("click", () => showFullScreenshot(opts.screenshotB64))
    }
    ssIndicator.innerHTML = '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;margin-right:4px"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/><circle cx="12" cy="13" r="4"/></svg>Sent with screenshot'
    msg.appendChild(ssIndicator)
  }

  // Show speaker transcript toggle if available
  if (role === "user" && opts.speakerTranscript) {
    const speakerToggle = document.createElement("button")
    speakerToggle.className = "speaker-transcript-toggle"
    speakerToggle.innerHTML = `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;margin-right:4px"><path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="22"/></svg>${opts.speakerCount || 1} speaker${opts.speakerCount !== 1 ? 's' : ''}`
    speakerToggle.title = "Click to view transcript with speaker labels"
    speakerToggle.style.cssText = "margin-left: 8px; font-size: 0.7em; color: var(--accent); background: none; border: none; cursor: pointer;"
    speakerToggle.addEventListener("click", () => {
      showSpeakerTranscriptModal(opts.speakerTranscript)
    })
    msg.appendChild(speakerToggle)
  }

  const labelEl = document.createElement("span")
  labelEl.className = "msg-label"
  labelEl.textContent = label
  msg.appendChild(labelEl)
  msg.appendChild(bubble)

  // Add copy button for assistant messages
  if (role === "assistant") {
    const actions = document.createElement("div")
    actions.className = "msg-actions"
    const copyBtn = document.createElement("button")
    copyBtn.className = "msg-copy-btn"
    copyBtn.textContent = "Copy"
    copyBtn.addEventListener("click", () => {
      let textToCopy = bubble.dataset.fullText || bubble.innerText || text || ""
      textToCopy = textToCopy.replace(/\[.*?\]\s*$/, "").trim()
      textToCopy = textToCopy.replace(/^AI:\s*/i, "").trim()
      if (!textToCopy) {
        copyBtn.textContent = "Empty"
        setTimeout(() => { copyBtn.textContent = "Copy" }, 1000)
        return
      }
      navigator.clipboard.writeText(textToCopy).then(() => {
        copyBtn.textContent = "Copied"
        copyBtn.classList.add("copied")
        setTimeout(() => { copyBtn.textContent = "Copy"; copyBtn.classList.remove("copied") }, 1500)
      }).catch(() => {
        copyBtn.textContent = "Error"
        setTimeout(() => { copyBtn.textContent = "Copy" }, 1000)
      })
    })
    actions.appendChild(copyBtn)

    // Add Read button for TTS (browser SpeechSynthesis)
    const readBtn = document.createElement("button")
    readBtn.className = "msg-read-btn"
    readBtn.textContent = "Read"
    readBtn.addEventListener("click", () => {
      const textToSpeak = bubble.dataset.fullText || bubble.innerText || text || ""
      if (!textToSpeak.trim()) return
      if (window.speechSynthesis.paused) {
        window.speechSynthesis.resume()
        readBtn.textContent = "Pause"
        return
      }
      if (window.speechSynthesis.speaking) {
        window.speechSynthesis.cancel()
        readBtn.textContent = "Read"
        return
      }
      const utterance = new SpeechSynthesisUtterance(textToSpeak)
      utterance.rate = 1.2
      utterance.onend = () => { readBtn.textContent = "Read" }
      utterance.onerror = () => { readBtn.textContent = "Read" }
      window.speechSynthesis.speak(utterance)
      readBtn.textContent = "Pause"
    })
    actions.appendChild(readBtn)

    msg.appendChild(actions)
  }

  chatArea.appendChild(msg)
  scrollChat()

  latestBotMessage = { role, element: msg, bubble, accumulatedText: role === "assistant" ? (text || "") : undefined }

  // Track user messages
  if (!suppressAutoSave && role === "user") {
    const modeTag = document.querySelector(".mode-tag")
    const currentMode = modeTag ? modeTag.textContent.replace(/[\[\]]/g, "").trim() : "adaptive"
    currentMessages.push({ role, text, timestamp: Date.now(), mode: currentMode })
    saveCurrentConversation()
  }

  return msg
}


// ==============================
// BACKEND CONNECTION
// ==============================
async function waitForBackend() {
  const maxRetries = 20
  const healthUrl = window.api.getHealthUrl()

  for (let i = 0; i < maxRetries; i++) {
    try {
      const res = await fetch(healthUrl)
      if (res.ok) {
        isBackendReady = true
        return true
      }
    } catch {}
    await new Promise(r => setTimeout(r, 500))
  }
  return false
}

// ==============================
// SUBMIT TEXT (from text input)
// ==============================
async function submitText(text) {
  window.speechSynthesis?.cancel()
  setProcessingUI(true)

  // Combine user text with screenshot if available
  const hasScreenshot = !!pendingOcrScreenshot

  streamMessage("user", text, { hasScreenshot })

  // If we have a screenshot, send it directly to vision AI (skip OCR)
  if (pendingOcrScreenshot) {
    const visionQuery = `The user said: "${text}"\n\nAlso, I can see their screen. Help based on both the conversation and what's on screen.`
    await streamAIResponseWithImage(visionQuery, pendingOcrScreenshot)
  } else {
    const selectedModel = modelSelect ? modelSelect.value : "auto"
    if (selectedModel === "auto") {
      await streamAIRace(text)
    } else {
      await streamAIResponse(text)
    }
  }

  clearPendingOcr()
}

// ==============================
// SUBMIT AUDIO
// ==============================
async function submitAudio(blob, screenshotB64 = null) {
  window.speechSynthesis?.cancel()

  // If WebSocket streaming already produced text, use it instead of re-transcribing blob
  const streamedText = textInput.value.trim()
  if (streamedText) {
    // Partial transcript from WS — submit directly as text
    textInput.value = ""
    setProcessingUI(true)
    const effectiveScreenshot = screenshotB64 || pendingOcrScreenshot
    streamMessage("user", streamedText, { hasScreenshot: !!effectiveScreenshot, screenshotB64: effectiveScreenshot })
    if (effectiveScreenshot) {
      // Skip OCR — send screenshot directly to vision AI for faster response
      const visionQuery = `The user said: "${streamedText}"\n\nAlso, I can see their screen. Help based on both the conversation and what's on screen.`
      await streamAIResponseWithImage(visionQuery, effectiveScreenshot)
    } else {
      await streamAIResponse(streamedText)
    }
    clearPendingOcr()
    return
  }

  setProcessingUI(true)

  // Transcribe audio first
  const formData = new FormData()
  formData.append("file", blob, "audio.webm")

  let response
  let transcribeUrl = window.api.getTranscribeUrl()

  // Use speaker diarization endpoint if enabled
  if (speakerDiarizationEnabled) {
    transcribeUrl = window.api.getTranscribeWithSpeakersUrl()
  }

  // Add auth headers explicitly (belt-and-suspenders with patchedFetch)
  const transcribeHeaders = {}
  try {
    const token = localStorage.getItem('ainotetaker_auth_token')
    if (token) transcribeHeaders['Authorization'] = `Bearer ${token}`
  } catch {}

  try {
    response = await fetch(transcribeUrl, {
      method: "POST",
      headers: transcribeHeaders,
      body: formData
    })
  } catch (e) {
    addErrorMessage("Backend unavailable")
    setProcessingUI(false)
    return
  }

  if (!response.ok) {
    if (response.status === 401) {
      addErrorMessage("Session expired. Please log in again.")
      if (window.AuthHelper) { AuthHelper.clearToken(); AuthHelper.ensureAuth() }
    } else {
      addErrorMessage(`Transcription failed (${response.status})`)
    }
    setProcessingUI(false)
    return
  }

  const data = await response.json()

  if (!data.text) {
    setProcessingUI(false)
    return
  }

  // Store speaker info if available
  if (data.speakers) {
    currentSpeakers = data.speakers
  }

  // Format message with speaker info if available
  const messageOptions = { hasScreenshot: !!(screenshotB64 || pendingOcrScreenshot), screenshotB64: screenshotB64 || pendingOcrScreenshot }
  if (data.formatted_transcript && speakerDiarizationEnabled) {
    messageOptions.speakerTranscript = data.formatted_transcript
    messageOptions.speakerCount = data.speaker_count
  }

  streamMessage("user", data.text, messageOptions)

  // Skip OCR — send screenshot directly to vision AI for faster response
  const effectiveScreenshot = screenshotB64 || pendingOcrScreenshot
  if (effectiveScreenshot) {
    const visionQuery = `The user said: "${data.text}"\n\nAlso, I can see their screen. Help based on both the conversation and what's on screen.`
    await streamAIResponseWithImage(visionQuery, effectiveScreenshot)
  } else {
    await streamAIResponse(data.text)
  }
  clearPendingOcr()
}

// ==============================
// START / STOP LISTENING
// ==============================
listenBtn.addEventListener("click", async () => {
  if (isStarting) return

  // If always-on mic is active and buffer has text, flush it to AI immediately
  if (alwaysOnActive && alwaysOnTranscriptionBuffer.trim()) {
    flushAlwaysOnBuffer()
    return
  }

  // If text input has content, submit text instead of voice
  const typedText = textInput.value.trim()
  if (typedText) {
    textInput.value = ""
    await submitText(typedText)
    return
  }

  if (isListening) {
    stopListening()
    return
  }

  try {
    isStarting = true

    // Fire-and-forget backend check — if not ready, we'll show error later
    if (!isBackendReady) {
      waitForBackend().then(ok => {
        if (!ok) console.warn("[Voice] Backend became unavailable after start")
      })
    }

    setListeningUI(true)

    // Use prewarmed mic stream if available (instant), otherwise request fresh
    if (prewarmedMicStream) {
      mediaStream = prewarmedMicStream
      prewarmedMicStream = null
      // Re-warm in background for next click
      prewarmVoiceResources()
    } else {
      mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true })
    }

    mediaRecorder = new MediaRecorder(mediaStream)
    audioChunks = []

    // Setup waveform visualization (reuses prewarmed AudioContext if available)
    startWaveform(mediaStream)

    mediaRecorder.addEventListener("dataavailable", (e) => {
      if (e.data && e.data.size > 0) {
        audioChunks.push(e.data)
      }
    })

    mediaRecorder.addEventListener("stop", () => {
      const audioBlob = new Blob(audioChunks, { type: "audio/webm" })
      mediaRecorder = null
      audioChunks = []
      stopTracks()

      console.log("[mediaRecorder] stop event fired, audioBlob size:", audioBlob.size)

      if (audioBlob.size === 0) {
        setListeningUI(false)
        return
      }

      // UI already updated by stopListening() — just do background work
      // Fire screenshot fetch + submit in background so user sees instant feedback
      (async () => {
        let screenshotB64 = null
        try {
          screenshotB64 = await window.api.overlayGetLatestScreenshot()
        } catch (e) {
          console.warn("Auto-screenshot buffer read failed:", e)
        }
        await submitAudio(audioBlob, screenshotB64)
      })()
    })

    mediaRecorder.start()

    // Start real-time streaming transcription pipeline
    startStreamingTranscription()

  } catch (e) {
    console.error(e)
    addErrorMessage("Microphone unavailable")
    setListeningUI(false)
    stopTracks()
  } finally {
    isStarting = false
  }
})

function stopListening() {
  // Update UI immediately so user feels instant response
  setListeningUI(false)

  // Stop WebSocket streaming first (triggers final transcription)
  stopStreamingTranscription()

  if (mediaRecorder && mediaRecorder.state !== "inactive") {
    mediaRecorder.stop()
  }

  // Auto-generate meeting notes if session was 5+ minutes
  autoGenerateMeetingNotes()
}

// ==============================
// TRACK CLEANUP
// ==============================
function stopTracks() {
  stopWaveform()
  if (mediaStream) {
    for (const track of mediaStream.getTracks()) {
      track.stop()
    }
    mediaStream = null
  }
}

// ==============================
// PRE-WARM VOICE RESOURCES
// ==============================
function prewarmVoiceResources() {
  // Pre-request microphone permission so getUserMedia is instant on click
  if (!prewarmedMicStream) {
    navigator.mediaDevices.getUserMedia({ audio: true })
      .then(stream => {
        prewarmedMicStream = stream
        // Pre-create AudioContext for waveform so it's ready
        if (!prewarmedAudioCtx) {
          try {
            prewarmedAudioCtx = new AudioContext()
          } catch {}
        }
      })
      .catch(() => { /* mic permission denied — will show error on actual click */ })
  }
}

// ==============================
// REAL-TIME STREAMING TRANSCRIPTION
// ==============================

/**
 * Start streaming audio from the microphone to the backend via WebSocket.
 * Partial transcriptions appear in real-time in the text input.
 * If the WebSocket errors, the existing MediaRecorder blob path is used as fallback.
 */
function startStreamingTranscription() {
  partialTranscriptText = ""

  // Prevent duplicate connections
  if (transcribeWs && (transcribeWs.readyState === WebSocket.CONNECTING || transcribeWs.readyState === WebSocket.OPEN)) {
    console.log("[transcribeWs] Already connecting or open, skipping new connection")
    return
  }

  // Pass auth token in WebSocket URL so backend auth succeeds immediately
  let wsUrl = API_BASE.replace('http', 'ws') + "/ws/transcribe"
  try {
    const token = localStorage.getItem('ainotetaker_auth_token')
    if (token) wsUrl += "?token=" + encodeURIComponent(token)
  } catch {}

  transcribeWs = new WebSocket(wsUrl)
  let connectionTimeout = null

  // Set connection timeout to prevent hanging
  connectionTimeout = setTimeout(() => {
    if (transcribeWs && transcribeWs.readyState === WebSocket.CONNECTING) {
      console.warn("[transcribeWs] Connection timeout, aborting")
      transcribeWs.close()
      transcribeWs = null
    }
  }, 3000) // 3 second timeout — auth now passes instantly

  transcribeWs.addEventListener("open", () => {
    clearTimeout(connectionTimeout)
    console.log("[transcribeWs] connected")

    // Create audio pipeline: MediaStream → ScriptProcessor → Float32 PCM → WebSocket
    // Close any existing context first to prevent leaks
    if (audioCtx) {
      try { audioCtx.close() } catch {}
    }
    audioCtx = new AudioContext()
    const source = audioCtx.createMediaStreamSource(mediaStream)
    streamProcessor = audioCtx.createScriptProcessor(4096, 1, 1)

    streamProcessor.onaudioprocess = (e) => {
      if (transcribeWs?.readyState === WebSocket.OPEN) {
        const inputData = e.inputBuffer.getChannelData(0)
        // Downsample from system sample rate (e.g. 48000) to 16000 Hz
        const downsampled = downsampleBuffer(inputData, e.inputBuffer.sampleRate, 16000)
        transcribeWs.send(downsampled.buffer)
      }
    }

    source.connect(streamProcessor)
    streamProcessor.connect(audioCtx.destination)
    // Keep audioCtx alive for the duration — don't close it here
  })

  transcribeWs.addEventListener("message", (e) => {
    try {
      const data = JSON.parse(e.data)
      if (data.type === "partial") {
        partialTranscriptText = data.text
        showPartialTranscript(data.text)
        // Pass speaker info to agent suggestion pipeline if available
        if (data.speaker || data.semantic_role) {
          lastDetectedSpeaker = data.speaker || "Speaker 1"
          lastSpeakerRole = data.semantic_role || "user"
        }
        // Real-time keyword detection (Cluely-style dynamic actions)
        detectKeywords(data.text, data.speaker || lastDetectedSpeaker)
      } else if (data.type === "final") {
        confirmPartialTranscript(data.text)
        // Final message may include speaker list
        if (data.speakers && Array.isArray(data.speakers)) {
          console.log("[transcribeWs] Speakers detected:", data.speakers.join(", "))
        }
      }
    } catch {}
  })

  transcribeWs.addEventListener("error", () => {
    console.warn("[transcribeWs] error — falling back to blob recording")
    stopStreamingPipeline()
    // MediaRecorder blob path will handle it alone
  })
}

/** Stop the WebSocket and audio pipeline. */
function stopStreamingTranscription() {
  if (transcribeWs) {
    // Only close if not already closing/closed
    if (transcribeWs.readyState === WebSocket.OPEN || transcribeWs.readyState === WebSocket.CONNECTING) {
      transcribeWs.close()
    }
    transcribeWs = null
  }
  stopStreamingPipeline()
}

/** Disconnect and clean up the audio pipeline. */
let audioCtx = null  // Track AudioContext for cleanup

function stopStreamingPipeline() {
  if (streamProcessor) {
    try { streamProcessor.disconnect() } catch {}
    streamProcessor = null
  }
  // Close AudioContext to prevent memory leak
  if (audioCtx) {
    try { audioCtx.close() } catch {}
    audioCtx = null
  }
  partialTranscriptText = ""
}

/**
 * Linear interpolation downsampler.
 * @param {Float32Array} buffer - input audio buffer
 * @param {number} fromRate - source sample rate (e.g. 48000)
 * @param {number} toRate - target sample rate (e.g. 16000)
 * @returns {Float32Array} downsampled buffer
 */
function downsampleBuffer(buffer, fromRate, toRate) {
  if (fromRate === toRate) return buffer
  const ratio = fromRate / toRate
  const newLen = Math.round(buffer.length / ratio)
  const result = new Float32Array(newLen)
  for (let i = 0; i < newLen; i++) {
    const srcIdx = i * ratio
    const idx = Math.floor(srcIdx)
    const frac = srcIdx - idx
    result[i] = (buffer[idx] || 0) * (1 - frac) + (buffer[idx + 1] || 0) * frac
  }
  return result
}

/** Show interim transcription in the input field with italic green styling. */
function showPartialTranscript(text) {
  textInput.value = text
  textInput.classList.add("partial-transcript")
}

/** Confirm final transcription — remove italic styling. */
function confirmPartialTranscript(text) {
  textInput.classList.remove("partial-transcript")
  if (text) {
    textInput.value = text
    // Trigger agent suggestions with speaker info from diarizer
    processTranscriptForSuggestions(text, lastDetectedSpeaker)
  }
  partialTranscriptText = ""
}

// ==============================
// WAVEFORM VISUALIZATION
// ==============================
function startWaveform(stream) {
  try {
    // Reuse prewarmed AudioContext if available, otherwise create new
    waveformAudioCtx = prewarmedAudioCtx || new AudioContext()
    prewarmedAudioCtx = null  // consumed, will be re-warmed on next init
    waveformAnalyser = waveformAudioCtx.createAnalyser()
    waveformAnalyser.fftSize = 256
    const source = waveformAudioCtx.createMediaStreamSource(stream)
    source.connect(waveformAnalyser)

    waveformCanvasCtx = waveformCanvasEl.getContext("2d")
    waveformCanvasEl.width = waveformCanvasEl.offsetWidth || 80
    waveformCanvasEl.height = waveformCanvasEl.offsetHeight || 32
    waveformCanvasEl.classList.add("active")

    const dataArray = new Uint8Array(waveformAnalyser.frequencyBinCount)

    function draw() {
      if (!waveformAnalyser) return
      waveformAnimationId = requestAnimationFrame(draw)
      waveformAnalyser.getByteTimeDomainData(dataArray)

      waveformCanvasCtx.fillStyle = "rgba(0,0,0,0)"
      waveformCanvasCtx.fillRect(0, 0, waveformCanvasEl.width, waveformCanvasEl.height)
      waveformCanvasCtx.lineWidth = 1.5
      waveformCanvasCtx.strokeStyle = "#16a34a"
      waveformCanvasCtx.beginPath()

      const sliceWidth = waveformCanvasEl.width / dataArray.length
      let x = 0
      for (let i = 0; i < dataArray.length; i++) {
        const v = dataArray[i] / 128.0
        const y = (v * waveformCanvasEl.height) / 2
        if (i === 0) waveformCanvasCtx.moveTo(x, y)
        else waveformCanvasCtx.lineTo(x, y)
        x += sliceWidth
      }
      waveformCanvasCtx.lineTo(waveformCanvasEl.width, waveformCanvasEl.height / 2)
      waveformCanvasCtx.stroke()
    }
    draw()
  } catch (e) {
    console.warn("Waveform setup failed:", e)
  }
}

function stopWaveform() {
  if (waveformAnimationId) {
    cancelAnimationFrame(waveformAnimationId)
    waveformAnimationId = null
  }
  if (waveformCanvasCtx) {
    waveformCanvasCtx.clearRect(0, 0, waveformCanvasEl.width, waveformCanvasEl.height)
    waveformCanvasCtx = null
  }
  if (waveformAnalyser) {
    waveformAnalyser = null
  }
  if (waveformAudioCtx) {
    waveformAudioCtx.close()
    waveformAudioCtx = null
  }
  if (waveformCanvasEl) {
    waveformCanvasEl.classList.remove("active")
  }
}

// ==============================
// MODE PILLS
// ==============================
const MODE_MAP = {
  auto: "auto", fast: "fast", adaptive: "adaptive",
  universal: "universal", interview: "interview", reasoning: "reasoning",
  cloud: "cloud", code: "code"
}

document.querySelectorAll(".mode-pill").forEach(pill => {
  pill.addEventListener("click", async () => {
    const value = pill.getAttribute("data-value")
    document.querySelectorAll(".mode-pill").forEach(p => p.classList.remove("active"))
    pill.classList.add("active")
    if (modeSelect) modeSelect.value = value
    await window.api.storeSet("mode", value)
  })
})

// ==============================
// CONTROL EVENTS
// ==============================
fontSizeSelect?.addEventListener("change", async () => {
  document.documentElement.style.setProperty("--font-size", fontSizeSelect.value + "px")
  await window.api.storeSet("fontSize", fontSizeSelect.value)
})

modeSelect?.addEventListener("change", async () => {
  await window.api.storeSet("mode", modeSelect.value)
  updateProviderRecommendation(modeSelect.value)
})

contextLengthSelect?.addEventListener("change", async () => {
  await window.api.storeSet("contextLength", contextLengthSelect.value)
})

tokenLimitSelect?.addEventListener("change", async () => {
  await window.api.storeSet("tokenLimit", tokenLimitSelect.value)
})

responseStyleSelect?.addEventListener("change", async () => {
  await window.api.storeSet("responseStyle", responseStyleSelect.value)
})
temperatureSelect?.addEventListener("change", async () => {
  await window.api.storeSet("temperature", temperatureSelect.value)
})
modelSelect?.addEventListener("change", async () => {
  await window.api.storeSet("model", modelSelect.value)
  updateModelProviderBar()
})

// Cloud model select — update active provider indicator
cloudModelSelect?.addEventListener("change", async () => {
  await window.api.storeSet("cloudModel", cloudModelSelect.value)
  updateActiveProviders()
})

minBtn.addEventListener("click", () => {
  window.api.minimizeWindow()
})

maxBtn.addEventListener("click", async () => {
  const result = await window.api.toggleMaximizeWindow()
  updateMaximizeButtonIcon(result?.isMaximized)
})

// Update maximize button icon based on state
function updateMaximizeButtonIcon(isMaximized) {
  if (!maxBtn) return
  maxBtn.innerHTML = isMaximized
    ? '<span class="traffic-icon">&#9634;</span>'
    : '<span class="traffic-icon">&#9633;</span>'
  maxBtn.title = isMaximized ? "Restore" : "Maximize"
}

// Listen for maximize state changes from main process
if (window.api.onMaximizeChanged) {
  window.api.onMaximizeChanged((state) => {
    updateMaximizeButtonIcon(state?.isMaximized)
  })
}

closeBtn.addEventListener("click", () => {
  window.api.closeWindow()
})

// ==============================
// SUMMARIZE BUTTON
// ==============================
function showSummarizeButton() {
  if (summarizeBtn && currentMessages.length >= 2) {
    summarizeBtn.classList.add("visible")
  }
}

function hideSummarizeButton() {
  if (summarizeBtn) summarizeBtn.classList.remove("visible")
}

summarizeBtn?.addEventListener("click", async () => {
  if (!currentMessages || currentMessages.length < 2) return
  summarizeBtn.classList.add("loading")
  summarizeBtn.querySelector(".summarize-btn-label").textContent = "Summarizing..."

  // Remove existing summary if present
  const existing = document.querySelector(".summary-block")
  if (existing) existing.remove()

  try {
    // Build transcript text
    const transcript = currentMessages.map(m => {
      const role = m.role === "user" ? "You" : "AI"
      return `${role}: ${m.text}`
    }).join("\n\n")

    // Call the AI summary endpoint with proper SSE parsing
    const selectedModel = modelSelect ? modelSelect.value : "auto"
    const isCloudModel = selectedModel && selectedModel !== "auto" && selectedModel.includes("-") && !selectedModel.includes(":")
    const isLocalModel = selectedModel && selectedModel !== "auto" && selectedModel.includes(":")
    const provider = isCloudModel ? selectedModel : (isLocalModel ? selectedModel : "ollama")

    const healthUrl = window.api.getHealthUrl()
    const base = healthUrl.replace("/health", "")
    const params = new URLSearchParams({
      q: transcript,
      mode: "summary",
      style: "detailed",
      provider
    })
    const url = `${base}/stream?${params.toString()}`

    const response = await fetch(url)
    if (!response.ok) throw new Error("Summary failed")

    // Create summary block BEFORE streaming so we can append to it
    const summaryBlock = document.createElement("div")
    summaryBlock.className = "summary-block"
    summaryBlock.innerHTML = `<div class="summary-block-title">&#10022; Meeting Notes</div><div class="summary-block-content" id="summaryContent"></div>`
    chatArea.appendChild(summaryBlock)
    scrollChat()

    const summaryContent = document.getElementById("summaryContent")

    // Stream with proper SSE parsing (same approach as streamAIResponse)
    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ""
    let accumulated = ""

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split("\n")
      buffer = lines.pop() // Keep unparsed tail for next iteration

      for (const line of lines) {
        if (line.startsWith("data:")) {
          const dataStr = line.slice(5).trim()
          if (!dataStr) continue
          try {
            const data = JSON.parse(dataStr)
            if (data.type === "chunk" && data.content) {
              accumulated += data.content
            }
          } catch {}
        }
      }

      // Render accumulated text using the existing formatMessage renderer
      requestAnimationFrame(() => {
        summaryContent.innerHTML = formatMessage(accumulated)
        scrollChat()
      })

    }

    // Final render with full formatting
    summaryContent.innerHTML = formatMessage(accumulated)

    // Add copy button to summary block
    const copyBtn = document.createElement("button")
    copyBtn.className = "summary-copy-btn"
    copyBtn.textContent = "Copy"
    copyBtn.title = "Copy meeting notes"
    copyBtn.addEventListener("click", () => {
      window.api.copyToClipboard(accumulated)
      copyBtn.textContent = "Copied!"
      setTimeout(() => { copyBtn.textContent = "Copy" }, 1500)
    })
    summaryBlock.querySelector(".summary-block-title").appendChild(copyBtn)

    // Add follow-up email button
    const emailBtn = document.createElement("button")
    emailBtn.className = "summary-copy-btn followup-email-btn"
    emailBtn.textContent = "Follow-up Email"
    emailBtn.title = "Generate and copy a follow-up email"
    emailBtn.addEventListener("click", async () => {
      emailBtn.textContent = "Generating..."
      const email = await generateFollowUpEmail()
      if (email) {
        emailBtn.textContent = "Email Copied!"
        setTimeout(() => { emailBtn.textContent = "Follow-up Email" }, 2000)
      } else {
        emailBtn.textContent = "Failed"
        setTimeout(() => { emailBtn.textContent = "Follow-up Email" }, 2000)
      }
    })
    summaryBlock.querySelector(".summary-block-title").appendChild(emailBtn)

    scrollChat()
  } catch (e) {
    console.error("Summary error:", e)
    // Fallback: show a simple text summary
    const summaryBlock = document.createElement("div")
    summaryBlock.className = "summary-block"
    const date = new Date().toLocaleDateString()
    const first = currentMessages.find(m => m.role === "user")
    const last = currentMessages.slice(-1)[0]
    summaryBlock.innerHTML = `<div class="summary-block-title">&#10022; Summary</div><div class="summary-block-content"><p><strong>Topic:</strong> ${escapeHtml(first?.text?.substring(0, 80) || "Conversation")}</p><p><strong>Date:</strong> ${date}</p><p><strong>Exchanged:</strong> ${currentMessages.length} messages</p><p><strong>Last response:</strong> ${escapeHtml(last?.text?.substring(0, 120) || "")}...</p></div>`
    chatArea.appendChild(summaryBlock)
    scrollChat()
  } finally {
    summarizeBtn.classList.remove("loading")
    summarizeBtn.querySelector(".summarize-btn-label").textContent = "Summarize"
  }
})

// ==============================
// AUTO MEETING NOTES + FOLLOW-UP EMAIL
// ==============================
const MEETING_NOTES_MIN_DURATION = 5 * 60 * 1000 // 5 minutes in ms

function autoGenerateMeetingNotes() {
  // Only auto-generate if session was long enough and we have enough messages
  if (!sessionStartTime) return
  const sessionDuration = Date.now() - sessionStartTime
  if (sessionDuration < MEETING_NOTES_MIN_DURATION) return
  if (!currentMessages || currentMessages.length < 2) return

  // Don't auto-trigger if a summary block already exists
  if (document.querySelector(".summary-block")) return

  // Auto-click the summarize button after a short delay
  setTimeout(() => {
    if (summarizeBtn && !summarizeBtn.classList.contains("loading")) {
      summarizeBtn.click()
    }
  }, 1000)
}

async function generateFollowUpEmail() {
  const summaryBlock = document.querySelector(".summary-block")
  if (!summaryBlock) return

  const summaryContent = summaryBlock.querySelector(".summary-block-content")
  if (!summaryContent) return

  const summaryText = summaryContent.textContent || summaryContent.innerText

  // Build conversation transcript for context
  const transcript = currentMessages.map(m => {
    const role = m.role === "user" ? "You" : "AI"
    return `${role}: ${m.text}`
  }).join("\n\n")

  const query = `Meeting summary:\n${summaryText}\n\nConversation context:\n${transcript.substring(0, 2000)}`

  // Use the AI with follow-up email mode
  const healthUrl = window.api.getHealthUrl()
  const base = healthUrl.replace("/health", "")
  const params = new URLSearchParams({
    q: query,
    mode: "followup",
    style: "detailed",
    provider: "ollama"
  })
  const url = `${base}/stream?${params.toString()}`

  try {
    const response = await fetch(url)
    if (!response.ok) throw new Error("Failed to generate follow-up email")

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ""
    let accumulated = ""

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split("\n")
      buffer = lines.pop()
      for (const line of lines) {
        if (line.startsWith("data:")) {
          const dataStr = line.slice(5).trim()
          if (!dataStr) continue
          try {
            const data = JSON.parse(dataStr)
            if (data.type === "chunk" && data.content) {
              accumulated += data.content
            }
          } catch {}
        }
      }
    }

    // Copy to clipboard
    if (accumulated.trim()) {
      await window.api.copyToClipboard(accumulated)
      return accumulated
    }
  } catch (e) {
    console.error("Follow-up email error:", e)
  }
  return null
}

// ==============================
// HISTORY PANEL
// ==============================
function toggleHistoryPanel() {
  const wasOpen = historyPanel.classList.contains("open")
  historyPanel.classList.toggle("open")
  updatePanelBackdrop()

  const historyList = document.getElementById("historyList")

  if (historyPanel.classList.contains("open")) {
    // Opening - close other panels first, then render
    closeProviderConfig()
    settingsPanel.classList.remove("open")
    appMenu.classList.remove("open")
    renderHistoryList()
    // Force reflow and scroll to top
    if (historyList) {
      historyList.style.display = "none"
      void historyList.offsetHeight
      historyList.style.display = ""
      historyList.scrollTop = 0
    }
  } else if (historyList) {
    // Closing - reset scroll
    historyList.scrollTop = 0
  }
}

// Back button — close history panel
const historyBackBtn = document.getElementById("historyBackBtn")
if (historyBackBtn) {
  historyBackBtn.addEventListener("click", () => {
    closeHistoryPanel()
  })
}

// Search input — live filter
const historySearchInput = document.getElementById("historySearch")
if (historySearchInput) {
  historySearchInput.addEventListener("input", () => {
    renderHistoryList()
  })
}

// Sort select
const historySortSelect = document.getElementById("historySort")
if (historySortSelect) {
  historySortSelect.addEventListener("change", () => {
    historySortBy = historySortSelect.value
    renderHistoryList()
  })
}

newChatBtn.addEventListener("click", () => {
  startNewConversation()
})

// Close history panel when clicking outside
document.addEventListener("click", (e) => {
  if (
    historyPanel?.classList.contains("open") &&
    !historyPanel?.contains(e.target) &&
    !historyBtn?.contains(e.target)
  ) {
    closeHistoryPanel()
  }
})

// ==============================
// STEALTH TOGGLE
// ==============================
async function syncStealthState() {
  try {
    const result = await window.api.storeGet("stealthState")
    if (result !== undefined) {
      isUndetectable = result
    }
  } catch {}
}

function updateStealthUI(enabled, undetectable) {
  isUndetectable = undetectable
  if (stealthBtn) stealthBtn.classList.toggle("undetectable", undetectable)
  if (stealthLabel) stealthLabel.textContent = undetectable ? "Undetectable" : "Detectable"
}

if (stealthBtn) stealthBtn.addEventListener("click", async () => {
  const newState = !isUndetectable
  updateStealthUI(newState, newState)
  try {
    // Toggle stealth mode (tray + capture protection together)
    await window.api.setStealthMode(newState)
    // Sync state from main process response
    await window.api.storeSet("stealthState", newState)
  } catch (e) {
    console.error(e)
  }
})

// Smart mode — code/coding assistance toggle
let smartModeActive = false
smartModeBtn?.addEventListener("click", async () => {
  smartModeActive = !smartModeActive
  smartModeBtn.classList.toggle("active", smartModeActive)
  if (smartModeActive) {
    // Switch to code mode
    if (modeSelect) modeSelect.value = "code"
    await window.api.storeSet("mode", "code")
  } else {
    // Restore previous mode from store
    const saved = await window.api.storeGet("mode")
    if (modeSelect) modeSelect.value = saved || "adaptive"
  }
})

// Auto-screenshot toggle
if (autoSSBtn) {
  autoSSBtn.addEventListener("click", async () => {
    const isActive = autoSSBtn.classList.contains("active")
    const newState = !isActive
    try {
      await window.api.autoScreenshotSetEnabled(newState, 5000)
      autoSSBtn.classList.toggle("active", newState)
      if (autoSSDot) autoSSDot.style.display = newState ? "block" : "none"
    } catch (e) {
      console.error("autoScreenshotSetEnabled failed:", e)
    }
  })
  // Restore state on load
  ;(async () => {
    try {
      const status = await window.api.autoScreenshotGetStatus()
      if (status && status.enabled) {
        autoSSBtn.classList.add("active")
        if (autoSSDot) autoSSDot.style.display = "block"
      }
    } catch {}
  })()
}

// ==============================
// SCREENSHOT CAPTURE + OCR
// ==============================
// Capture a screenshot, OCR it, and show a preview badge.
// The extracted text is combined with user input when sending to AI.

async function runOcr(screenshotB64) {
  try {
    const resp = await fetch(window.api.getOcrUrl(), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ image_b64: screenshotB64 })
    })
    if (resp.ok) {
      return await resp.json()
    }
  } catch (e) {
    console.warn("[OCR] Failed:", e)
  }
  return { text: "", method: "none" }
}

function clearPendingOcr() {
  pendingOcrText = null
  pendingOcrScreenshot = null
  if (ocrBadge) ocrBadge.style.display = "none"
}

if (captureBtn) {
  captureBtn.addEventListener("click", async () => {
    if (captureBtn.classList.contains("processing")) return
    captureBtn.classList.add("processing")

    try {
      // 1. Capture fresh screenshot via Electron IPC
      const screenshot = await window.api.captureScreenshot()
      if (!screenshot) {
        captureBtn.classList.remove("processing")
        return
      }

      // 2. Send to /ocr endpoint
      const ocrResult = await runOcr(screenshot)

      // 3. Store results
      pendingOcrScreenshot = screenshot
      pendingOcrText = (ocrResult.text || "").trim()

      // 4. Show badge
      if (ocrBadge && ocrBadgeText) {
        if (pendingOcrText) {
          const preview = pendingOcrText.length > 80
            ? pendingOcrText.substring(0, 80) + "..."
            : pendingOcrText
          ocrBadgeText.textContent = preview
        } else {
          ocrBadgeText.textContent = "Screenshot captured (no text detected)"
        }
        ocrBadge.style.display = "flex"
      }
    } catch (e) {
      console.error("[Capture+OCR] Error:", e)
      // Fallback: store screenshot for vision model path
      try {
        pendingOcrScreenshot = await window.api.captureScreenshot()
        pendingOcrText = null
        if (ocrBadge && ocrBadgeText) {
          ocrBadgeText.textContent = "Screenshot captured"
          ocrBadge.style.display = "flex"
        }
      } catch {}
    }

    captureBtn.classList.remove("processing")
  })
}

if (ocrBadgeRemove) {
  ocrBadgeRemove.addEventListener("click", () => {
    clearPendingOcr()
  })
}

// Build combined query from user text + pending OCR
function buildCombinedQuery(userText) {
  if (pendingOcrText) {
    return `Screen context: ${pendingOcrText}\n\nUser said: ${userText}\n\nAnswer based on both the screen content and what the user said.`
  }
  return userText
}

// ==============================
// ALWAYS-ON MIC — auto listen + transcribe + auto-query AI
// ==============================
function startAlwaysOnListen() {
  if (alwaysOnEventSource) return
  alwaysOnTranscriptionBuffer = ""
  alwaysOnLastHeardTime = Date.now()

  alwaysOnEventSource = new EventSource(`${API_BASE}/transcribe-stream`)

  alwaysOnEventSource.addEventListener("transcript", (e) => {
    try {
      const data = JSON.parse(e.data)
      if (data.text && data.text.trim()) {
        alwaysOnTranscriptionBuffer += " " + data.text.trim()
        alwaysOnLastHeardTime = Date.now()
      }
    } catch {}
  })

  alwaysOnEventSource.addEventListener("ping", () => {
    // Check if silence threshold exceeded
    const elapsed = Date.now() - alwaysOnLastHeardTime
    if (alwaysOnTranscriptionBuffer.trim().length > 0 && elapsed > ALWAYS_ON_SILENCE_THRESHOLD) {
      const text = alwaysOnTranscriptionBuffer.trim()
      alwaysOnTranscriptionBuffer = ""
      // Auto-send to AI with latest screenshot
      autoSendToAI(text)
    }
  })

  alwaysOnEventSource.onerror = () => {
    stopAlwaysOnListen()
  }
}

function stopAlwaysOnListen() {
  if (alwaysOnEventSource) {
    alwaysOnEventSource.close()
    alwaysOnEventSource = null
  }
  alwaysOnTranscriptionBuffer = ""

  // Auto-generate meeting notes if session was 5+ minutes
  autoGenerateMeetingNotes()
}

function flushAlwaysOnBuffer() {
  if (!alwaysOnTranscriptionBuffer.trim()) return
  const text = alwaysOnTranscriptionBuffer.trim()
  alwaysOnTranscriptionBuffer = ""
  alwaysOnLastHeardTime = 0  // reset silence timer
  autoSendToAI(text)
}

async function autoSendToAI(text) {
  if (!text || !text.trim()) return
  if (isProcessing) return  // skip if AI is busy

  try {
    // Always grab latest screenshot from auto-screenshot ring buffer (like Cluely)
    let screenshotB64 = null
    try {
      screenshotB64 = await window.api.overlayGetLatestScreenshot()
    } catch {}

    // Also check for manually captured screenshot
    const effectiveScreenshot = screenshotB64 || pendingOcrScreenshot
    streamMessage("user", text, { hasScreenshot: !!effectiveScreenshot, screenshotB64: effectiveScreenshot })

    if (effectiveScreenshot) {
      try {
        const ocrResult = await runOcr(effectiveScreenshot)
        if (ocrResult.text && ocrResult.text.trim()) {
          const combinedQuery = `Screen context: ${ocrResult.text.trim()}\n\nUser said: ${text}\n\nAnswer based on both the screen content and what the user said.`
          // Route through race mode when auto-selected
          const selectedModel = modelSelect ? modelSelect.value : "auto"
          if (selectedModel === "auto") {
            await streamAIRace(combinedQuery)
          } else {
            await streamAIResponse(combinedQuery)
          }
        } else {
          // OCR found no text — just send voice without screen context
          await streamAIResponse(text)
        }
      } catch {
        await streamAIResponse(text)
      }
    } else {
      await streamAIResponse(text)
    }
    clearPendingOcr()
  } catch (e) {
    console.error("autoSendToAI error:", e)
  }
}

// Always-on mic toggle
if (alwaysOnBtn) {
  alwaysOnBtn.addEventListener("click", async () => {
    const isActive = alwaysOnBtn.classList.contains("active")
    const newState = !isActive
    try {
      const resp = await fetch(`${API_BASE}/set-always-on-mic`, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: `enabled=${newState}`
      })
      if (resp.ok) {
        alwaysOnBtn.classList.toggle("active", newState)
        if (alwaysOnDot) alwaysOnDot.style.display = newState ? "block" : "none"
        alwaysOnActive = newState
        if (newState) {
          startAlwaysOnListen()
        } else {
          stopAlwaysOnListen()
        }
      }
    } catch (e) {
      console.error("set-always-on-mic failed:", e)
    }
  })
}

// ==============================
// RESIZE HANDLE
// ==============================
const resizeHandle = document.querySelector(".resize-handle")
if (resizeHandle) {
  let isResizing = false
  let startY = 0
  let startHeight = 0

  resizeHandle.addEventListener("mousedown", (e) => {
    isResizing = true
    startY = e.screenY
    const shell = document.querySelector(".shell")
    startHeight = shell.offsetHeight
    document.body.style.cursor = "s-resize"
    e.preventDefault()
  })

  document.addEventListener("mousemove", (e) => {
    if (!isResizing) return
    const delta = e.screenY - startY
    const newHeight = Math.max(280, startHeight + delta)
    window.api.resizeWindow(null, newHeight)
  })

  document.addEventListener("mouseup", () => {
    if (isResizing) {
      isResizing = false
      document.body.style.cursor = ""
    }
  })
}

// ==============================
// RESPONSIVE WINDOW HANDLING
// ==============================
function updateResponsiveLayout() {
  const width = window.innerWidth
  const body = document.body

  // Remove all responsive classes
  body.classList.remove("window-xs", "window-sm", "window-md", "window-lg")

  // Add appropriate class based on window size
  if (width <= 480) {
    body.classList.add("window-xs")
  } else if (width <= 680) {
    body.classList.add("window-sm")
  } else if (width <= 800) {
    body.classList.add("window-md")
  } else {
    body.classList.add("window-lg")
  }
}

// Initial call
updateResponsiveLayout()

// Debounced resize handler
let resizeTimeout
window.addEventListener("resize", () => {
  clearTimeout(resizeTimeout)
  resizeTimeout = setTimeout(updateResponsiveLayout, 100)
})

// ==============================
// MENU BUTTON + APP MENU
// ==============================
const appMenu = document.getElementById("appMenu")
const shortcutsModal = document.getElementById("shortcutsModal")
const aboutModal = document.getElementById("aboutModal")
const closeShortcutsBtn = document.getElementById("closeShortcutsModal")
const closeAboutBtn = document.getElementById("closeAboutModal")

// Adjust menu position to keep it within window bounds
function adjustMenuPosition() {
  if (!appMenu.classList.contains("open")) return

  const menuRect = appMenu.getBoundingClientRect()
  const windowWidth = window.innerWidth
  const windowHeight = window.innerHeight

  // Check if menu extends beyond right edge
  if (menuRect.right > windowWidth - 10) {
    appMenu.style.right = '10px'
    appMenu.style.left = 'auto'
  }

  // Check if menu extends beyond bottom edge
  if (menuRect.bottom > windowHeight - 10) {
    const newTop = Math.max(10, windowHeight - menuRect.height - 10)
    appMenu.style.top = newTop + 'px'
    appMenu.style.maxHeight = (windowHeight - newTop - 10) + 'px'
  } else {
    appMenu.style.top = '48px'
    appMenu.style.maxHeight = ''
  }
}

// Handle window resize
window.addEventListener('resize', () => {
  adjustMenuPosition()
})

menuBtn.addEventListener("click", (e) => {
  e.stopPropagation()
  closeHistoryPanel() // Close history if open

  // Reset menu styles before opening
  appMenu.style.top = '48px'
  appMenu.style.right = '80px'
  appMenu.style.left = 'auto'
  appMenu.style.maxHeight = ''

  appMenu.classList.toggle("open")
  shortcutsModal.classList.remove("open")
  aboutModal.classList.remove("open")

  // Adjust position after opening
  if (appMenu.classList.contains("open")) {
    setTimeout(adjustMenuPosition, 0)
  }
})

function openSettings() {
  closeHistoryPanel()
  settingsPanel?.classList.add("open")
  updatePanelBackdrop()
}

// Close menu when clicking outside
document.addEventListener("click", (e) => {
  if (appMenu?.classList.contains("open") && !appMenu?.contains(e.target) && !menuBtn?.contains(e.target)) {
    appMenu.classList.remove("open")
  }
})

// Handle menu item clicks
appMenu.addEventListener("click", async (e) => {
  const item = e.target.closest(".app-menu-item")
  if (!item) return
  e.stopPropagation() // Prevent document click from closing menu
  appMenu.classList.remove("open")

  const action = item.getAttribute("data-action")

  if (action === "settings") {
    openSettings()
    // Reset to General tab
    settingsTabs.forEach(t => t.classList.remove('active'))
    settingsTabContents.forEach(c => c.classList.remove('active'))
    document.querySelector('.settings-tab[data-tab="general"]').classList.add('active')
    document.querySelector('.settings-tab-content[data-content="general"]').classList.add('active')

    try {
      const providers = await window.api.getProviders()
      // Merge backend key status with local store to avoid stale cache disabling a freshly-saved provider
      const mergeProvider = async (name) => {
        const hasKeyBackend = !!providers[name]
        let hasKeyLocal = false
        try { hasKeyLocal = (await window.api.hasApiKey(name)).hasKey } catch {}
        let stored = {}
        try { stored = (await window.api.storeGet("provider_" + name)) || {} } catch {}
        const hasKey = hasKeyBackend || hasKeyLocal
        if (hasKey) {
          const isEnabled = stored.enabled !== false
          syncProviderRow(name, isEnabled)
          return
        }
        const isEnabled = stored.enabled !== false && !!stored.apiKey
        syncProviderRow(name, isEnabled)
      }
      await mergeProvider("openai")
      await mergeProvider("anthropic")
      await mergeProvider("google")
      await mergeProvider("xai")
      await mergeProvider("deepseek")
      await mergeProvider("groq")
      await mergeProvider("ollama-cloud")
      await mergeProvider("perplexity")
    } catch (e) { console.error(e) }
    const savedCloudModel = await window.api.storeGet("cloudModel")
    if (savedCloudModel && cloudModelSelect) {
      cloudModelSelect.value = savedCloudModel
      // Update custom dropdown — check both standard items and custom model entries
      const selectedItem = cloudModelMenu?.querySelector(`.custom-dropdown-item[data-value="${savedCloudModel}"]`)
        || cloudModelMenu?.querySelector(`.custom-model-entry[data-value="${savedCloudModel}"]`)
      if (selectedItem && cloudModelText) {
        cloudModelText.textContent = selectedItem.textContent
        cloudModelMenu.querySelectorAll(".custom-dropdown-item, .custom-model-entry").forEach(i => i.classList.remove("selected"))
        selectedItem.classList.add("selected")
      }
    }
    updateActiveProviders()
  }
  else if (action === "shortcuts") {
    shortcutsModal.classList.add("open")
  }
  else if (action === "about") {
    aboutModal.classList.add("open")
    loadAboutStatus()
  }
  else if (action === "cognitive-graph") {
    window.location.href = 'cognitive-graph.html'
  }
  else if (action === "pre-interview") {
    window.location.href = 'pre-interview.html'
  }
  else if (action === "analytics") {
    window.location.href = 'analytics-dashboard.html'
  }
  else if (action === "logs") {
    window.api.openLogs()
  }
  else if (action === "quit") {
    window.api.closeWindow()
  }
  else if (action === "signout") {
    if (window.AuthHelper) {
      AuthHelper.clearToken()
      showToast("Signed out")
      setTimeout(() => { AuthHelper.showLoginOverlay() }, 400)
    }
  }
  else if (action === "new-chat") {
    startNewConversation()
    showToast("New conversation started")
  }
  else if (action === "history") {
    toggleHistoryPanel()
  }
  else if (action === "export") {
    exportCurrentConversation = currentMessages.length > 0 ? currentMessages : null
    if (exportModal) exportModal.classList.add("open")
  }
  else if (action === "study-plan") {
    window.location.href = 'study-plan.html'
  }
  else if (action === "interview-simulator") {
    window.location.href = 'interview-simulator.html'
  }
  else if (action === "job-tracker") {
    window.location.href = 'job-tracker.html'
  }
  else if (action === "resume-review") {
    window.location.href = 'resume-review.html'
  }
})

// Shortcuts modal
closeShortcutsBtn.addEventListener("click", () => {
  shortcutsModal.classList.remove("open")
})
shortcutsModal.addEventListener("click", (e) => {
  if (e.target === shortcutsModal) shortcutsModal.classList.remove("open")
})

// About modal
closeAboutBtn.addEventListener("click", () => {
  aboutModal.classList.remove("open")
})
aboutModal.addEventListener("click", (e) => {
  if (e.target === aboutModal) aboutModal.classList.remove("open")
})

// Load backend status into About modal
async function loadAboutStatus() {
  const setStatus = (id, ok, text) => {
    const el = document.getElementById(id)
    if (!el) return
    el.textContent = text
    el.className = "about-status-value " + (ok ? "ok" : "fail")
  }

  setStatus("aboutBackend", true, "Running")
  setStatus("aboutOllama", false, "Checking...")
  setStatus("aboutWhisper", false, "Checking...")

  // Check Ollama (local only — not available on cloud)
  var _ollamaUrl = (typeof API_BASE !== 'undefined' && API_BASE.indexOf('127.0.0.1') !== -1) ? 'http://127.0.0.1:11434/api/tags' : null;
  if (_ollamaUrl) {
  try {
    const res = await fetch(_ollamaUrl, { method: "GET", signal: AbortSignal.timeout(3000) })
    if (res.ok) {
      const data = await res.json()
      const count = data.models ? data.models.length : 0
      setStatus("aboutOllama", true, `Connected (${count} models)`)
    } else {
      setStatus("aboutOllama", false, "Connection failed")
    }
  } catch {
    setStatus("aboutOllama", false, "Not reachable")
  }

  // Whisper model is loaded on first use — we can't query it directly
  // Check if backend has processed at least one transcription
  setStatus("aboutWhisper", true, "Ready")
}

// ==============================
// SETTINGS PANEL
// ==============================
let activeProvider = null

// DOM refs for config panel
const providerConfigPanel = document.getElementById("providerConfigPanel")
const settingsProvidersView = document.getElementById("settingsProvidersView")
const configProviderName = document.getElementById("configProviderName")
const configProviderIcon = document.getElementById("configProviderIcon")
const configApiKeyInput = document.getElementById("configApiKeyInput")
const configSaveBtn = document.getElementById("configSaveBtn")
const configTestResult = document.getElementById("configTestResult")
const configSyncEnvCheckbox = document.getElementById("configSyncEnvCheckbox")
const configEnvWarning = document.getElementById("configEnvWarning")
const configRestartHint = document.getElementById("configRestartHint")
const configRestartBackendBtn = document.getElementById("configRestartBackendBtn")
// ==============================
// SETTINGS TABS
// ==============================
const settingsTabs = document.querySelectorAll('.settings-tab')
const settingsTabContents = document.querySelectorAll('.settings-tab-content')

settingsTabs.forEach(tab => {
  tab.addEventListener('click', async () => {
    const targetTab = tab.dataset.tab

    // Deactivate all tabs
    settingsTabs.forEach(t => t.classList.remove('active'))
    settingsTabContents.forEach(c => c.classList.remove('active'))

    // Activate clicked tab
    tab.classList.add('active')
    document.querySelector(`.settings-tab-content[data-content="${targetTab}"]`).classList.add('active')

    // Refresh Model Manager when opening Models tab
    if (targetTab === "models" && typeof renderRaceToggles === "function") {
      await renderRaceToggles()
    }
  })
})

// ==============================
// MODULE HEALTH
// ==============================
const MODULE_HEALTH_NAMES = {
  database: "Database",
  neo4j_graph: "Knowledge Graph (Neo4j)",
  whisper: "Whisper Transcription",
  voice_clone: "Voice Clone",
  ai_router: "AI Router",
  collaboration: "Collaboration",
  mock_interview: "Mock Interview",
  study_plan: "Study Plans",
  interview_simulator: "Interview Simulator",
  job_tracker: "Job Tracker",
  encryption: "Encryption"
}

async function refreshModuleHealth() {
  const grid = document.getElementById("moduleHealthGrid")
  if (!grid) return

  try {
    const response = await fetch(`${API_BASE}/health/modules`)
    if (!response.ok) throw new Error("Failed to fetch")

    const data = await response.json()
    const modules = data.modules || {}

    // Update overall health badge if it exists
    const healthBadge = document.getElementById("moduleHealthBadge")
    if (healthBadge) {
      healthBadge.textContent = `${data.overall_health || 0}%`
      healthBadge.className = `health-badge ${data.overall_health >= 75 ? 'healthy' : data.overall_health >= 50 ? 'partial' : 'unhealthy'}`
    }

    // Update summary text
    const healthSummary = document.getElementById("moduleHealthSummary")
    if (healthSummary) {
      healthSummary.textContent = `${data.available_count || 0}/${data.total_count || 0} modules active`
    }

    grid.innerHTML = ""

    for (const [key, moduleData] of Object.entries(modules)) {
      const label = MODULE_HEALTH_NAMES[key] || key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
      const status = moduleData.status || 'unknown'
      const isAvailable = status === 'green'

      // Build status detail
      let detail = ''
      if (key === 'ai_router' && moduleData.active_providers !== undefined) {
        detail = ` (${moduleData.active_providers} providers)`
      } else if (key === 'mock_interview' && moduleData.question_count !== undefined) {
        detail = ` (${moduleData.question_count} questions)`
      } else if (key === 'voice_clone' && moduleData.rvc_available) {
        detail = ' (RVC available)'
      } else if (key === 'database' && moduleData.type) {
        detail = ` (${moduleData.type})`
      }

      // Build config hint if not green
      let configHint = ''
      if (status !== 'green' && moduleData.required_dependency) {
        configHint = `<span class="module-hint">→ ${moduleData.required_dependency}</span>`
      }

      const item = document.createElement("div")
      item.className = `module-item ${status}`
      item.innerHTML = `
        <span class="module-status-dot ${status}"></span>
        <span class="module-name" title="${label}">${label}${detail}</span>
        ${configHint}
      `
      grid.appendChild(item)
    }
  } catch (e) {
    console.warn('[Health] Failed to fetch module health:', e)
    // Backend not available - show all unknown
    grid.innerHTML = ""
    for (const [key, label] of Object.entries(MODULE_HEALTH_NAMES)) {
      const item = document.createElement("div")
      item.className = "module-item unknown"
      item.innerHTML = `
        <span class="module-status-dot unknown"></span>
        <span class="module-name" title="${label}">${label}</span>
      `
      grid.appendChild(item)
    }
  }
}

// Refresh module health when settings panel opens — debounced to avoid transitionend spam
let _lastHealthFetch = 0
const _HEALTH_FETCH_MIN_INTERVAL = 5000  // 5 seconds
function _throttledRefreshHealth() {
  const now = Date.now()
  if (now - _lastHealthFetch < _HEALTH_FETCH_MIN_INTERVAL) return
  _lastHealthFetch = now
  refreshModuleHealth()
}
document.getElementById("settingsPanel")?.addEventListener("transitionend", (e) => {
  // Only fire for the panel itself, not child elements (transitionend bubbles)
  if (e.target !== document.getElementById("settingsPanel")) return
  const panel = document.getElementById("settingsPanel")
  if (panel?.classList.contains("open")) {
    _throttledRefreshHealth()
  }
})

// Also refresh when general tab is clicked
document.querySelectorAll('.settings-tab').forEach(tab => {
  tab.addEventListener('click', () => {
    if (tab.dataset.tab === 'general') {
      _throttledRefreshHealth()
    }
  })
})

// ==============================
// COLLAPSIBLE CARDS
// ==============================
document.querySelectorAll('.settings-card-header[data-collapsible]').forEach(header => {
  header.addEventListener('click', () => {
    const targetId = header.dataset.collapsible
    const body = document.getElementById(targetId)
    const arrow = header.querySelector('.settings-card-arrow')

    if (body) {
      body.classList.toggle('collapsed')
      header.classList.toggle('collapsed')
    }
  })
})

// Provider metadata — full model catalog
const PROVIDER_META = {
  openai: {
    name: "OpenAI",
    models: [
      { value: "openai-gpt-4o-mini", label: "GPT-4o Mini" },
      { value: "openai-gpt-4o", label: "GPT-4o" },
      { value: "openai-gpt-4-turbo", label: "GPT-4 Turbo" },
      { value: "openai-o1-mini", label: "o1 Mini (Reasoning)" },
      { value: "openai-o3-mini", label: "o3 Mini (Reasoning)" },
      { value: "openai-gpt-3.5-turbo", label: "GPT-3.5 Turbo" },
    ]
  },
  anthropic: {
    name: "Anthropic",
    models: [
      { value: "anthropic-claude-3-5-haiku", label: "Claude 3.5 Haiku" },
      { value: "anthropic-claude-3-5-sonnet", label: "Claude 3.5 Sonnet" },
      { value: "anthropic-claude-sonnet-4-20250514", label: "Claude Sonnet 4" },
      { value: "anthropic-claude-opus-4-20250514", label: "Claude Opus 4" },
    ]
  },
  google: {
    name: "Google",
    models: [
      { value: "google-gemini-2-0-flash", label: "Gemini 2.0 Flash" },
      { value: "google-gemini-2-0-flash-exp", label: "Gemini 2.0 Flash Exp" },
      { value: "google-gemini-1-5-flash", label: "Gemini 1.5 Flash" },
      { value: "google-gemini-1-5-pro", label: "Gemini 1.5 Pro" },
      { value: "google-gemini-pro", label: "Gemini Pro" },
    ]
  },
  xai: {
    name: "xAI",
    models: [
      { value: "xai-grok-2-mini", label: "Grok 2 Mini" },
      { value: "xai-grok-2", label: "Grok 2" },
      { value: "xai-grok-beta", label: "Grok Beta" },
    ]
  },
  deepseek: {
    name: "DeepSeek",
    models: [
      { value: "deepseek-deepseek-chat", label: "DeepSeek Chat" },
      { value: "deepseek-deepseek-coder", label: "DeepSeek Coder" },
      { value: "deepseek-deepseek-math", label: "DeepSeek Math" },
    ]
  },
  groq: {
    name: "Groq",
    models: [
      { value: "groq-llama-3-3-70b", label: "Llama 3.3 70B" },
      { value: "groq-llama-3-1-8b", label: "Llama 3.1 8B" },
      { value: "groq-llama-3-2-1b", label: "Llama 3.2 1B" },
      { value: "groq-llama-3-2-3b", label: "Llama 3.2 3B" },
      { value: "groq-mixtral-8x7b", label: "Mixtral 8x7B" },
      { value: "groq-qwen-2-5-72b", label: "Qwen 2.5 72B" },
    ]
  },
  "ollama-cloud": {
    name: "Ollama Cloud",
    models: [
      { value: "qwen3.5:397b-cloud", label: "Qwen 3.5 397B" },
      { value: "minimax-m2.7:cloud", label: "MiniMax M2.7" },
      { value: "glm-4.7:cloud", label: "GLM 4.7" },
      { value: "glm-5.1:cloud", label: "GLM 5.1" },
      { value: "kimi-k2.5:cloud", label: "Kimi K2.5" },
      { value: "nemotron-3-nano:30b-cloud", label: "Nemotron 3 Nano 30B" },
      { value: "nemotron-3-super:cloud", label: "Nemotron 3 Super" },
      { value: "rnj-1:8b-cloud", label: "RNJ-1 8B" },
      { value: "gemini-3-flash-preview:cloud", label: "Gemini 3 Flash Preview" },
    ]
  },
  perplexity: {
    name: "Perplexity",
    models: [
      { value: "perplexity-sonar", label: "Sonar" },
      { value: "perplexity-sonar-pro", label: "Sonar Pro" },
      { value: "perplexity-sonar-reasoning", label: "Sonar Reasoning" },
      { value: "perplexity-sonar-reasoning-plus", label: "Sonar Reasoning+" },
    ]
  }
}

// Open inline config panel for a provider
function openProviderConfig(provider) {
  activeProvider = provider

  const meta = PROVIDER_META[provider]
  if (!meta) return

  configProviderName.textContent = meta.name
  configProviderIcon.style.color = {
    openai: "#6ee7b7",
    anthropic: "#fcd34d",
    google: "#fcd34d",
    xai: "rgba(255,255,255,0.8)",
    deepseek: "#7dd3fc",
    groq: "#fca5a5",
    "ollama-cloud": "#f97316",
    perplexity: "#20B4E3",
  }[provider] || "rgba(255,255,255,0.5)"

  // Load stored config
  loadProviderConfig(provider)

  // Switch views - show config panel, hide provider list
  settingsProvidersView.style.display = "none"
  providerConfigPanel.classList.add("open")

  // Focus input
  configApiKeyInput.focus()
}

function closeProviderConfig() {
  if (!providerConfigPanel) return
  activeProvider = null
  providerConfigPanel.classList.remove("open")
  if (settingsProvidersView) settingsProvidersView.style.display = ""
  if (configTestResult) {
    configTestResult.className = "config-inline-result"
    configTestResult.textContent = ""
  }
  if (configSyncEnvCheckbox) configSyncEnvCheckbox.checked = false
  if (configEnvWarning) configEnvWarning.classList.remove("show")
  if (configRestartHint) configRestartHint.style.display = "none"

  // Switch back to providers tab
  settingsTabs.forEach(t => t.classList.remove('active'))
  settingsTabContents.forEach(c => c.classList.remove('active'))
  const providersTab = document.querySelector('.settings-tab[data-tab="providers"]')
  const providersContent = document.querySelector('.settings-tab-content[data-content="providers"]')
  if (providersTab) providersTab.classList.add('active')
  if (providersContent) providersContent.classList.add('active')
}

// Load provider config from store
async function loadProviderConfig(provider) {
  let stored = {}
  try { stored = await window.api.storeGet("provider_" + provider) || {} } catch {}
  const hasKey = await checkProviderHasKey(provider)

  // Clear the API key input for security
  configApiKeyInput.value = ""
  // Only show masked placeholder if key exists (no actual key in input)
  if (hasKey) {
    configApiKeyInput.placeholder = "API key configured ••••••••"
  } else {
    configApiKeyInput.placeholder = getApiKeyHint(provider)
  }

  const statusBadge = document.getElementById("configStatusBadge")
  const toggle = document.getElementById("toggle-" + provider)
  const isEnabled = stored.enabled !== false && hasKey

  if (statusBadge) {
    if (isEnabled) {
      const lastUpdated = stored.lastUpdated
      let timeText = "Connected"
      if (lastUpdated) {
        const elapsed = Date.now() - lastUpdated
        const minutes = Math.floor(elapsed / 60000)
        if (minutes < 1) timeText = "Just configured"
        else if (minutes < 60) timeText = `Active (${minutes}m ago)`
        else timeText = `Active (${Math.floor(minutes / 60)}h ago)`
      }
      statusBadge.textContent = timeText
      statusBadge.className = "config-status-badge enabled"
    } else {
      statusBadge.textContent = hasKey ? "Disabled" : "Add API key to enable"
      statusBadge.className = "config-status-badge"
    }
  }
  if (toggle) toggle.checked = isEnabled
}

// Check if provider has API key configured (backend + local encrypted store)
async function checkProviderHasKey(provider) {
  try {
    const providers = await window.api.getProviders()
    if (providers[provider]) return true
  } catch {}
  try {
    const local = await window.api.hasApiKey(provider)
    if (local.hasKey) return true
  } catch {}
  return false
}

// Close settings panel
closeSettingsBtn.addEventListener("click", async () => {
  providerConfigPanel.classList.remove("open")
  settingsPanel.classList.remove("open")
  updatePanelBackdrop()
  updateModelProviderBar()
  await updateCloudModelVisibility()
})

// Save button
/**
 * Validate API key format for different providers.
 * Returns true if format is valid, false otherwise.
 */
function validateApiKeyFormat(provider, apiKey) {
  const formats = {
    openai: /^sk-[a-zA-Z0-9]{20,}$/,
    anthropic: /^sk-ant-[a-zA-Z0-9_-]{20,}$/,
    google: /^[a-zA-Z0-9_-]{20,}$/,
    xai: /^xai-[a-zA-Z0-9_-]{20,}$/,
    deepseek: /^sk-[a-zA-Z0-9_-]{20,}$/,
    groq: /^gsk_[a-zA-Z0-9_-]{20,}$/,
    "ollama-cloud": /^.{10,}$/,  // Ollama Cloud: any string, min 10 chars
    perplexity: /^pplx-[a-zA-Z0-9_-]{20,}$/,
  }
  const regex = formats[provider]
  if (!regex) return true // Unknown provider, skip validation
  return regex.test(apiKey)
}

/**
 * Get API key format hint for a provider.
 */
function getApiKeyHint(provider) {
  const hints = {
    openai: "Format: sk-xxxxxxxxxxxxxxxxxxxxxxxx",
    anthropic: "Format: sk-ant-xxxxxxxxxxxxxxxxxxxxxxxx",
    google: "Format: AIza... (starts with AIza)",
    xai: "Format: xai-xxxxxxxxxxxxxxxxxxxxxxxx",
    deepseek: "Format: sk-xxxxxxxxxxxxxxxxxxxxxxxx",
    groq: "Format: gsk_xxxxxxxxxxxxxxxxxxxxxx",
    "ollama-cloud": "Format: Your ollama.com API key (10+ chars)",
    perplexity: "Format: pplx-xxxxxxxxxxxxxxxxxxxxxxxx",
  }
  return hints[provider] || "Enter your API key"
}

configSaveBtn.addEventListener("click", async () => {
  const apiKey = sanitizeInput(configApiKeyInput.value.trim())

  if (!apiKey) {
    configTestResult.className = "config-inline-result error"
    configTestResult.textContent = "Enter an API key first"
    configApiKeyInput.focus()
    return
  }

  // Validate API key format
  if (!validateApiKeyFormat(activeProvider, apiKey)) {
    configTestResult.className = "config-inline-result error"
    configTestResult.textContent = "Invalid API key format. " + getApiKeyHint(activeProvider)
    configApiKeyInput.focus()
    return
  }

  // Show loading state
  configSaveBtn.disabled = true
  configSaveBtn.textContent = "Saving..."
  configTestResult.className = "config-inline-result"
  configTestResult.textContent = "Verifying API key..."

  try {
    const syncToEnv = configSyncEnvCheckbox?.checked || false
    // Save API key to secure encrypted storage (P1 Privacy)
    // SECURITY: Keys are never sent over HTTP, only via secure IPC
    const saveResult = await window.api.saveApiKey(activeProvider, apiKey, syncToEnv)
    if (!saveResult.success) {
      throw new Error(saveResult.error || "Failed to save API key securely")
    }

    // Update UI — mark provider as enabled
    syncProviderRow(activeProvider, true)

    // Persist enabled state so models stay visible after reload
    const stored = await window.api.storeGet("provider_" + activeProvider) || {}
    await window.api.storeSet("provider_" + activeProvider, { ...stored, enabled: true })

    // Refresh model dropdown so newly-enabled provider models appear
    await updateCloudModelVisibility()

    // Refresh Model Manager so newly-enabled provider sections appear
    if (typeof renderRaceToggles === "function") {
      await renderRaceToggles()
    }

    // Show success (with optional .env warning)
    configTestResult.className = "config-inline-result success"
    configTestResult.textContent = saveResult.warning
      ? "Saved. " + saveResult.warning
      : "Saved successfully"

    // Clear the input field for security
    configApiKeyInput.value = ""

    // If synced to .env, show restart hint (backend needs restart to pick up new env vars)
    if (syncToEnv && configRestartHint) {
      configRestartHint.style.display = "flex"
    } else {
      // Auto-close after short delay if no restart needed
      setTimeout(() => {
        closeProviderConfig()
      }, 800)
    }
  } catch (e) {
    console.error("Provider config error:", e)
    configTestResult.className = "config-inline-result error"

    // Provide more user-friendly error messages
    let errorMsg = e.message || "Unknown error"
    if (errorMsg.includes("401") || errorMsg.includes("403")) {
      errorMsg = "Invalid API key. Please check your key."
    } else if (errorMsg.includes("429")) {
      errorMsg = "Rate limited. Please try again later."
    } else if (errorMsg.includes("connection") || errorMsg.includes("network")) {
      errorMsg = "Network error. Please check your connection."
    }

    configTestResult.textContent = "Failed: " + errorMsg
  } finally {
    configSaveBtn.disabled = false
    configSaveBtn.textContent = "Save"
  }
})

// Enter key on config input
configApiKeyInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") configSaveBtn.click()
})

// Restart backend button in provider config panel
if (configRestartBackendBtn) {
  configRestartBackendBtn.addEventListener("click", async () => {
    configRestartBackendBtn.textContent = "Restarting..."
    configRestartBackendBtn.disabled = true
    try {
      await window.api.restartBackend()
      if (configTestResult) {
        configTestResult.className = "config-inline-result success"
        configTestResult.textContent = "Backend restarted successfully"
      }
      setTimeout(() => closeProviderConfig(), 600)
    } catch (e) {
      console.error("Backend restart failed:", e)
      if (configTestResult) {
        configTestResult.className = "config-inline-result error"
        configTestResult.textContent = "Restart failed: " + (e.message || "Unknown error")
      }
      configRestartBackendBtn.textContent = "Restart"
      configRestartBackendBtn.disabled = false
    }
  })
}

// Toggle .env warning when checkbox changes
configSyncEnvCheckbox?.addEventListener("change", () => {
  configEnvWarning?.classList.toggle("show", configSyncEnvCheckbox.checked)
})

// Sync a provider row's enabled/disabled state
function syncProviderRow(key, enabled) {
  const card = document.getElementById("card-" + key)
  const toggle = document.getElementById("toggle-" + key)
  const statusEl = document.getElementById("status-" + key)
  const dotEl = document.getElementById("dot-" + key)
  if (!card) return

  card.classList.toggle("provider-enabled", enabled)
  card.classList.toggle("provider-disabled", !enabled)
  if (toggle) toggle.checked = enabled
  if (statusEl) {
    if (key === "ollama") {
      statusEl.className = "provider-status " + (enabled ? "connected" : "dimmed")
      statusEl.textContent = enabled ? "Running locally" : "Disabled"
    } else {
      statusEl.className = "provider-status " + (enabled ? "connected" : "dimmed")
      statusEl.textContent = enabled ? "Connected" : "Add API key to enable"
    }
  }
  if (dotEl) {
    dotEl.classList.toggle("active", enabled)
  }
}

// Wire up toggle switches for cloud providers (NOT local ollama - it has no API key)
// Local ollama is always enabled by default and doesn't need API key
const CLOUD_PROVIDERS_WITH_KEY = ["openai", "anthropic", "google", "xai", "deepseek", "groq", "ollama-cloud", "perplexity"]
CLOUD_PROVIDERS_WITH_KEY.forEach(p => {
  const toggle = document.getElementById("toggle-" + p)
  if (!toggle) return
  toggle.addEventListener("change", async () => {
    const isEnabled = toggle.checked
    const stored = await window.api.storeGet("provider_" + p) || {}
    const hasKey = await checkProviderHasKey(p)

    if (isEnabled && !hasKey) {
      // Need API key — open config panel
      openProviderConfig(p)
      return
    }

    // Persist enabled state in store
    await window.api.storeSet("provider_" + p, { ...stored, enabled: isEnabled })

    // Save API key to secure storage if enabling with existing key
    // SECURITY: Only use secure IPC, never send over HTTP
    if (isEnabled && stored.apiKey) {
      try { await window.api.saveApiKey(p, stored.apiKey) } catch {}
    }

    syncProviderRow(p, isEnabled)
  })
})

// Local Ollama - always enabled, no API key needed
const ollamaToggle = document.getElementById("toggle-ollama")
if (ollamaToggle) {
  ollamaToggle.checked = true
  ollamaToggle.addEventListener("change", async () => {
    // Local ollama is always on - just persist state
    const stored = await window.api.storeGet("provider_ollama") || {}
    await window.api.storeSet("provider_ollama", { ...stored, enabled: ollamaToggle.checked })
    syncProviderRow("ollama", ollamaToggle.checked)
  })
}

function updateActiveProviders() {
  const selected = cloudModelSelect ? cloudModelSelect.value : "auto"
  const activeMap = {
    // OpenAI
    "openai-gpt-4o-mini": "openai",
    "openai-gpt-4o": "openai",
    "openai-gpt-4-turbo": "openai",
    "openai-o1-mini": "openai",
    "openai-o3-mini": "openai",
    "openai-gpt-3.5-turbo": "openai",
    // Anthropic
    "anthropic-claude-3-5-haiku": "anthropic",
    "anthropic-claude-3-5-sonnet": "anthropic",
    "anthropic-claude-sonnet-4-20250514": "anthropic",
    "anthropic-claude-opus-4-20250514": "anthropic",
    // Google
    "google-gemini-2-0-flash": "google",
    "google-gemini-2-0-flash-exp": "google",
    "google-gemini-1-5-flash": "google",
    "google-gemini-1-5-pro": "google",
    "google-gemini-pro": "google",
    // xAI
    "xai-grok-2-mini": "xai",
    "xai-grok-2": "xai",
    "xai-grok-beta": "xai",
    // DeepSeek
    "deepseek-deepseek-chat": "deepseek",
    "deepseek-deepseek-coder": "deepseek",
    "deepseek-deepseek-math": "deepseek",
    // Groq
    "groq-llama-3-3-70b": "groq",
    "groq-llama-3-1-8b": "groq",
    "groq-llama-3-2-1b": "groq",
    "groq-llama-3-2-3b": "groq",
    "groq-mixtral-8x7b": "groq",
    "groq-qwen-2-5-72b": "groq",
    // Perplexity
    "perplexity-sonar": "perplexity",
    "perplexity-sonar-pro": "perplexity",
    "perplexity-sonar-reasoning": "perplexity",
    "perplexity-sonar-reasoning-plus": "perplexity",
    // Ollama Cloud
    "qwen3.5:397b-cloud": "ollama-cloud",
    "minimax-m2.7:cloud": "ollama-cloud",
    "glm-4.7:cloud": "ollama-cloud",
    "glm-5.1:cloud": "ollama-cloud",
    "kimi-k2.5:cloud": "ollama-cloud",
    "nemotron-3-nano:30b-cloud": "ollama-cloud",
    "nemotron-3-super:cloud": "ollama-cloud",
    "rnj-1:8b-cloud": "ollama-cloud",
    "gemini-3-flash-preview:cloud": "ollama-cloud",
  }

  // Add custom models to activeMap (from localStorage)
  const customModels = loadCustomModels()
  for (const cm of customModels) {
    activeMap[cm.value] = "ollama-cloud"
  }
  const activeKey = activeMap[selected]

  // Clear .active from all provider rows
  document.querySelectorAll(".provider-row").forEach(el => el.classList.remove("active"))

  // Set .active for the current cloud model provider, or ollama
  const activeCard = document.getElementById("card-" + (activeKey || "ollama"))
  if (activeCard) activeCard.classList.add("active")
}

// === Custom Cloud Model Management ===
// Users can add any Ollama Cloud model via "Add Custom Model" in the dropdowns.
// Custom models are persisted in localStorage and rendered dynamically.

const CUSTOM_MODELS_KEY = "ant_custom_cloud_models"
const DISABLED_MODELS_KEY = "ant_disabled_models"

// Per-model race toggle — disabled models are excluded from the race
function getDisabledModels() {
  try {
    const saved = localStorage.getItem(DISABLED_MODELS_KEY)
    return saved ? JSON.parse(saved) : []
  } catch (e) { return [] }
}

function setModelDisabled(modelValue, disabled) {
  let list = getDisabledModels()
  if (disabled) {
    if (!list.includes(modelValue)) list.push(modelValue)
  } else {
    list = list.filter(m => m !== modelValue)
  }
  localStorage.setItem(DISABLED_MODELS_KEY, JSON.stringify(list))
}

function isModelDisabled(modelValue) {
  return getDisabledModels().includes(modelValue)
}

function loadCustomModels() {
  try {
    const saved = localStorage.getItem(CUSTOM_MODELS_KEY)
    return saved ? JSON.parse(saved) : []
  } catch (e) { return [] }
}

function saveCustomModels(models) {
  try {
    localStorage.setItem(CUSTOM_MODELS_KEY, JSON.stringify(models))
  } catch (e) { /* ignore */ }
}

function addCustomModelToDropdowns(name, value) {
  // Add to toolbar <select>
  const modelSelect = document.getElementById("modelSelect")
  if (modelSelect) {
    const fastGroup = modelSelect.querySelector('optgroup[label="Fast & Affordable"]')
    if (fastGroup && !fastGroup.querySelector(`option[value="${CSS.escape(value)}"]`)) {
      const opt = document.createElement("option")
      opt.value = value
      const displayName = name.includes("★") ? name : name + " [Default]"
	      opt.textContent = displayName
      fastGroup.appendChild(opt)
    }
  }

  // Add to settings dropdown menu
  const settingsMenu = document.getElementById("cloudModelMenu")
  if (settingsMenu) {
    const container = document.getElementById("customModelsContainer")
    if (container && !container.querySelector(`[data-value="${value}"]`)) {
      const item = document.createElement("div")
      item.className = "custom-model-entry"
      item.dataset.value = value
      item.innerHTML = `
        <span class="custom-model-name">${name}</span>
        <span class="custom-model-badge">custom</span>
        <span class="remove-custom-model" data-value="${value}" title="Remove">×</span>
      `
      container.appendChild(item)

      // Click to select — update hidden input, display text, and trigger onChange
      item.addEventListener("click", (e) => {
        if (e.target.classList.contains("remove-custom-model")) return
        const hidden = document.getElementById("cloudModelSelect")
        const textEl = document.getElementById("cloudModelText")
        const menu = document.getElementById("cloudModelMenu")
        if (hidden) hidden.value = value
        if (textEl) textEl.textContent = name
        if (menu) {
          menu.querySelectorAll(".custom-dropdown-item, .custom-model-entry").forEach(i => i.classList.remove("selected"))
        }
        item.classList.add("selected")
        // Sync toolbar model select
        if (modelSelect) modelSelect.value = value
        window.api.storeSet("cloudModel", value)
        updateActiveProviders()
      })

      // Remove button
      item.querySelector(".remove-custom-model").addEventListener("click", (e) => {
        e.stopPropagation()
        removeCustomModel(value)
      })
    }
  }
}

function removeCustomModel(value) {
  let models = loadCustomModels()
  models = models.filter(m => m.value !== value)
  saveCustomModels(models)

  // Remove from toolbar <select>
  const modelSelect = document.getElementById("modelSelect")
  if (modelSelect) {
    const opt = modelSelect.querySelector(`option[value="${value}"]`)
    if (opt) opt.remove()
  }

  // Remove from settings dropdown
  const container = document.getElementById("customModelsContainer")
  if (container) {
    const item = container.querySelector(`[data-value="${value}"]`)
    if (item) item.remove()
  }
}

function initCustomModels() {
  const models = loadCustomModels()
  for (const m of models) {
    addCustomModelToDropdowns(m.name, m.value)
  }

  // Wire up "Add Custom Model" in settings dropdown
  const addBtn = document.querySelector('.add-custom-model[data-value="__add_custom__"]')
  if (addBtn) {
    addBtn.addEventListener("click", (e) => {
      e.stopPropagation()
      showAddCustomModelDialog()
    })
  }

  // Also wire up "Add Custom Model" in toolbar select (via right-click or double-click context)
  // The toolbar <select> doesn't support custom items natively,
  // so we add it through addCustomModelToDropdowns above
}

// === Dynamic Local Ollama Model Detection ===
// Fetches installed models from /ollama/models and populates the toolbar dropdown + settings list

async function loadLocalOllamaModels() {
  try {
    const headers = {}
    try {
      const token = localStorage.getItem('ainotetaker_auth_token')
      if (token) headers['Authorization'] = `Bearer ${token}`
    } catch {}
    const response = await fetch(`${API_BASE}/ollama/models`, { headers })
    if (!response.ok) {
      console.warn("[loadLocalOllamaModels] Failed to fetch models:", response.status)
      return []
    }
    const data = await response.json()
    const models = data.models || []

    // Populate toolbar <select> optgroup
    const localGroup = document.getElementById("ollamaLocalGroup")
    if (localGroup) {
      // Remove existing dynamic options (keep the optgroup itself)
      localGroup.innerHTML = ""
      for (const m of models) {
        const opt = document.createElement("option")
        opt.value = m.name  // e.g. "qwen2.5:1.5b"
        opt.textContent = m.name
        opt.dataset.localModel = "true"
        opt.dataset.provider = "ollama"
        localGroup.appendChild(opt)
      }
    }

    // Also update settings panel Ollama models list with delete buttons
    const settingsList = document.getElementById("ollamaModelsList")
    if (settingsList) {
      if (models.length === 0) {
        settingsList.innerHTML = '<div class="ollama-models-loading">No local models found</div>'
      } else {
        settingsList.innerHTML = models.map(m => `
          <div class="ollama-model-item" data-model-name="${m.name}">
            <span class="ollama-model-name">${m.name}</span>
            <span class="ollama-model-size">${formatOllamaSize(m.size)}</span>
            <button class="ollama-model-delete" data-model-name="${m.name}" title="Delete model">&times;</button>
          </div>
        `).join("")

        // Wire up delete buttons
        settingsList.querySelectorAll(".ollama-model-delete").forEach(btn => {
          btn.addEventListener("click", async () => {
            const modelName = btn.dataset.modelName
            if (!modelName) return
            if (!confirm(`Delete local model "${modelName}"? This cannot be undone.`)) return
            try {
              await window.api.deleteOllamaModel(modelName)
              btn.closest(".ollama-model-item").remove()
              await loadLocalOllamaModels() // Refresh
            } catch (e) {
              console.error("[loadLocalOllamaModels] Delete failed:", e)
            }
          })
        })
      }
    }

    // Update activeMap with local model entries
    for (const m of models) {
      // Local Ollama models map to "ollama" provider
      // They don't need an activeMap entry since they use the ":" naming convention
    }

    // Refresh race toggles to include newly detected models
    if (typeof renderRaceToggles === "function") {
      await renderRaceToggles()
    }

    return models
  } catch (e) {
    console.warn("[loadLocalOllamaModels] Error fetching models:", e)
    return []
  }
}

function formatOllamaSize(bytes) {
  if (!bytes || bytes === 0) return ""
  const k = 1024
  const sizes = ["B", "KB", "MB", "GB"]
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i]
}

// Interlinked model visibility: disables (not hides) options from providers without keys
// so users can discover available models. Uses data-provider attributes for reliable matching.
async function updateCloudModelVisibility() {
  let backendProviders = {}
  try {
    backendProviders = await window.api.getProviders()
  } catch (e) {
    console.warn("[updateCloudModelVisibility] Could not fetch providers:", e)
  }

  const selectEl = document.getElementById("modelSelect")
  if (!selectEl) return

  const disabledModels = getDisabledModels()

  // Build provider state map
  const providerState = {}
  for (const provider of CLOUD_PROVIDERS_WITH_KEY) {
    let stored = {}
    try {
      stored = await window.api.storeGet("provider_" + provider) || {}
    } catch (e) {
      console.warn(`[updateCloudModelVisibility] Could not read store for ${provider}:`, e)
    }
    const hasKeyBackend = !!backendProviders[provider]
    let hasKeyLocal = false
    try { hasKeyLocal = (await window.api.hasApiKey(provider)).hasKey } catch {}
    const hasKey = hasKeyBackend || hasKeyLocal
    const isEnabled = hasKey && stored.enabled !== false
    providerState[provider] = { hasKey, isEnabled }
  }

  // Ensure local Ollama is always enabled
  providerState["ollama"] = { hasKey: true, isEnabled: true }

  // Update each option based on its data-provider attribute
  // Front-page dropdown: selectable if key exists (ignore toggle) so users can always
  // pick from providers they have keys for. Toggle controls race-mode inclusion only.
  selectEl.querySelectorAll("option[data-provider]").forEach(opt => {
    const provider = opt.dataset.provider
    const state = providerState[provider]
    if (!state) return
    const modelDisabled = disabledModels.includes(opt.value)
    const shouldDisable = !state.hasKey || modelDisabled
    opt.disabled = shouldDisable
    // Keep option visible (interlink UX) — remove hidden
    opt.hidden = false
    // Add/remove CSS classes for styling
    opt.classList.toggle("model-option-no-key", !state.hasKey)
    opt.classList.toggle("model-option-disabled", modelDisabled)
  })

  // Update model provider bar below dropdown
  updateModelProviderBar()

  // Also update settings panel provider cards visibility
  for (const provider of CLOUD_PROVIDERS_WITH_KEY) {
    const card = document.getElementById("card-" + provider)
    if (!card) continue
    const state = providerState[provider]
    if (!state) continue
    card.classList.toggle("provider-no-key", !state.hasKey)
  }

  console.log("[updateCloudModelVisibility] Provider state:", providerState)
}

// Map a model value to its provider name
function getModelProvider(modelValue) {
  if (!modelValue || modelValue === "auto") return null
  if (modelValue.endsWith(":cloud")) return { id: "ollama-cloud", name: "Ollama Cloud" }
  if (modelValue.includes(":")) return { id: "ollama", name: "Local Ollama" }
  const prefixMap = {
    "openai-": { id: "openai", name: "OpenAI" },
    "anthropic-": { id: "anthropic", name: "Anthropic" },
    "google-": { id: "google", name: "Google" },
    "xai-": { id: "xai", name: "xAI" },
    "deepseek-": { id: "deepseek", name: "DeepSeek" },
    "groq-": { id: "groq", name: "Groq" },
    "perplexity-": { id: "perplexity", name: "Perplexity" },
  }
  for (const [prefix, info] of Object.entries(prefixMap)) {
    if (modelValue.startsWith(prefix)) return info
  }
  return null
}

// Update the model provider info bar below the model dropdown
async function updateModelProviderBar() {
  const bar = document.getElementById("modelProviderBar")
  const badge = document.getElementById("modelProviderBadge")
  const status = document.getElementById("modelProviderStatus")
  const configBtn = document.getElementById("modelProviderConfigBtn")
  if (!bar || !badge || !status) return

  const modelValue = modelSelect ? modelSelect.value : "auto"
  const provider = getModelProvider(modelValue)

  if (!provider || provider.id === "ollama") {
    bar.style.display = "none"
    return
  }

  bar.style.display = "flex"
  badge.textContent = provider.name

  // Check if provider has key and is enabled
  let hasKeyLocal = false
  try { hasKeyLocal = (await window.api.hasApiKey(provider.id)).hasKey } catch {}
  let backendProviders = {}
  try { backendProviders = await window.api.getProviders() } catch {}
  let stored = {}
  try { stored = await window.api.storeGet("provider_" + provider.id) || {} } catch {}
  const hasKeyBackend = !!backendProviders[provider.id]
  const hasKey = hasKeyBackend || hasKeyLocal
  const isEnabled = hasKey && stored.enabled !== false

  if (hasKey && isEnabled) {
    status.textContent = "Ready"
    status.style.color = "#6ee7b7"
    bar.classList.remove("provider-missing-key")
    if (configBtn) configBtn.style.display = "none"
  } else if (hasKey && !isEnabled) {
    status.textContent = "Disabled in settings"
    status.style.color = "var(--text-dim)"
    bar.classList.add("provider-missing-key")
    if (configBtn) {
      configBtn.style.display = "inline-block"
      configBtn.textContent = "Enable"
    }
  } else {
    status.textContent = "API key required"
    status.style.color = "#fca5a5"
    bar.classList.add("provider-missing-key")
    if (configBtn) {
      configBtn.style.display = "inline-block"
      configBtn.textContent = "Add Key"
    }
  }
}

// Model provider config button (Add Key / Enable)
document.getElementById("modelProviderConfigBtn")?.addEventListener("click", () => {
  const modelValue = modelSelect ? modelSelect.value : "auto"
  const provider = getModelProvider(modelValue)
  if (provider) {
    openSettings()
    // Switch to providers tab and open config for this provider
    settingsTabs.forEach(t => t.classList.remove("active"))
    settingsTabContents.forEach(c => c.classList.remove("active"))
    const providersTab = document.querySelector('.settings-tab[data-tab="providers"]')
    const providersContent = document.querySelector('.settings-tab-content[data-content="providers"]')
    if (providersTab) providersTab.classList.add("active")
    if (providersContent) providersContent.classList.add("active")
    openProviderConfig(provider.id)
  }
})

// === Ollama Model Pull Handler ===
if (ollamaPullBtn) {
  ollamaPullBtn.addEventListener("click", async () => {
    const modelName = ollamaPullInput ? ollamaPullInput.value.trim() : ""
    if (!modelName) return

    ollamaPullBtn.disabled = true
    ollamaPullBtn.textContent = "Pulling..."
    if (ollamaPullStatus) {
      ollamaPullStatus.textContent = `Pulling ${modelName}...`
      ollamaPullStatus.style.color = "var(--text-dim)"
    }

    try {
      const response = await window.api.pullOllamaModel(modelName)
      const result = await response.json()

      if (ollamaPullStatus) {
        ollamaPullStatus.textContent = `Successfully pulled ${modelName}`
        ollamaPullStatus.style.color = "#22c55e"
      }
      if (ollamaPullInput) ollamaPullInput.value = ""

      // Refresh local models list
      await loadLocalOllamaModels()
    } catch (e) {
      console.error("[Pull] Failed:", e)
      if (ollamaPullStatus) {
        ollamaPullStatus.textContent = `Failed to pull ${modelName}: ${e.message || "Unknown error"}`
        ollamaPullStatus.style.color = "#ef4444"
      }
    } finally {
      ollamaPullBtn.disabled = false
      ollamaPullBtn.textContent = "Pull"
    }
  })
}

// === Race Toggle Rendering ===
// Renders per-model on/off switches in the Race Toggles settings section
async function renderRaceToggles() {
  // Backward compat: render into old raceToggleList if it exists
  const oldContainer = document.getElementById("raceToggleList")
  if (oldContainer) oldContainer.innerHTML = ""

  const container = document.getElementById("modelManagerList")
  if (!container) return

  const disabledModels = getDisabledModels()

  // Provider badge initials
  const providerInitials = {
    openai: "O",
    anthropic: "A",
    google: "G",
    xai: "X",
    deepseek: "D",
    groq: "Q",
    perplexity: "P",
    "ollama-cloud": "OC",
    ollama: "L"
  }

  // Fetch provider key status
  let backendProviders = {}
  try { backendProviders = await window.api.getProviders() } catch {}

  let html = ""

  // Cloud provider models from PROVIDER_META
  for (const [provider, meta] of Object.entries(PROVIDER_META)) {
    let hasKeyLocal = false
    try { hasKeyLocal = (await window.api.hasApiKey(provider)).hasKey } catch {}
    const hasKeyBackend = !!backendProviders[provider]
    const hasKey = hasKeyBackend || hasKeyLocal
    const providerDisabled = !hasKey

    html += `<div class="model-provider-section ${providerDisabled ? 'provider-disabled' : ''}">`
    html += `<div class="model-provider-header">`
    html += `<span class="model-provider-badge provider-badge-${provider}">${providerInitials[provider] || provider[0].toUpperCase()}</span>`
    html += `<span class="model-provider-name">${meta.name}</span>`
    html += `<span class="model-provider-status ${hasKey ? 'ready' : 'nokey'}">${hasKey ? 'Ready' : 'No Key'}</span>`
    html += `<div class="model-provider-actions">`
    html += `<button data-provider="${provider}" data-action="enable-all">All On</button>`
    html += `<button data-provider="${provider}" data-action="disable-all">All Off</button>`
    html += `</div></div>`

    html += `<div class="model-grid">`
    for (const model of meta.models) {
      const isDisabled = disabledModels.includes(model.value)
      html += `<div class="model-card ${isDisabled ? 'disabled' : ''}" data-model-value="${model.value}">`
      html += `<div class="model-card-info">`
      html += `<span class="model-card-name">${model.label}</span>`
      html += `<span class="model-card-value">${model.value}</span>`
      html += `</div>`
      html += `<label class="model-card-toggle">`
      html += `<input type="checkbox" data-model-value="${model.value}" ${isDisabled ? '' : 'checked'} ${providerDisabled ? 'disabled' : ''} />`
      html += `<span class="toggle-track"></span>`
      html += `</label>`
      html += `</div>`
    }
    html += `</div></div>`
  }

  // Local Ollama models
  const localGroup = document.getElementById("ollamaLocalGroup")
  if (localGroup) {
    const localOptions = localGroup.querySelectorAll("option")
    if (localOptions.length > 0) {
      html += `<div class="model-provider-section">`
      html += `<div class="model-provider-header">`
      html += `<span class="model-provider-badge provider-badge-ollama">L</span>`
      html += `<span class="model-provider-name">Local Ollama</span>`
      html += `<span class="model-provider-status ready">Ready</span>`
      html += `<div class="model-provider-actions">`
      html += `<button data-provider="ollama" data-action="enable-all">All On</button>`
      html += `<button data-provider="ollama" data-action="disable-all">All Off</button>`
      html += `</div></div>`

      html += `<div class="model-grid">`
      for (const opt of localOptions) {
        const isDisabled = disabledModels.includes(opt.value)
        html += `<div class="model-card ${isDisabled ? 'disabled' : ''}" data-model-value="${opt.value}">`
        html += `<div class="model-card-info">`
        html += `<span class="model-card-name">${opt.textContent}</span>`
        html += `<span class="model-card-value">${opt.value}</span>`
        html += `</div>`
        html += `<label class="model-card-toggle">`
        html += `<input type="checkbox" data-model-value="${opt.value}" ${isDisabled ? '' : 'checked'} />`
        html += `<span class="toggle-track"></span>`
        html += `</label>`
        html += `</div>`
      }
      html += `</div></div>`
    }
  }

  // Custom cloud models from localStorage
  const customModels = loadCustomModels()
  if (customModels.length > 0) {
    html += `<div class="model-provider-section">`
    html += `<div class="model-provider-header">`
    html += `<span class="model-provider-badge provider-badge-ollama-cloud">C</span>`
    html += `<span class="model-provider-name">Custom Models</span>`
    html += `<span class="model-provider-status ready">Ready</span>`
    html += `<div class="model-provider-actions">`
    html += `<button data-provider="custom" data-action="enable-all">All On</button>`
    html += `<button data-provider="custom" data-action="disable-all">All Off</button>`
    html += `</div></div>`

    html += `<div class="model-grid">`
    for (const cm of customModels) {
      const isDisabled = disabledModels.includes(cm.value)
      html += `<div class="model-card ${isDisabled ? 'disabled' : ''}" data-model-value="${cm.value}">`
      html += `<div class="model-card-info">`
      html += `<span class="model-card-name">${cm.name}</span>`
      html += `<span class="model-card-value">${cm.value}</span>`
      html += `</div>`
      html += `<label class="model-card-toggle">`
      html += `<input type="checkbox" data-model-value="${cm.value}" ${isDisabled ? '' : 'checked'} />`
      html += `<span class="toggle-track"></span>`
      html += `</label>`
      html += `</div>`
    }
    html += `</div></div>`
  }

  container.innerHTML = html

  // Wire up individual toggle event listeners
  container.querySelectorAll("input[type='checkbox'][data-model-value]").forEach(cb => {
    cb.addEventListener("change", () => {
      const modelValue = cb.dataset.modelValue
      const isDisabled = !cb.checked
      setModelDisabled(modelValue, isDisabled)

      // Update card styling
      const card = cb.closest(".model-card")
      if (card) {
        card.classList.toggle("disabled", isDisabled)
      }

      // Update cloud model visibility in toolbar
      updateCloudModelVisibility()
    })
  })

  // Wire up provider-level enable/disable all buttons
  container.querySelectorAll(".model-provider-actions button").forEach(btn => {
    btn.addEventListener("click", () => {
      const provider = btn.dataset.provider
      const action = btn.dataset.action
      const section = btn.closest(".model-provider-section")
      if (!section) return
      const checkboxes = section.querySelectorAll("input[type='checkbox'][data-model-value]")
      checkboxes.forEach(cb => {
        if (cb.disabled) return
        const shouldCheck = action === "enable-all"
        if (cb.checked !== shouldCheck) {
          cb.checked = shouldCheck
          cb.dispatchEvent(new Event("change"))
        }
      })
    })
  })
}

function showAddCustomModelDialog() {
  const menu = document.getElementById("cloudModelMenu")
  if (!menu) return

  // Check if form already exists
  if (document.getElementById("addCustomModelForm")) return

  const form = document.createElement("div")
  form.id = "addCustomModelForm"
  form.className = "add-custom-model-form"
  form.innerHTML = `
    <input type="text" id="customModelInput" placeholder="e.g., my-model:cloud" />
    <button id="customModelAddBtn">Add</button>
  `
  menu.appendChild(form)

  const input = document.getElementById("customModelInput")
  const btn = document.getElementById("customModelAddBtn")

  const doAdd = () => {
    let val = input.value.trim()
    if (!val) return
    // Auto-append :cloud if missing
    if (!val.includes(":")) val += ":cloud"
    // Check for duplicates
    const existing = loadCustomModels()
    if (existing.find(m => m.value === val)) {
      input.style.borderColor = "#ef4444"
      input.placeholder = "Model already exists"
      return
    }
    const name = val.replace(":cloud", "").replace(/-/g, " ").replace(/\b\w/g, c => c.toUpperCase())
    const models = loadCustomModels()
    models.push({ name, value: val })
    saveCustomModels(models)
    addCustomModelToDropdowns(name, val)
    form.remove()
  }

  btn.addEventListener("click", doAdd)
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") doAdd()
    if (e.key === "Escape") form.remove()
  })
  input.focus()
}

// Provider config buttons — open inline panel
document.querySelectorAll(".provider-config-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    const provider = btn.getAttribute("data-provider")
    if (!provider) return
    openProviderConfig(provider)
  })
})

// Config panel back button
const configBackBtn = document.getElementById("configBackBtn")
if (configBackBtn) {
  configBackBtn.addEventListener("click", () => {
    closeProviderConfig()
  })
}

// Close settings when clicking outside
document.addEventListener("click", (e) => {
  if (!settingsPanel?.classList.contains("open")) return

  const clickedAppMenu = appMenu?.contains(e.target)

  if (clickedAppMenu) return

  if (!settingsPanel?.contains(e.target) && !menuBtn?.contains(e.target)) {
    // If config panel is open, just go back to provider list
    if (providerConfigPanel?.classList.contains("open")) {
      closeProviderConfig()
      return
    }
    // Otherwise close the whole panel
    closeProviderConfig()
    settingsPanel.classList.remove("open")
    updatePanelBackdrop()
  }
})
async function init() {
  try {
    await waitForBackend()

    // Restore user preferences

    // Font size
    const savedFontSize = await window.api.storeGet("fontSize")
    if (savedFontSize && fontSizeSelect) {
      fontSizeSelect.value = savedFontSize
      document.documentElement.style.setProperty("--font-size", savedFontSize + "px")
    }

    // Mode
    const savedMode = await window.api.storeGet("mode")
    if (savedMode && modeSelect) modeSelect.value = savedMode
    updateProviderRecommendation(savedMode || "adaptive")

    // Response style
    const savedResponseStyle = await window.api.storeGet("responseStyle")
    if (savedResponseStyle && responseStyleSelect) {
      responseStyleSelect.value = savedResponseStyle
    }

    // Temperature
    const savedTemperature = await window.api.storeGet("temperature")
    if (savedTemperature && temperatureSelect) {
      temperatureSelect.value = savedTemperature
    }

    // Context
    const savedContextLength = await window.api.storeGet("contextLength")
    if (savedContextLength && contextLengthSelect) {
      contextLengthSelect.value = savedContextLength
    }

    // Token limit
    const savedTokenLimit = await window.api.storeGet("tokenLimit")
    if (savedTokenLimit && tokenLimitSelect) {
      tokenLimitSelect.value = savedTokenLimit
    }

    // Model — init custom models first so their <option> elements exist
    initCustomModels()
    // Auto-detect local Ollama models and populate toolbar dropdown
    await loadLocalOllamaModels()
    const savedModel = await window.api.storeGet("model")
    if (savedModel && modelSelect) {
      modelSelect.value = savedModel
    }

    // Reset model to auto if saved model belongs to a disabled provider
    if (savedModel && savedModel !== "auto" && modelSelect) {
      const providerMap = {
        "openai-": "openai", "anthropic-": "anthropic", "google-": "google",
        "xai-": "xai", "deepseek-": "deepseek", "groq-": "groq"
      }
      let provider = null
      if (savedModel.endsWith(":cloud")) provider = "ollama-cloud"
      else {
        for (const [prefix, p] of Object.entries(providerMap)) {
          if (savedModel.startsWith(prefix)) { provider = p; break }
        }
      }
      if (provider) {
        let stored = {}
        try { stored = (await window.api.storeGet("provider_" + provider)) || {} } catch {}
        let backendProviders = {}
        try { backendProviders = await window.api.getProviders() } catch {}
        let hasKeyLocal = false
        try { hasKeyLocal = (await window.api.hasApiKey(provider)).hasKey } catch {}
        const hasKey = !!backendProviders[provider] || hasKeyLocal
        const isEnabled = hasKey && stored.enabled !== false
        if (!isEnabled) {
          modelSelect.value = "auto"
          await window.api.storeSet("model", "auto")
        }
      }
    }

    // Right-click context menu for copying selected text
    document.addEventListener("contextmenu", (e) => {
      const selection = window.getSelection().toString().trim()
      if (selection) {
        e.preventDefault()
        navigator.clipboard.writeText(selection)
      }
    })

    // Sync stealth state on startup
    await syncStealthState()
    updateStealthUI(null, isUndetectable)

    // Sync screenshot toggle on startup
    await syncScreenshotState()

    // Sync all provider rows on startup
    await syncAllProviderRows()

    // Hide cloud models for providers without API keys
    await updateCloudModelVisibility()

    // Update model provider bar on startup
    updateModelProviderBar()

    // Render per-model race toggles
    await renderRaceToggles()

    // Initialize overlay features (autostart, portable mode)
    await initOverlayFeatures()

    // Pre-warm microphone and audio context for instant voice start
    prewarmVoiceResources()

    // Run onboarding check on first launch
    await checkOnboarding()
  } catch (e) {
    console.error(e)
  }
}

// Sync all cloud provider rows — called on init
async function syncAllProviderRows() {
  const providers = await window.api.getProviders()
  for (const p of CLOUD_PROVIDERS_WITH_KEY) {
    let hasKeyBackend = !!providers[p]
    let hasKeyLocal = false
    try { hasKeyLocal = (await window.api.hasApiKey(p)).hasKey } catch {}
    const hasKey = hasKeyBackend || hasKeyLocal
    let stored = {}
    try { stored = (await window.api.storeGet("provider_" + p)) || {} } catch {}
    const isEnabled = stored.enabled !== false && hasKey
    syncProviderRow(p, isEnabled)
  }
}

// Screenshot capture toggle — privacy control
const toggleScreenshot = document.getElementById("toggle-screenshot")
const screenshotStatusText = document.getElementById("screenshotStatusText")

async function syncScreenshotState() {
  if (!toggleScreenshot) return
  const stored = await window.api.storeGet("screenshotEnabled")
  const enabled = stored !== false // default true
  toggleScreenshot.checked = enabled
  if (screenshotStatusText) {
    screenshotStatusText.textContent = enabled ? "Screenshots enabled" : "Screenshots disabled"
  }
}

toggleScreenshot?.addEventListener("change", async () => {
  const enabled = toggleScreenshot.checked
  await window.api.storeSet("screenshotEnabled", enabled)
  if (screenshotStatusText) {
    screenshotStatusText.textContent = enabled ? "Screenshots enabled" : "Screenshots disabled"
  }
  // Apply to stealth module
  await window.api.setUndetectable(enabled)
})

// ==============================
// ONBOARDING
// ==============================
async function checkOnboarding() {
  const hasOnboarded = await window.api.storeGet("hasOnboarded")
  if (hasOnboarded) return

  const checklist = document.getElementById("onboardingChecklist")
  const note = document.getElementById("onboardingNote")
  const closeBtn = document.getElementById("onboardingClose")
  const modal = document.getElementById("onboardingModal")

  // Step 1: Microphone
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    stream.getTracks().forEach(t => t.stop())
    const micItem = checklist.querySelector('[data-step="mic"]')
    micItem.className = "ok"
    micItem.textContent = "Microphone access granted"
  } catch {
    const micItem = checklist.querySelector('[data-step="mic"]')
    micItem.className = "fail"
    micItem.textContent = "Microphone access denied — please allow in system settings"
  }

  // Step 2: Ollama
  try {
    const r = await fetch(`${API_BASE}/health`)
    if (r.ok) {
      const ollamaItem = checklist.querySelector('[data-step="ollama"]')
      ollamaItem.className = "ok"
      ollamaItem.textContent = "Ollama backend running"
    } else {
      throw new Error("not ok")
    }
  } catch {
    const ollamaItem = checklist.querySelector('[data-step="ollama"]')
    ollamaItem.className = "fail"
    ollamaItem.textContent = "Ollama not running — start with: python backend/main.py"
  }

  // Step 3: Vision model
  try {
    const r = await fetch(`${API_BASE}/providers`)
    if (r.ok) {
      const visionItem = checklist.querySelector('[data-step="vision"]')
      visionItem.className = "ok"
      visionItem.textContent = "Vision model available (moondream/llava)"
    } else {
      throw new Error()
    }
  } catch {
    const visionItem = checklist.querySelector('[data-step="vision"]')
    visionItem.className = "fail"
    visionItem.textContent = "Vision model not found — optional, voice will work without it"
  }

  // Check if all critical items passed
  const micOk = checklist.querySelector('[data-step="mic"]').classList.contains("ok")
  const ollamaOk = checklist.querySelector('[data-step="ollama"]').classList.contains("ok")

  if (micOk && ollamaOk) {
    note.textContent = "You're all set! Press Enter to start talking."
    await window.api.storeSet("hasOnboarded", true)
  } else if (!micOk) {
    note.textContent = "Microphone access is required. Please restart and allow access."
  } else {
    note.textContent = "Start the backend with: python backend/main.py"
  }

  modal.classList.add("open")
  closeBtn.addEventListener("click", () => {
    modal.classList.remove("open")
  })
}

// ==============================
// DOCUMENT UPLOAD
// ==============================
const documentDropzone = document.getElementById("documentDropzone")
const documentFileInput = document.getElementById("documentFileInput")
const documentList = document.getElementById("documentList")

async function loadDocuments() {
  if (!documentList) return
  try {
    const result = await window.api.listDocuments()
    uploadedDocuments = result.documents || []
    renderDocumentList()
  } catch (e) {
    console.error("Failed to load documents:", e)
    if (documentList) {
      documentList.innerHTML = '<div class="document-empty">Failed to load documents</div>'
    }
  }
}

function renderDocumentList() {
  if (!documentList) return

  if (uploadedDocuments.length === 0) {
    documentList.innerHTML = '<div class="document-empty">No documents uploaded yet</div>'
    return
  }

  documentList.innerHTML = uploadedDocuments.map(doc => {
    const icon = doc.name.endsWith('.pdf') ? '&#128196;' :
                 doc.name.endsWith('.docx') ? '&#128221;' : '&#128196;'
    return `
      <div class="document-item" data-id="${doc.id}">
        <span class="document-item-icon">${icon}</span>
        <div class="document-item-info">
          <div class="document-item-name" title="${escapeHtml(doc.name)}">${escapeHtml(doc.name)}</div>
          <div class="document-item-meta">${doc.chunks} chunks</div>
        </div>
        <button class="document-item-delete" onclick="deleteDocument('${doc.id}')" title="Delete">&#10005;</button>
      </div>
    `
  }).join('')
}

async function deleteDocument(docId) {
  try {
    await window.api.deleteDocument(docId)
    await loadDocuments()
  } catch (e) {
    console.error("Failed to delete document:", e)
    alert("Failed to delete document")
  }
}

// Make deleteDocument available globally
window.deleteDocument = deleteDocument

// Document dropzone handlers
if (documentDropzone && documentFileInput) {
  documentDropzone.addEventListener("click", () => documentFileInput.click())

  documentDropzone.addEventListener("dragover", (e) => {
    e.preventDefault()
    documentDropzone.classList.add("dragover")
  })

  documentDropzone.addEventListener("dragleave", () => {
    documentDropzone.classList.remove("dragover")
  })

  documentDropzone.addEventListener("drop", (e) => {
    e.preventDefault()
    documentDropzone.classList.remove("dragover")
    const files = e.dataTransfer.files
    if (files.length > 0) {
      uploadFiles(files)
    }
  })

  documentFileInput.addEventListener("change", (e) => {
    if (e.target.files.length > 0) {
      uploadFiles(e.target.files)
      e.target.value = "" // Reset for next upload
    }
  })
}

async function uploadFiles(files) {
  if (!documentList) return

  documentList.innerHTML = '<div class="document-loading">Uploading...</div>'

  for (const file of files) {
    const formData = new FormData()
    formData.append("file", file)

    try {
      const result = await window.api.uploadDocument(formData)
      if (result.error) {
        console.error("Upload error:", result.error)
        alert(`Failed to upload ${file.name}: ${result.error}`)
      } else {
        console.log("Uploaded:", result.doc_name, result.chunks, "chunks")
      }
    } catch (e) {
      console.error("Upload failed:", e)
      alert(`Failed to upload ${file.name}`)
    }
  }

  await loadDocuments()
}

// ==============================
// INTERVIEW DATA INGESTION
// ==============================
const ingestionRepoInput = document.getElementById("ingestionRepoInput")
const ingestionRepoTags = document.getElementById("ingestionRepoTags")
const ingestionDryRunBtn = document.getElementById("ingestionDryRunBtn")
const ingestionStartBtn = document.getElementById("ingestionStartBtn")
const ingestionStatus = document.getElementById("ingestionStatus")
const ingestionProgressBar = document.getElementById("ingestionProgressBar")
const ingestionStatsEl = document.getElementById("ingestionStats")

let ingestionRepos = []

function addIngestionRepo(repo) {
  repo = repo.trim()
  if (!repo) return
  // Normalize: accept full URLs or owner/repo format
  if (repo.startsWith("https://github.com/")) {
    repo = repo.replace("https://github.com/", "").replace(/\.git$/, "").replace(/\/$/, "")
  }
  if (ingestionRepos.includes(repo)) return
  ingestionRepos.push(repo)
  renderIngestionTags()
}

function flushIngestionInput() {
  // Pick up any text still in the input field
  if (ingestionRepoInput && ingestionRepoInput.value.trim()) {
    addIngestionRepo(ingestionRepoInput.value)
    ingestionRepoInput.value = ""
  }
}

function removeIngestionRepo(repo) {
  ingestionRepos = ingestionRepos.filter((r) => r !== repo)
  renderIngestionTags()
}

function renderIngestionTags() {
  if (!ingestionRepoTags) return
  ingestionRepoTags.innerHTML = ingestionRepos
    .map(
      (repo) =>
        `<span class="ingestion-tag">${repo}<span class="ingestion-tag-remove" data-repo="${repo}">&times;</span></span>`
    )
    .join("")
  ingestionRepoTags.querySelectorAll(".ingestion-tag-remove").forEach((btn) => {
    btn.addEventListener("click", () => removeIngestionRepo(btn.dataset.repo))
  })
}

function getIngestionMode() {
  const checked = document.querySelector('input[name="ingestionMode"]:checked')
  return checked ? checked.value : "full"
}

function showIngestionStatus(stats, error) {
  if (!ingestionStatus) return
  ingestionStatus.style.display = "block"
  if (error) {
    ingestionStatsEl.innerHTML = `<div class="ingestion-error">${error}</div>`
    ingestionProgressBar.style.width = "0%"
    return
  }
  const total = stats.qa_pairs_found + stats.pdfs_processed || 1
  const loaded = stats.qa_pairs_loaded_graph + stats.qa_pairs_loaded_rag + stats.pdfs_loaded_rag
  const pct = Math.min(100, Math.round((loaded / total) * 100))
  ingestionProgressBar.style.width = pct + "%"
  ingestionStatsEl.innerHTML = `
    <div class="stat-row"><span class="stat-label">Q&A found</span><span class="stat-value">${stats.qa_pairs_found}</span></div>
    <div class="stat-row"><span class="stat-label">Q&A → Graph</span><span class="stat-value">${stats.qa_pairs_loaded_graph}</span></div>
    <div class="stat-row"><span class="stat-label">Q&A → RAG</span><span class="stat-value">${stats.qa_pairs_loaded_rag}</span></div>
    <div class="stat-row"><span class="stat-label">Q&A cached</span><span class="stat-value">${stats.qa_pairs_cached}</span></div>
    <div class="stat-row"><span class="stat-label">PDFs processed</span><span class="stat-value">${stats.pdfs_processed}</span></div>
    <div class="stat-row"><span class="stat-label">PDFs → RAG</span><span class="stat-value">${stats.pdfs_loaded_rag}</span></div>
    <div class="stat-row"><span class="stat-label">Graph nodes</span><span class="stat-value">${stats.graph_nodes_created}</span></div>
    <div class="stat-row"><span class="stat-label">RAG chunks</span><span class="stat-value">${stats.rag_chunks_created}</span></div>
    <div class="stat-row"><span class="stat-label">Errors</span><span class="stat-value">${(stats.errors || []).length}</span></div>
    <div class="stat-row"><span class="stat-label">Time</span><span class="stat-value">${stats.elapsed_seconds}s</span></div>
  `
}

async function startIngestion(dryRun = false) {
  if (!ingestionStartBtn || !ingestionStatus) return
  flushIngestionInput()
  if (ingestionRepos.length === 0) {
    alert("Add at least one GitHub repo (e.g. ShyamSunder89/DevOps-Interview-Questions1)")
    return
  }
  const mode = getIngestionMode()
  ingestionStartBtn.disabled = true
  ingestionDryRunBtn.disabled = true
  ingestionStatus.style.display = "block"
  ingestionProgressBar.style.width = "10%"
  ingestionStatsEl.innerHTML = "Cloning repos..."

  try {
    // Start ingestion (returns immediately with task_id)
    const resp = await fetch(`${API_BASE}/agents/ingestion`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        repos: ingestionRepos,
        mode: mode,
        dry_run: dryRun,
      }),
    })
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}))
      throw new Error(err.error?.message || err.detail || `HTTP ${resp.status}`)
    }
    const data = await resp.json()
    if (!data.task_id) {
      // Old-style sync response
      showIngestionStatus(data)
      return
    }

    // Poll for results
    const taskId = data.task_id
    ingestionProgressBar.style.width = "20%"
    ingestionStatsEl.innerHTML = "Processing..."

    const pollInterval = setInterval(async () => {
      try {
        const pollResp = await fetch(`${API_BASE}/agents/ingestion/status?task_id=${taskId}`)
        const pollData = await pollResp.json()
        if (pollData.status === "completed") {
          clearInterval(pollInterval)
          showIngestionStatus(pollData.result)
          ingestionStartBtn.disabled = false
          ingestionDryRunBtn.disabled = false
        } else if (pollData.status === "failed") {
          clearInterval(pollInterval)
          showIngestionStatus(null, pollData.error)
          ingestionStartBtn.disabled = false
          ingestionDryRunBtn.disabled = false
        } else {
          ingestionProgressBar.style.width = "40%"
          ingestionStatsEl.innerHTML = "Still processing..."
        }
      } catch (e) {
        clearInterval(pollInterval)
        showIngestionStatus(null, e.message)
        ingestionStartBtn.disabled = false
        ingestionDryRunBtn.disabled = false
      }
    }, 3000)
  } catch (e) {
    showIngestionStatus(null, e.message)
    ingestionStartBtn.disabled = false
    ingestionDryRunBtn.disabled = false
  }
}

if (ingestionRepoInput) {
  ingestionRepoInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault()
      flushIngestionInput()
    }
  })
}
if (ingestionStartBtn) {
  ingestionStartBtn.addEventListener("click", () => startIngestion(false))
}
if (ingestionDryRunBtn) {
  ingestionDryRunBtn.addEventListener("click", () => startIngestion(true))
}

// ==============================
// SPEAKER DIARIZATION
// ==============================
// Note: Speaker diarization is handled server-side during transcription
// The UI displays speaker labels when available in the transcript

function formatSpeakerLabel(speakerId) {
  // Normalize speaker IDs (SPEAKER_00 -> Speaker 1)
  if (speakerId.startsWith("SPEAKER_")) {
    try {
      const num = parseInt(speakerId.split("_")[1]) + 1
      return `Speaker ${num}`
    } catch {
      return speakerId
    }
  }
  return speakerId
}

function getSpeakerClass(speakerId) {
  if (speakerId.includes("1") || speakerId.endsWith("00")) return "speaker-1"
  if (speakerId.includes("2") || speakerId.endsWith("01")) return "speaker-2"
  if (speakerId.includes("3") || speakerId.endsWith("02")) return "speaker-3"
  if (speakerId.includes("4") || speakerId.endsWith("03")) return "speaker-4"
  return "speaker-unknown"
}

// Function to show speaker transcript modal
function showSpeakerTranscriptModal(transcript) {
  // Create modal if it doesn't exist
  let modal = document.getElementById("speakerTranscriptModal")
  if (!modal) {
    modal = document.createElement("div")
    modal.id = "speakerTranscriptModal"
    modal.className = "modal-overlay"
    modal.innerHTML = `
      <div class="modal-box" style="max-width: 600px; max-height: 80vh;">
        <div class="modal-title">Transcript with Speakers</div>
        <div class="speaker-transcript-content" style="max-height: 60vh; overflow-y: auto; white-space: pre-wrap; font-family: monospace; font-size: 0.9em; line-height: 1.6; background: rgba(0,0,0,0.2); padding: 16px; border-radius: 8px; margin: 16px 0;"></div>
        <div class="modal-actions">
          <button class="settings-btn modal-cancel-btn" onclick="document.getElementById('speakerTranscriptModal').classList.remove('open')">Close</button>
          <button class="settings-btn modal-save-btn" id="copySpeakerTranscriptBtn">Copy</button>
        </div>
      </div>
    `
    document.body.appendChild(modal)
  }

  const content = modal.querySelector(".speaker-transcript-content")
  content.textContent = transcript

  // Copy button handler
  const copyBtn = document.getElementById("copySpeakerTranscriptBtn")
  copyBtn.onclick = () => {
    navigator.clipboard.writeText(transcript).then(() => {
      copyBtn.textContent = "Copied!"
      setTimeout(() => copyBtn.textContent = "Copy", 1500)
    }).catch(() => {
      fallbackCopyText(transcript)
      copyBtn.textContent = "Copied!"
      setTimeout(() => copyBtn.textContent = "Copy", 1500)
    })
  }

  modal.classList.add("open")

  // Close on backdrop click
  modal.addEventListener("click", (e) => {
    if (e.target === modal) modal.classList.remove("open")
  })
}

// Function to create speaker diarization toggle button
function createSpeakerToggle() {
  const btn = document.createElement("button")
  btn.className = "speaker-toggle-btn"
  btn.id = "speakerToggleBtn"
  btn.innerHTML = `
    <span class="speaker-toggle-dot"></span>
    <span class="speaker-toggle-label">Speakers</span>
  `
  btn.title = "Toggle speaker diarization (identifies who is speaking)"
  btn.addEventListener("click", () => {
    speakerDiarizationEnabled = !speakerDiarizationEnabled
    btn.classList.toggle("active", speakerDiarizationEnabled)
    window.api.storeSet("speakerDiarizationEnabled", speakerDiarizationEnabled)
  })
  return btn
}

// Load speaker diarization setting
async function loadSpeakerSetting() {
  const stored = await window.api.storeGet("speakerDiarizationEnabled")
  speakerDiarizationEnabled = stored === true
  const btn = document.getElementById("speakerToggleBtn")
  if (btn) btn.classList.toggle("active", speakerDiarizationEnabled)
}

// Add speaker toggle to controls if not present
function initSpeakerToggle() {
  const controlsStrip = document.querySelector(".controls-strip")
  if (!controlsStrip || document.getElementById("speakerToggleBtn")) return

  const speakerBtn = createSpeakerToggle()
  controlsStrip.appendChild(speakerBtn)
  loadSpeakerSetting()
}

// ==============================
// EXPORT/IMPORT FUNCTIONALITY
// ==============================
const exportAllBtn = document.getElementById("exportAllBtn")
const importBtn = document.getElementById("importBtn")
const exportModal = document.getElementById("exportModal")
const importModal = document.getElementById("importModal")
const cancelExportBtn = document.getElementById("cancelExportBtn")
const confirmExportBtn = document.getElementById("confirmExportBtn")
const cancelImportBtn = document.getElementById("cancelImportBtn")
const importDropzone = document.getElementById("importDropzone")
const importFileInput = document.getElementById("importFileInput")

// Export functionality
if (exportAllBtn) {
  exportAllBtn.addEventListener("click", () => {
    exportCurrentConversation = currentMessages.length > 0 ? currentMessages : null
    openExportModal()
  })
}

function openExportModal() {
  if (exportModal) {
    exportModal.classList.add("open")
  }
}

function closeExportModal() {
  if (exportModal) {
    exportModal.classList.remove("open")
  }
}

if (cancelExportBtn) {
  cancelExportBtn.addEventListener("click", closeExportModal)
}

if (exportModal) {
  exportModal.addEventListener("click", (e) => {
    if (e.target === exportModal) closeExportModal()
  })
}

if (confirmExportBtn) {
  confirmExportBtn.addEventListener("click", async () => {
    const format = document.querySelector('input[name="exportFormat"]:checked')?.value || "markdown"
    const includeMetadata = document.getElementById("includeMetadata")?.checked ?? true
    const includeTimestamps = document.getElementById("includeTimestamps")?.checked ?? false

    let messagesToExport = exportCurrentConversation || currentMessages
    if (!messagesToExport || messagesToExport.length === 0) {
      alert("No conversation to export")
      return
    }

    try {
      const result = await window.api.exportConversation({
        messages: messagesToExport,
        format: format,
        includeMetadata: includeMetadata,
        includeTimestamps: includeTimestamps,
        metadata: {
          mode: modeSelect?.value,
          model: modelSelect?.value,
          exportedFrom: "AI Note Taker"
        }
      })

      if (result.error) {
        alert("Export failed: " + result.error)
        return
      }

      // Save file via dialog
      const saveResult = await window.api.saveFile({
        defaultPath: result.filename,
        filters: getExportFilters(format),
        content: result.content
      })

      if (saveResult.success) {
        confirmExportBtn.textContent = "Exported!"
        setTimeout(() => {
          confirmExportBtn.textContent = "Export"
          closeExportModal()
        }, 1000)
      } else if (saveResult.error) {
        console.error("Save failed:", saveResult.error)
      }
    } catch (e) {
      console.error("Export error:", e)
      alert("Export failed")
    }
  })
}

function getExportFilters(format) {
  if (format === "json") {
    return [{ name: "JSON", extensions: ["json"] }]
  } else if (format === "markdown") {
    return [{ name: "Markdown", extensions: ["md"] }]
  } else {
    return [{ name: "Text", extensions: ["txt"] }]
  }
}

// Export individual conversation by ID
function exportConversationById(conversationId) {
  window.api.conversationLoad(conversationId).then(conv => {
    if (conv && conv.messages) {
      exportCurrentConversation = conv.messages
      openExportModal()
    }
  })
}

window.exportConversation = exportConversationById

// Import functionality
if (importBtn) {
  importBtn.addEventListener("click", () => {
    if (importModal) importModal.classList.add("open")
  })
}

// ==============================
// CLEAR CHAT & SELECT BUTTONS
// ==============================
const clearChatBtn = document.getElementById("clearChatBtn")
const selectBtn = document.getElementById("selectBtn")

// Clear Chat button - context aware behavior
if (clearChatBtn) {
  clearChatBtn.addEventListener("click", async () => {
    // Get selected conversations when in selection mode
    const selectedItems = document.querySelectorAll('.history-item.selected')
    const selectedIds = Array.from(selectedItems).map(item => item.dataset.id)

    if (selectionMode && selectedIds.length > 0) {
      // Delete selected conversations from history
      if (confirm(`Delete ${selectedIds.length} selected conversation(s)?`)) {
        let deletedCount = 0
        for (const id of selectedIds) {
          try {
            await window.api.conversationDelete(id)
            deletedCount++
          } catch (e) {
            console.error('Failed to delete conversation:', e)
          }
        }
        showToast(`${deletedCount} conversation(s) deleted`, "info")
        renderHistoryList() // Refresh the list
        // Exit selection mode
        if (selectBtn) selectBtn.click()
      }
    } else {
      // Clear current active chat
      if (confirm("Clear current chat? This will remove all messages.")) {
        clearConversation()
        showToast("Chat cleared", "info")
      }
    }
  })
}

// Select button - toggle selection mode for conversations
let selectionMode = false
if (selectBtn) {
  selectBtn.addEventListener("click", () => {
    selectionMode = !selectionMode
    selectBtn.classList.toggle("active", selectionMode)
    selectBtn.innerHTML = selectionMode
      ? '<span>&#9745;</span> Done'
      : '<span>&#9744;</span> Select'

    // Toggle checkboxes in history list
    const historyItems = document.querySelectorAll('.history-item')
    historyItems.forEach(item => {
      const checkbox = item.querySelector('.history-item-checkbox')
      if (checkbox) {
        checkbox.style.display = selectionMode ? 'flex' : 'none'
      }
      // Reset selection when exiting mode
      if (!selectionMode) {
        item.classList.remove('selected')
        const checkboxBox = item.querySelector('.history-item-checkbox .checkbox-box')
        if (checkboxBox) checkboxBox.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/></svg>'
      }
    })

    // Reset clear chat button text
    if (clearChatBtn) {
      clearChatBtn.innerHTML = '<span>&#128465;</span> Clear Chat'
    }

    if (selectionMode) {
      showToast("Select conversations to delete", "info")
    }
  })
}

if (cancelImportBtn) {
  cancelImportBtn.addEventListener("click", () => {
    if (importModal) importModal.classList.remove("open")
  })
}

if (importModal) {
  importModal.addEventListener("click", (e) => {
    if (e.target === importModal) importModal.classList.remove("open")
  })
}

if (importDropzone && importFileInput) {
  importDropzone.addEventListener("click", () => importFileInput.click())

  importDropzone.addEventListener("dragover", (e) => {
    e.preventDefault()
    importDropzone.classList.add("dragover")
  })

  importDropzone.addEventListener("dragleave", () => {
    importDropzone.classList.remove("dragover")
  })

  importDropzone.addEventListener("drop", (e) => {
    e.preventDefault()
    importDropzone.classList.remove("dragover")
    const files = e.dataTransfer.files
    if (files.length > 0) {
      handleImportFile(files[0])
    }
  })

  importFileInput.addEventListener("change", (e) => {
    if (e.target.files.length > 0) {
      handleImportFile(e.target.files[0])
      e.target.value = ""
    }
  })
}

async function handleImportFile(file) {
  if (!file.name.endsWith(".json")) {
    alert("Please import a JSON file exported from AI Note Taker")
    return
  }

  const formData = new FormData()
  formData.append("file", file)

  try {
    const result = await window.api.importConversations(formData)
    if (result.error) {
      alert("Import failed: " + result.error)
      return
    }

    // Save imported messages as a new conversation
    if (result.messages && result.messages.length > 0) {
      const title = result.messages[0]?.text?.substring(0, 50) || "Imported Conversation"
      await window.api.conversationSave({
        id: crypto.randomUUID(),
        title: title,
        messages: result.messages,
        createdAt: Date.now(),
        updatedAt: Date.now()
      })

      // Refresh history
      renderHistoryList()

      alert(`Imported ${result.count} messages successfully`)
      if (importModal) importModal.classList.remove("open")
    }
  } catch (e) {
    console.error("Import error:", e)
    alert("Import failed")
  }
}

// ==============================
// EDITABLE SUMMARIES
// ==============================
function makeSummaryEditable(summaryBlock) {
  if (!summaryBlock) return

  const content = summaryBlock.querySelector(".summary-block-content")
  const titleBar = summaryBlock.querySelector(".summary-block-title")

  // Add edit button if not present
  if (!summaryBlock.querySelector(".summary-edit-btn")) {
    const editBtn = document.createElement("button")
    editBtn.className = "summary-edit-btn"
    editBtn.textContent = "Edit"
    editBtn.addEventListener("click", () => startEditing(summaryBlock, content, titleBar))
    titleBar.appendChild(editBtn)
  }
}

function startEditing(summaryBlock, content, titleBar) {
  summaryBlock.classList.add("editable")
  content.contentEditable = "true"
  content.focus()

  // Replace edit button with save/cancel
  const editBtn = titleBar.querySelector(".summary-edit-btn")
  if (editBtn) editBtn.style.display = "none"

  const copyBtn = titleBar.querySelector(".summary-copy-btn")
  if (copyBtn) copyBtn.style.display = "none"

  const actions = document.createElement("div")
  actions.className = "summary-edit-actions"
  actions.innerHTML = `
    <button class="summary-save-btn">Save</button>
    <button class="summary-cancel-btn">Cancel</button>
  `

  actions.querySelector(".summary-save-btn").addEventListener("click", () => {
    saveSummaryEdit(summaryBlock, content, titleBar, actions)
  })

  actions.querySelector(".summary-cancel-btn").addEventListener("click", () => {
    cancelSummaryEdit(summaryBlock, content, titleBar, actions)
  })

  summaryBlock.appendChild(actions)
}

function saveSummaryEdit(summaryBlock, content, titleBar, actions) {
  const editedText = content.innerText

  // Update the stored summary if exists
  const existing = document.querySelector(".summary-block")
  if (existing) {
    existing.dataset.editedContent = editedText
  }

  // Save to conversation
  if (currentConversationId) {
    window.api.conversationLoad(currentConversationId).then(conv => {
      if (conv) {
        conv.summary = editedText
        conv.summaryEdited = true
        window.api.conversationSave(conv)
      }
    })
  }

  // Clean up editing state
  content.contentEditable = "false"
  summaryBlock.classList.remove("editable")
  actions.remove()

  // Restore buttons
  const editBtn = titleBar.querySelector(".summary-edit-btn")
  if (editBtn) editBtn.style.display = ""
  const copyBtn = titleBar.querySelector(".summary-copy-btn")
  if (copyBtn) copyBtn.style.display = ""
}

function cancelSummaryEdit(summaryBlock, content, titleBar, actions) {
  // Restore original content
  const existing = summaryBlock.dataset.originalContent
  if (existing) {
    content.innerHTML = existing
  }

  content.contentEditable = "false"
  summaryBlock.classList.remove("editable")
  actions.remove()

  // Restore buttons
  const editBtn = titleBar.querySelector(".summary-edit-btn")
  if (editBtn) editBtn.style.display = ""
  const copyBtn = titleBar.querySelector(".summary-copy-btn")
  if (copyBtn) copyBtn.style.display = ""
}

// Extend summarize button to make summaries editable
const originalSummarizeBtn = summarizeBtn
if (originalSummarizeBtn) {
  originalSummarizeBtn.addEventListener("click", () => {
    // Wait for summary to be generated
    setTimeout(() => {
      const summaryBlock = document.querySelector(".summary-block")
      if (summaryBlock) {
        // Store original content
        const content = summaryBlock.querySelector(".summary-block-content")
        if (content) {
          summaryBlock.dataset.originalContent = content.innerHTML
        }
        makeSummaryEditable(summaryBlock)
      }
    }, 500)
  }, true) // Use capture to run before existing handler
}

// ==============================
// SESSION TIMER
// ==============================
function startSessionTimer() {
  sessionStartTime = Date.now()
  sessionDurationMinutes = 0

  // Create timer display if not exists
  let timerDisplay = document.getElementById("sessionTimer")
  if (!timerDisplay) {
    timerDisplay = document.createElement("div")
    timerDisplay.id = "sessionTimer"
    timerDisplay.className = "session-timer"

    // Insert into header
    const header = document.querySelector(".header-center")
    if (header) {
      header.appendChild(timerDisplay)
    }
  }

  updateSessionTimer()
  sessionTimerInterval = setInterval(updateSessionTimer, 60000) // Update every minute
}

function stopSessionTimer() {
  if (sessionTimerInterval) {
    clearInterval(sessionTimerInterval)
    sessionTimerInterval = null
  }
  sessionStartTime = null

  const timerDisplay = document.getElementById("sessionTimer")
  if (timerDisplay) {
    timerDisplay.remove()
  }
}

function updateSessionTimer() {
  if (!sessionStartTime) return

  const elapsed = Math.floor((Date.now() - sessionStartTime) / 60000)
  sessionDurationMinutes = elapsed

  const timerDisplay = document.getElementById("sessionTimer")
  if (timerDisplay) {
    const hours = Math.floor(elapsed / 60)
    const mins = elapsed % 60
    const timeStr = hours > 0 ? `${hours}h ${mins}m` : `${mins}m`

    timerDisplay.innerHTML = `
      <span>&#9201;</span>
      <span>${timeStr}</span>
    `

    // Add warning styling and extension button
    timerDisplay.classList.remove("warning", "danger")
    if (elapsed >= SESSION_MAX_DURATION) {
      timerDisplay.classList.add("danger")
      // Auto-stop recording at max duration
      if (isListening) {
        stopListening()
        addErrorMessage(`Recording stopped after ${SESSION_MAX_DURATION} minutes`)
      }
    } else if (elapsed >= SESSION_WARNING_THRESHOLD) {
      timerDisplay.classList.add("warning")
      // Show extend button if not already shown
      if (!document.getElementById("sessionExtendBtn")) {
        const extendBtn = document.createElement("button")
        extendBtn.id = "sessionExtendBtn"
        extendBtn.className = "session-extend-btn"
        extendBtn.innerHTML = "+30m"
        extendBtn.title = "Extend session by 30 minutes"
        extendBtn.onclick = () => {
          extendSessionTimer(30)
        }
        timerDisplay.appendChild(extendBtn)
      }
    }
  }
}

function extendSessionTimer(additionalMinutes) {
  // Adjust thresholds to extend session
  SESSION_MAX_DURATION += additionalMinutes
  SESSION_WARNING_THRESHOLD += additionalMinutes
  showToast(`Session extended by ${additionalMinutes} minutes`)

  // Remove the extend button after clicking
  const extendBtn = document.getElementById("sessionExtendBtn")
  if (extendBtn) {
    extendBtn.remove()
  }

  // Reset timer display styling
  const timerDisplay = document.getElementById("sessionTimer")
  if (timerDisplay) {
    timerDisplay.classList.remove("warning")
  }
}

// Extend startListening to include session timer
const originalStartListening = listenBtn?.onclick
if (listenBtn) {
  listenBtn.addEventListener("click", () => {
    if (!isListening) {
      startSessionTimer()
    } else {
      stopSessionTimer()
    }
  })
}

// ==============================
// SALES OBJECTION HANDLING
// ==============================
function createObjectionToggle() {
  const btn = document.createElement("button")
  btn.className = "objection-toggle-btn"
  btn.id = "objectionToggleBtn"
  btn.innerHTML = `
    <span>&#128161;</span>
    <span>Sales</span>
  `
  btn.title = "Toggle sales objection detection"
  btn.addEventListener("click", () => {
    objectionDetectionEnabled = !objectionDetectionEnabled
    btn.classList.toggle("active", objectionDetectionEnabled)
    window.api.storeSet("objectionDetectionEnabled", objectionDetectionEnabled)
    if (objectionDetectionEnabled) {
      showToast("Sales objection detection enabled")
    }
  })
  return btn
}

async function checkForObjections(text) {
  if (!objectionDetectionEnabled || !text) return

  try {
    const result = await window.api.detectObjections(text)
    if (result.objections && result.objections.length > 0) {
      showObjectionBanner(result.objections[0])
    }
  } catch (e) {
    console.error("Objection detection error:", e)
  }
}

function showObjectionBanner(objection) {
  // Remove existing banner
  const existing = document.querySelector(".objection-banner")
  if (existing) existing.remove()

  const banner = document.createElement("div")
  banner.className = "objection-banner"
  banner.innerHTML = `
    <div class="objection-title">${escapeHtml(objection.title)}</div>
    <div class="objection-suggestions">
      ${objection.suggestions.map(s => `<button class="objection-suggestion">${escapeHtml(s)}</button>`).join("")}
    </div>
  `

  // Add click handlers for suggestions
  banner.querySelectorAll(".objection-suggestion").forEach(btn => {
    btn.addEventListener("click", () => {
      // Copy suggestion to clipboard
      window.api.copyToClipboard(btn.textContent)
      showToast("Response copied to clipboard")
      banner.classList.add("fade-out")
      setTimeout(() => banner.remove(), 300)
    })
  })

  document.body.appendChild(banner)

  // Auto-remove after 15 seconds
  setTimeout(() => {
    if (banner.parentNode) {
      banner.classList.add("fade-out")
      setTimeout(() => banner.remove(), 300)
    }
  }, 15000)
}

// Add objection toggle to controls
function initObjectionToggle() {
  const controlsStrip = document.querySelector(".controls-strip")
  if (!controlsStrip || document.getElementById("objectionToggleBtn")) return

  const btn = createObjectionToggle()
  controlsStrip.appendChild(btn)

  // Load saved setting
  window.api.storeGet("objectionDetectionEnabled").then(enabled => {
    objectionDetectionEnabled = enabled === true
    btn.classList.toggle("active", objectionDetectionEnabled)
  })
}

// Check for objections when messages are added
const originalStreamMessage = streamMessage
streamMessage = window.streamMessage = function(role, text, opts = {}) {
  const result = originalStreamMessage(role, text, opts)
  if (role === "user" && text) {
    checkForObjections(text)
  }
  return result
}

// ==============================
// ANALYTICS
// ==============================
const analyticsPreview = document.getElementById("analyticsPreview")
const viewAnalyticsBtn = document.getElementById("viewAnalyticsBtn")
const exportAnalyticsBtn = document.getElementById("exportAnalyticsBtn")
const analyticsModal = document.getElementById("analyticsModal")
const closeAnalyticsBtn = document.getElementById("closeAnalyticsBtn")

async function loadAnalyticsPreview() {
  if (!analyticsPreview) return
  try {
    const summary = await window.api.getAnalyticsSummary(30)
    if (summary.total_conversations === 0) {
      analyticsPreview.innerHTML = `<div class="document-empty">No conversations yet. Start talking!</div>`
      return
    }
    analyticsPreview.innerHTML = `
      <div class="analytics-mini-stats">
        <div class="analytics-mini-stat">
          <div class="analytics-mini-value">${summary.total_conversations}</div>
          <div class="analytics-mini-label">Conversations</div>
        </div>
        <div class="analytics-mini-stat">
          <div class="analytics-mini-value">${summary.total_messages}</div>
          <div class="analytics-mini-label">Messages</div>
        </div>
        <div class="analytics-mini-stat">
          <div class="analytics-mini-value">${summary.avg_conversation_duration_minutes}m</div>
          <div class="analytics-mini-label">Avg Duration</div>
        </div>
        <div class="analytics-mini-stat">
          <div class="analytics-mini-value">${summary.speaker_ratio}:1</div>
          <div class="analytics-mini-label">User/AI Ratio</div>
        </div>
      </div>`
  } catch (e) {
    analyticsPreview.innerHTML = `<div class="document-empty">Failed to load analytics</div>`
  }
}

async function showAnalyticsModal() {
  if (!analyticsModal) return
  analyticsModal.classList.add("open")
  try {
    const summary = await window.api.getAnalyticsSummary(30)
    document.getElementById("analyticsTotalConversations").textContent = summary.total_conversations
    document.getElementById("analyticsTotalMessages").textContent = summary.total_messages
    document.getElementById("analyticsAvgDuration").textContent = summary.avg_conversation_duration_minutes + "m"
    document.getElementById("analyticsSpeakerRatio").textContent = summary.speaker_ratio + ":1"

    const container = document.querySelector(".analytics-chart-bars")
    if (container && summary.daily_trend) {
      const maxMessages = Math.max(...summary.daily_trend.map(d => d.messages), 1)
      container.innerHTML = summary.daily_trend.map(day => {
        const heightPercent = (day.messages / maxMessages) * 100
        const dateLabel = new Date(day.date).toLocaleDateString("en-US", { weekday: "short" })
        return `<div class="analytics-chart-bar" style="height: ${Math.max(heightPercent, 4)}%">
          <span class="analytics-chart-bar-value">${day.messages}</span>
          <span class="analytics-chart-bar-label">${dateLabel}</span>
        </div>`
      }).join("")
    }
  } catch (e) {
    console.error("Analytics error:", e)
  }
}

if (viewAnalyticsBtn) viewAnalyticsBtn.addEventListener("click", showAnalyticsModal)
if (closeAnalyticsBtn) closeAnalyticsBtn.addEventListener("click", () => analyticsModal?.classList.remove("open"))
if (analyticsModal) analyticsModal.addEventListener("click", (e) => { if (e.target === analyticsModal) analyticsModal.classList.remove("open") })

// Back buttons for modals
const backShortcutsModal = document.getElementById("backShortcutsModal")
const backAnalyticsModal = document.getElementById("backAnalyticsModal")
const backAboutModal = document.getElementById("backAboutModal")
const backExportModal = document.getElementById("backExportModal")
const backImportModal = document.getElementById("backImportModal")

if (backShortcutsModal) backShortcutsModal.addEventListener("click", () => shortcutsModal?.classList.remove("open"))
if (backAnalyticsModal) backAnalyticsModal.addEventListener("click", () => analyticsModal?.classList.remove("open"))
if (backAboutModal) backAboutModal.addEventListener("click", () => aboutModal?.classList.remove("open"))
if (backExportModal) backExportModal.addEventListener("click", closeExportModal)
if (backImportModal) backImportModal.addEventListener("click", () => importModal?.classList.remove("open"))

// ==============================
// CUSTOM DROPDOWNS HELPERS
// ==============================
function initCustomDropdown(triggerId, menuId, textId, hiddenInputId, onChange) {
  const trigger = document.getElementById(triggerId)
  const menu = document.getElementById(menuId)
  const text = document.getElementById(textId)
  const hidden = document.getElementById(hiddenInputId)
  if (!trigger || !menu) return

  trigger.addEventListener("click", (e) => {
    e.stopPropagation()
    const isOpen = menu.classList.contains("open")
    // Close all other custom dropdowns
    document.querySelectorAll(".custom-dropdown-menu.open").forEach(m => {
      if (m !== menu) m.classList.remove("open")
    })
    document.querySelectorAll(".custom-dropdown-trigger.active").forEach(t => {
      if (t !== trigger) t.classList.remove("active")
    })
    if (isOpen) {
      menu.classList.remove("open")
      trigger.classList.remove("active")
    } else {
      // Compute fixed position so menu escapes overflow clipping of scrollable parents
      const rect = trigger.getBoundingClientRect()
      const panelRect = settingsPanel ? settingsPanel.getBoundingClientRect() : { left: 0, right: window.innerWidth }
      const menuMaxWidth = Math.min(320, panelRect.right - rect.left - 8)
      menu.style.setProperty("--dropdown-width", menuMaxWidth + "px")
      menu.style.top = (rect.bottom + 4) + "px"
      menu.style.left = rect.left + "px"
      menu.classList.add("open")
      trigger.classList.add("active")
    }
  })

  menu.querySelectorAll(".custom-dropdown-item").forEach(item => {
    item.addEventListener("click", () => {
      const value = item.dataset.value
      const label = item.textContent
      if (hidden) hidden.value = value
      if (text) text.textContent = label
      menu.classList.remove("open")
      trigger.classList.remove("active")
      // Update selected styling
      menu.querySelectorAll(".custom-dropdown-item").forEach(i => i.classList.remove("selected"))
      item.classList.add("selected")
      if (onChange) onChange(value, label)
    })
  })
}

// Close custom dropdowns when clicking outside
document.addEventListener("click", () => {
  document.querySelectorAll(".custom-dropdown-menu.open").forEach(m => m.classList.remove("open"))
  document.querySelectorAll(".custom-dropdown-trigger.active").forEach(t => t.classList.remove("active"))
})

// ==============================
// CRM INTEGRATION
// ==============================
const crmProviderSelect = document.getElementById("crmProviderSelect")
const crmProviderText = document.getElementById("crmProviderText")
const crmProviderMenu = document.getElementById("crmProviderMenu")
const crmSaveBtn = document.getElementById("crmSaveBtn")
const crmTestBtn = document.getElementById("crmTestBtn")
const crmStatus = document.getElementById("crmStatus")

const crmProviderLabels = { "": "Disabled", "webhook": "Webhook", "salesforce": "Salesforce", "hubspot": "HubSpot" }

function updateCRMFields() {
  const provider = crmProviderSelect?.value
  document.querySelectorAll(".crm-field-group").forEach(g => g.style.display = g.dataset.provider === provider ? "block" : "none")
  const crmOptions = document.getElementById("crmOptions")
  if (crmOptions) crmOptions.style.display = provider ? "block" : "none"
}

async function loadCRMConfig() {
  try {
    const config = await window.api.getCRMConfig()
    if (crmProviderSelect) crmProviderSelect.value = config.provider || ""
    if (crmProviderText) crmProviderText.textContent = crmProviderLabels[config.provider] || "Disabled"
    if (crmProviderMenu) {
      crmProviderMenu.querySelectorAll(".custom-dropdown-item").forEach(i => {
        i.classList.toggle("selected", i.dataset.value === (config.provider || ""))
      })
    }
    if (document.getElementById("crmWebhookUrl")) document.getElementById("crmWebhookUrl").value = config.webhook_url || ""
    if (document.getElementById("crmSalesforceUrl")) document.getElementById("crmSalesforceUrl").value = config.instance_url || ""
    if (document.getElementById("crmSalesforceToken")) document.getElementById("crmSalesforceToken").value = config.oauth_token || ""
    if (document.getElementById("crmHubspotKey")) document.getElementById("crmHubspotKey").value = config.api_key || ""
    updateCRMFields()
  } catch (e) { console.error("CRM load error:", e) }
}

async function saveCRMConfig() {
  const config = {
    enabled: !!crmProviderSelect?.value,
    provider: crmProviderSelect?.value || "",
    webhook_url: document.getElementById("crmWebhookUrl")?.value || null,
    instance_url: document.getElementById("crmSalesforceUrl")?.value || null,
    oauth_token: document.getElementById("crmSalesforceToken")?.value || null,
    api_key: document.getElementById("crmHubspotKey")?.value || null,
    auto_log_conversations: document.getElementById("crmAutoLog")?.checked ?? true,
    contact_matching: document.getElementById("crmContactMatch")?.checked ?? true,
    log_format: document.getElementById("crmLogFormat")?.value || "summary"
  }
  try {
    await window.api.saveCRMConfig(config)
    if (crmStatus) { crmStatus.textContent = "Configuration saved"; crmStatus.className = "crm-status ok" }
  } catch (e) {
    if (crmStatus) { crmStatus.textContent = "Save failed"; crmStatus.className = "crm-status error" }
  }
}

// Init custom CRM dropdown
initCustomDropdown("crmProviderTrigger", "crmProviderMenu", "crmProviderText", "crmProviderSelect", (value) => {
  updateCRMFields()
})
if (crmSaveBtn) crmSaveBtn.addEventListener("click", saveCRMConfig)

// ==============================
// CLOUD MODEL CUSTOM DROPDOWN
// ==============================
const cloudModelText = document.getElementById("cloudModelText")
const cloudModelMenu = document.getElementById("cloudModelMenu")

initCustomDropdown("cloudModelTrigger", "cloudModelMenu", "cloudModelText", "cloudModelSelect", async (value) => {
  await window.api.storeSet("cloudModel", value)
  // Sync toolbar model select
  if (modelSelect) modelSelect.value = value
  updateActiveProviders()
})

// ==============================
// INITIALIZATION
// ==============================
async function initFeatures() {
  await loadDocuments()
  initSpeakerToggle()
  initObjectionToggle()
  loadAnalyticsPreview()
  loadCRMConfig()
  // Init voice clone after auth (requires API calls)
  initVoiceClone()
  initVoiceCloneRecording()
}

const originalInit = init
init = async function() {
  // Wait for auth before making any API calls
  // Check token exists AND is valid by making a test call
  if (window.AuthHelper) {
    const token = AuthHelper.getToken()
    if (!token) {
      // No token — wait for login
      window.addEventListener('auth-success', async () => {
        await originalInit()
        initFeatures()
      }, { once: true })
      return
    }
    // Token exists — verify it's still valid
    try {
      const testResp = await _originalFetch(`${API_BASE}/health`)
      // health doesn't need auth, but let's test an auth-required endpoint
      const authTest = await _originalFetch(`${API_BASE}/ollama/models`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (authTest.status === 401) {
        // Token expired — clear and wait for re-login
        AuthHelper.clearToken()
        AuthHelper.ensureAuth()
        window.addEventListener('auth-success', async () => {
          await originalInit()
          initFeatures()
        }, { once: true })
        return
      }
    } catch (e) {
      // Backend not ready yet — proceed, it'll retry later
    }
  }
  await originalInit()
  initFeatures()
}

init()

// ==============================
// ANALYTICS AND CRM EXTENSIONS
// ==============================

// ==============================
// REAL-TIME SUGGESTIONS - Phase 2 Task #28
// ==============================

const suggestionsBtn = document.getElementById("suggestionsBtn")
const suggestionsPanel = document.getElementById("suggestionsPanel")
const closeSuggestionsBtn = document.getElementById("closeSuggestionsBtn")
const suggestionsContent = document.getElementById("suggestionsContent")
const confidenceSlider = document.getElementById("confidenceSlider")
const confidenceValue = document.getElementById("confidenceValue")
const clearSuggestionsBtn = document.getElementById("clearSuggestionsBtn")

let suggestionsEnabled = false
let suggestionsCooldown = false
let suggestionHistory = []

// ==============================
// REAL-TIME KEYWORD DETECTION + DYNAMIC ACTION PILLS (Cluely-style)
// ==============================
const QUESTION_INDICATORS = [
  "?", "can you", "how would", "what is", "explain", "tell me", "describe",
  "why", "when", "where", "could you", "would you", "what are", "how do",
  "what's", "how's", "walk me", "help me understand", "what do you think",
  "opinion", "recommend", "suggest", "difference between", "compare"
]

const OBJECTION_KEYWORDS_JS = {
  price: { keywords: ["expensive", "too much", "price", "cost", "budget", "cheap", "afford"], label: "Price objection" },
  competitor: { keywords: ["competitor", "alternative", "vs", "versus", "compare", "better than"], label: "Competitor mention" },
  timing: { keywords: ["not now", "later", "next quarter", "next year", "not ready", "delay"], label: "Timing objection" },
  features: { keywords: ["missing", "doesn't have", "lacks", "require", "need"], label: "Feature gap" },
  security: { keywords: ["security", "privacy", "compliance", "soc2", "gdpr", "hipaa"], label: "Security concern" }
}

let activeDynamicAction = null
let dynamicActionPill = null

function detectKeywords(text, speaker) {
  if (!text || text.length < 15) return

  const lower = text.toLowerCase()

  // Detect questions from interviewer/other speaker
  const isQuestion = QUESTION_INDICATORS.some(ind => lower.includes(ind)) || lower.trim().endsWith("?")
  if (isQuestion && speaker && speaker !== "user") {
    showDynamicAction("Answer: " + text.substring(0, 40) + (text.length > 40 ? "..." : ""), "question", text)
    return
  }

  // Detect objections
  for (const [category, config] of Object.entries(OBJECTION_KEYWORDS_JS)) {
    if (config.keywords.some(kw => lower.includes(kw))) {
      showDynamicAction(config.label, "objection", text)
      return
    }
  }

  // Detect user asking for help (coaching opportunity)
  if (isQuestion && speaker === "user" && lower.length > 20) {
    showDynamicAction("Suggest answer", "coaching", text)
  }
}

function showDynamicAction(label, type, contextText) {
  // Remove existing pill
  removeDynamicAction()

  activeDynamicAction = { label, type, contextText }

  dynamicActionPill = document.createElement("div")
  dynamicActionPill.className = `dynamic-action-pill dynamic-action-${type}`
  dynamicActionPill.innerHTML = `<span class="dynamic-action-label">${escapeHtml(label)}</span><kbd>Tab</kbd>`
  dynamicActionPill.title = "Press Tab to trigger"

  // Insert above the chat input area
  const inputArea = document.querySelector(".chat-input-area") || document.querySelector(".input-area") || textInput?.parentElement
  if (inputArea) {
    inputArea.parentElement.insertBefore(dynamicActionPill, inputArea)
  }

  // Auto-dismiss after 15 seconds
  setTimeout(removeDynamicAction, 15000)
}

function removeDynamicAction() {
  if (dynamicActionPill) {
    dynamicActionPill.remove()
    dynamicActionPill = null
  }
  activeDynamicAction = null
}

async function triggerDynamicAction() {
  if (!activeDynamicAction) return

  const { type, contextText } = activeDynamicAction
  removeDynamicAction()

  if (isProcessing) return

  // Grab latest screenshot
  let screenshotB64 = null
  try {
    screenshotB64 = await window.api.overlayGetLatestScreenshot()
  } catch {}

  let query
  if (screenshotB64) {
    try {
      const ocrResult = await runOcr(screenshotB64)
      const ocrText = (ocrResult.text && ocrResult.text.trim()) ? ocrResult.text.trim() : ""
      query = ocrText
        ? `Screen context: ${ocrText}\n\nDetected ${type}: ${contextText}\n\nProvide a relevant answer based on the screen and conversation.`
        : `Detected ${type}: ${contextText}\n\nProvide a relevant answer.`
    } catch {
      query = `Detected ${type}: ${contextText}\n\nProvide a relevant answer.`
    }
  } else {
    query = `Detected ${type}: ${contextText}\n\nProvide a relevant answer.`
  }

  streamMessage("user", `[${type}]: ${contextText.substring(0, 60)}...`, { hasScreenshot: !!screenshotB64, screenshotB64 })
  const selectedModel = modelSelect ? modelSelect.value : "auto"
  if (selectedModel === "auto") {
    await streamAIRace(query)
  } else {
    await streamAIResponse(query)
  }
}

// Initialize suggestions feature
function initSuggestions() {
  if (!suggestionsBtn) return

  // Show button (hidden by default until Phase 2 is ready)
  suggestionsBtn.style.display = "inline-flex"

  // Toggle panel
  suggestionsBtn.addEventListener("click", () => {
    suggestionsEnabled = !suggestionsEnabled
    suggestionsBtn.classList.toggle("active", suggestionsEnabled)
    suggestionsPanel.style.display = suggestionsEnabled ? "flex" : "none"

    if (suggestionsEnabled) {
      // Clear suggestions when opening
      clearSuggestionsState()
      showSuggestionsMessage("Listening for interview questions...")
    }
  })

  // Close panel
  closeSuggestionsBtn?.addEventListener("click", () => {
    suggestionsEnabled = false
    suggestionsBtn.classList.remove("active")
    suggestionsPanel.style.display = "none"
  })

  // Confidence slider
  confidenceSlider?.addEventListener("input", (e) => {
    const value = e.target.value
    confidenceValue.textContent = value + "%"
    updateSuggestionConfig(value / 100)
  })

  // Clear history
  clearSuggestionsBtn?.addEventListener("click", () => {
    clearSuggestionsState()
    showSuggestionsMessage("History cleared. Listening for questions...")
  })
}

// ==============================
// AI AGENTS FRAMEWORK (v2)
// ==============================

let agentSessionId = null
let agentEventSource = null
let agentSessionType = "meeting"  // "interview", "sales_call", "meeting"
let activeAgentTypes = ["interview_coach", "meeting", "sales_coach"]
let agentSuggestionsEnabled = true
// Speaker diarization state — updated by WebSocket messages
let lastDetectedSpeaker = "Speaker 1"  // Raw diarizer label
let lastSpeakerRole = "user"            // Semantic role (user/interviewer/other)

// Initialize agent session
async function initAgentSession(sessionType = "meeting", company = "", role = "") {
  try {
    const response = await fetch(`${API_BASE}/agents/sessions?session_type=${encodeURIComponent(sessionType)}&active_agents=${encodeURIComponent(activeAgentTypes.join(","))}&company=${encodeURIComponent(company)}&role=${encodeURIComponent(role)}`, {
      method: "POST"
    })
    const data = await response.json()
    if (data.id) {
      agentSessionId = data.id
      agentSessionType = sessionType
      console.log(`[Agents] Session created: ${data.id.substring(0, 8)} type=${sessionType} agents=${activeAgentTypes.join(",")}`)
      // Connect SSE stream
      connectAgentStream(data.id)
      return data
    }
  } catch (error) {
    console.error("[Agents] Failed to create session:", error)
  }
  return null
}

// Connect SSE stream for real-time agent suggestions
function connectAgentStream(sessionId) {
  if (agentEventSource) {
    agentEventSource.close()
  }
  // SSE will be connected when segments are processed
  // The streaming endpoint is: /agents/sessions/{id}/stream
}

// Process transcript for suggestions — AGENT FRAMEWORK (v2)
// Falls back to old /realtime/process if agents unavailable
// Speaker info comes from the StreamingDiarizer (VibeVoice-ASR or fallback)
async function processTranscriptForSuggestions(text, speaker) {
  if (!suggestionsEnabled || !text || text.length < 10) return

  // Use detected speaker from diarizer if available, otherwise use the passed speaker
  // The orchestrator normalizes all speaker labels to user/interviewer/other
  const effectiveSpeaker = speaker || lastDetectedSpeaker || "Speaker 1"

  // Don't process during cooldown
  if (suggestionsCooldown) return

  // Try new agent framework first
  if (agentSessionId && agentSuggestionsEnabled) {
    try {
      const response = await fetch(`${API_BASE}/agents/sessions/${agentSessionId}/segment?text=${encodeURIComponent(text)}&speaker=${encodeURIComponent(effectiveSpeaker)}`, {
        method: "POST"
      })
      const data = await response.json()

      if (data.suggestions && data.suggestions.length > 0) {
        data.suggestions.forEach(suggestion => {
          displayAgentSuggestion(suggestion)
          suggestionHistory.push(suggestion)
        })

        // Set cooldown (shorter for multi-agent)
        suggestionsCooldown = true
        setTimeout(() => { suggestionsCooldown = false }, 8000)
        return
      }
      // If no suggestions, try old system as fallback
    } catch (error) {
      console.warn("[Agents] Agent framework error, falling back to realtime:", error)
    }
  }

  // Fallback to old realtime suggestions
  try {
    const response = await fetch(`${API_BASE}/realtime/process?text=${encodeURIComponent(text)}&speaker=${encodeURIComponent(effectiveSpeaker)}`)
    const data = await response.json()

    if (data.has_suggestion && data.suggestion) {
      displaySuggestion(data.suggestion)
      suggestionHistory.push(data.suggestion)

      // Set cooldown
      suggestionsCooldown = true
      setTimeout(() => {
        suggestionsCooldown = false
      }, 10000)
    }
  } catch (error) {
    console.error("[Suggestions] Error processing transcript:", error)
  }
}

// Display an agent suggestion (multi-agent aware)
function displayAgentSuggestion(suggestion) {
  if (!suggestionsContent) return

  const agentType = suggestion.agent_type || "interview_coach"
  const agentLabels = {
    interview_coach: "Interview Coach",
    meeting: "Meeting Notes",
    sales_coach: "Sales Coach"
  }
  const agentLabel = agentLabels[agentType] || agentType
  const categoryLabels = {
    technical: "Technical",
    behavioral: "Behavioral",
    clarification: "Clarify",
    strategic: "Strategy",
    stalling: "Stall",
    action_item: "Action Item",
    decision: "Decision",
    question: "Open Question",
    objection: "Objection",
    rebuttal: "Rebuttal",
    talking_point: "Talking Point",
    general: "Note"
  }

  const card = document.createElement("div")
  card.className = `suggestion-card agent-${agentType} ${suggestion.confidence >= 0.8 ? 'high-confidence' : ''}`
  card.dataset.suggestionId = suggestion.id
  card.dataset.agentType = agentType
  card.innerHTML = `
    <div class="suggestion-header">
      <span class="agent-type-badge ${agentType}">${agentLabel}</span>
      <span class="suggestion-category">${categoryLabels[suggestion.category] || suggestion.category}</span>
      <span class="suggestion-confidence">${Math.round(suggestion.confidence * 100)}%</span>
    </div>
    <div class="suggestion-content">${formatSuggestionContent(suggestion.content)}</div>
    <div class="suggestion-actions">
      <button class="accept-suggestion-btn" data-id="${suggestion.id}">Accept</button>
      <button class="dismiss-suggestion-btn" data-id="${suggestion.id}">Dismiss</button>
    </div>
  `

  // Wire up accept/dismiss buttons
  card.querySelector(".accept-suggestion-btn")?.addEventListener("click", () => {
    acceptAgentSuggestion(suggestion.id)
    card.classList.add("accepted")
    setTimeout(() => card.remove(), 500)
  })
  card.querySelector(".dismiss-suggestion-btn")?.addEventListener("click", () => {
    dismissAgentSuggestion(suggestion.id)
    card.classList.add("dismissed")
    setTimeout(() => card.remove(), 300)
  })

  // Insert at top
  suggestionsContent.insertBefore(card, suggestionsContent.firstChild)

  // Remove empty state
  const emptyState = suggestionsContent.querySelector('.suggestions-empty')
  if (emptyState) emptyState.remove()

  // Limit to 15 suggestions
  const cards = suggestionsContent.querySelectorAll('.suggestion-card')
  if (cards.length > 15) cards[cards.length - 1].remove()

  // Show notification dot
  const dot = document.getElementById("suggestionsDot")
  if (dot) {
    dot.style.display = "block"
    setTimeout(() => { dot.style.display = "none" }, 3000)
  }
}

// Accept an agent suggestion — records feedback for self-learning
async function acceptAgentSuggestion(suggestionId) {
  try {
    const response = await fetch(`${API_BASE}/agents/suggestions/${suggestionId}/accept`, { method: "POST" })
    console.log(`[Agents] Accepted suggestion: ${suggestionId}`)
    // Visual feedback: mark the card as accepted
    const card = document.querySelector(`[data-suggestion-id="${suggestionId}"]`)
    if (card) {
      card.classList.add("accepted")
      card.classList.remove("dismissed")
      const actions = card.querySelector(".suggestion-actions")
      if (actions) actions.innerHTML = '<span class="suggestion-accepted-label">Accepted</span>'
    }
  } catch (error) {
    console.error("[Agents] Accept error:", error)
  }
}

// Dismiss an agent suggestion — records feedback for self-learning
async function dismissAgentSuggestion(suggestionId) {
  try {
    const response = await fetch(`${API_BASE}/agents/suggestions/${suggestionId}/dismiss`, { method: "POST" })
    console.log(`[Agents] Dismissed suggestion: ${suggestionId}`)
    // Visual feedback: mark the card as dismissed and fade it out
    const card = document.querySelector(`[data-suggestion-id="${suggestionId}"]`)
    if (card) {
      card.classList.add("dismissed")
      card.classList.remove("accepted")
      card.style.transition = "opacity 0.3s ease"
      card.style.opacity = "0.5"
      setTimeout(() => { card.style.display = "none" }, 2000)
    }
  } catch (error) {
    console.error("[Agents] Dismiss error:", error)
  }
}

// End agent session
async function endAgentSession() {
  if (!agentSessionId) return
  try {
    await fetch(`${API_BASE}/agents/sessions/${agentSessionId}/end`, { method: "POST" })
    console.log(`[Agents] Session ended: ${agentSessionId.substring(0, 8)}`)
  } catch (error) {
    console.error("[Agents] End session error:", error)
  }
  agentSessionId = null
  if (agentEventSource) {
    agentEventSource.close()
    agentEventSource = null
  }
}

// Toggle agent types
async function setActiveAgents(agents) {
  if (!agentSessionId) return
  activeAgentTypes = agents
  try {
    await fetch(`${API_BASE}/agents/sessions/${agentSessionId}/agents?active_agents=${encodeURIComponent(agents.join(","))}`, {
      method: "POST"
    })
    console.log(`[Agents] Active agents updated: ${agents.join(", ")}`)
  } catch (error) {
    console.error("[Agents] Update agents error:", error)
  }
}

// ==============================
// END AI AGENTS FRAMEWORK (v2)
// ==============================

// Format suggestion content for display
function formatSuggestionContent(content) {
  // Convert markdown-style bold to HTML
  return content.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>').replace(/\n/g, '<br>')
}

// Display a suggestion card (old format, for /realtime/process fallback)
function displaySuggestion(suggestion) {
  if (!suggestionsContent) return

  const card = document.createElement("div")
  card.className = `suggestion-card ${suggestion.confidence >= 0.8 ? 'high-confidence' : ''}`
  card.innerHTML = `
    <div class="suggestion-header">
      <span class="suggestion-type">${(suggestion.type || 'general').replace('_', ' ')}</span>
      <span class="suggestion-confidence">${Math.round((suggestion.confidence || 0) * 100)}%</span>
    </div>
    <div class="suggestion-content">${formatSuggestionContent(suggestion.content)}</div>
    ${suggestion.context?.company ? `
      <div class="suggestion-meta">
        From: ${suggestion.context.company} interview
        ${suggestion.context.topics ? `• Topics: ${suggestion.context.topics.slice(0, 3).join(', ')}` : ''}
      </div>
    ` : ''}
  `

  // Insert at top
  suggestionsContent.insertBefore(card, suggestionsContent.firstChild)

  // Remove empty state if present
  const emptyState = suggestionsContent.querySelector('.suggestions-empty')
  if (emptyState) emptyState.remove()

  // Limit to 10 suggestions
  const cards = suggestionsContent.querySelectorAll('.suggestion-card')
  if (cards.length > 10) cards[cards.length - 1].remove()

  // Show notification dot on button
  const dot = document.getElementById("suggestionsDot")
  if (dot) {
    dot.style.display = "block"
    setTimeout(() => { dot.style.display = "none" }, 3000)
  }
}

// Show message in suggestions panel
function showSuggestionsMessage(message) {
  if (!suggestionsContent) return
  suggestionsContent.innerHTML = `<div class="suggestions-empty">${message}</div>`
}

// Clear suggestions state
function clearSuggestionsState() {
  suggestionHistory = []
  if (suggestionsContent) {
    suggestionsContent.innerHTML = ''
  }
  // Call API to clear server state
  fetch(`${API_BASE}/realtime/clear`, { method: 'POST' }).catch(console.error)
}

// Update suggestion config on server
async function updateSuggestionConfig(confidence) {
  try {
    await fetch(`${API_BASE}/realtime/configure?min_confidence=${confidence}`, {
      method: 'POST'
    })
  } catch (error) {
    console.error("[Suggestions] Error updating config:", error)
  }
}

// Voice command handler
async function processVoiceCommand(text) {
  if (!text.toLowerCase().startsWith("hey ant") && !text.toLowerCase().startsWith("okay ant")) {
    return null
  }

  try {
    const response = await fetch(`${API_BASE}/realtime/command?text=${encodeURIComponent(text)}`)
    const data = await response.json()

    if (data.is_command) {
      // Open suggestions panel if command found something
      if (!suggestionsEnabled) {
        suggestionsEnabled = true
        suggestionsBtn?.classList.add("active")
        suggestionsPanel.style.display = "flex"
      }

      // Display results
      if (data.action === "search_results") {
        showSuggestionsMessage(`Found ${data.data.results?.length || 0} results for "${data.data.query}"`)
        // Could display results here
      } else if (data.action === "suggestion") {
        displaySuggestion(data.data.suggestion)
      }

      return data
    }
  } catch (error) {
    console.error("[Suggestions] Voice command error:", error)
  }

  return null
}

// Initialize
initSuggestions()
console.log("[Suggestions] Phase 2 feature initialized")

// ==============================
// COMPLEXITY ANALYSIS BADGE
// ==============================

const complexityPatterns = {
  'O(1)': { pattern: /constant time|O\(1\)/i, badge: '● O(1)', color: '#22c55e', desc: 'Constant time' },
  'O(log n)': { pattern: /logarithmic|binary search|O\(log n\)/i, badge: '● O(log n)', color: '#22c55e', desc: 'Logarithmic time' },
  'O(n)': { pattern: /linear time|single pass|O\(n\)(?!\^|\w)/i, badge: '● O(n)', color: '#22c55e', desc: 'Linear time' },
  'O(n log n)': { pattern: /n log n|O\(n log n\)|merge sort|heap sort|quick sort.*average/i, badge: '● O(n log n)', color: '#eab308', desc: 'Linearithmic time' },
  'O(n²)': { pattern: /quadratic|nested loop|bubble sort|O\(n\^2\)|O\(n²\)/i, badge: '● O(n²)', color: '#eab308', desc: 'Quadratic time' },
  'O(2^n)': { pattern: /exponential|recursive.*tree|fibonacci recursive|O\(2\^n\)/i, badge: '● O(2ⁿ)', color: '#ef4444', desc: 'Exponential time' },
  'O(n!)': { pattern: /factorial|permutations|O\(n!\)/i, badge: '● O(n!)', color: '#ef4444', desc: 'Factorial time' }
}

function analyzeComplexity(text) {
  if (!text) return null

  const found = []
  for (const [complexity, config] of Object.entries(complexityPatterns)) {
    if (config.pattern.test(text)) {
      found.push({ complexity, ...config })
    }
  }

  // Return the worst complexity found (highest order)
  if (found.length > 0) {
    const order = ['O(1)', 'O(log n)', 'O(n)', 'O(n log n)', 'O(n²)', 'O(2^n)', 'O(n!)']
    const worst = found.sort((a, b) => order.indexOf(b.complexity) - order.indexOf(a.complexity))[0]
    return worst
  }

  return null
}

function showComplexityBadge(analysis, targetElement) {
  if (!analysis || !targetElement) return

  // Remove existing badge
  const existing = targetElement.querySelector('.complexity-badge')
  if (existing) existing.remove()

  const badge = document.createElement('div')
  badge.className = 'complexity-badge'
  badge.innerHTML = `
    <span class="complexity-icon">${analysis.badge.split(' ')[0]}</span>
    <span class="complexity-label">${analysis.badge.split(' ')[1]}</span>
    <span class="complexity-desc">${analysis.desc}</span>
  `
  badge.style.cssText = `
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 10px;
    background: ${analysis.color}20;
    border: 1px solid ${analysis.color};
    border-radius: 6px;
    font-size: 0.75em;
    font-family: monospace;
    color: ${analysis.color};
    margin-top: 8px;
    animation: fade-in 0.3s ease-out;
  `

  targetElement.appendChild(badge)

  // Auto-remove after 30 seconds
  setTimeout(() => {
    if (badge.parentNode) {
      badge.classList.add('fade-out')
      setTimeout(() => badge.remove(), 300)
    }
  }, 30000)
}

// Hook into streamMessage to analyze AI responses
const originalStreamMessageComplexity = streamMessage
streamMessage = window.streamMessage = function(role, text, opts = {}) {
  const element = originalStreamMessageComplexity(role, text, opts)

  // Analyze assistant messages for complexity
  if (role === 'assistant' && text) {
    const analysis = analyzeComplexity(text)
    if (analysis && element) {
      const bubble = element.querySelector('.msg-bubble')
      if (bubble) {
        showComplexityBadge(analysis, bubble)
      }
    }
  }

  return element
}

console.log("[Complexity] Analysis badge feature initialized")

// ==============================
// SCROLL TO BOTTOM BUTTON
// ==============================
const scrollToBottomBtn = document.getElementById("scrollToBottomBtn")

if (scrollToBottomBtn && chatArea) {
  // Show/hide scroll button based on scroll position
  chatArea.addEventListener("scroll", () => {
    const isNearBottom = chatArea.scrollHeight - chatArea.scrollTop - chatArea.clientHeight < 100
    scrollToBottomBtn.classList.toggle("visible", !isNearBottom)
  })

  // Scroll to bottom when clicked
  scrollToBottomBtn.addEventListener("click", () => {
    scrollChat()
  })
}

// ==============================
// WELCOME SUGGESTION CHIPS
// ==============================
const welcomeSuggestionBtns = document.querySelectorAll(".welcome-suggestion-btn")

welcomeSuggestionBtns.forEach(btn => {
  btn.addEventListener("click", () => {
    const prompt = btn.dataset.prompt
    if (prompt && textInput) {
      textInput.value = prompt
      textInput.focus()
      // Trigger input event to resize textarea
      textInput.dispatchEvent(new Event("input"))
    }
  })
})

// ==============================
// VOICE SETTINGS
// ==============================

// Voice configuration
let selectedVoice = null
let voiceRate = 1.2
let voicePitch = 1.0
let voicesLoaded = false
let availableVoices = []

// DOM elements
const voiceSelect = document.getElementById("voiceSelect")
const voiceDropdownTrigger = document.getElementById("voiceDropdownTrigger")
const voiceSelectedText = document.getElementById("voiceSelectedText")
const voiceDropdownMenu = document.getElementById("voiceDropdownMenu")
const voiceRateSlider = document.getElementById("voiceRateSlider")
const voiceRateValue = document.getElementById("voiceRateValue")
const voicePitchSlider = document.getElementById("voicePitchSlider")
const voicePitchValue = document.getElementById("voicePitchValue")
const voiceTestBtn = document.getElementById("voiceTestBtn")
const voiceStatus = document.getElementById("voiceStatus")

// Toggle custom dropdown
function toggleVoiceDropdown() {
  if (!voiceDropdownMenu) return
  const isOpen = voiceDropdownMenu.classList.contains("open")
  if (isOpen) {
    closeVoiceDropdown()
  } else {
    openVoiceDropdown()
  }
}

function openVoiceDropdown() {
  if (!voiceDropdownMenu || !voiceDropdownTrigger) return
  const rect = voiceDropdownTrigger.getBoundingClientRect()
  const panelRect = settingsPanel ? settingsPanel.getBoundingClientRect() : { right: window.innerWidth }
  const menuMaxWidth = Math.min(320, panelRect.right - rect.left - 8)
  voiceDropdownMenu.style.setProperty("--dropdown-width", menuMaxWidth + "px")
  voiceDropdownMenu.style.top = (rect.bottom + 4) + "px"
  voiceDropdownMenu.style.left = rect.left + "px"
  voiceDropdownMenu.classList.add("open")
  voiceDropdownTrigger.classList.add("active")
}

function closeVoiceDropdown() {
  if (!voiceDropdownMenu) return
  voiceDropdownMenu.classList.remove("open")
  if (voiceDropdownTrigger) voiceDropdownTrigger.classList.remove("active")
}

// Build custom dropdown menu
function buildVoiceDropdown(voicesByLang) {
  if (!voiceDropdownMenu) return

  voiceDropdownMenu.innerHTML = ""

  // System Default option
  const defaultItem = document.createElement("div")
  defaultItem.className = "custom-dropdown-item"
  defaultItem.textContent = "System Default"
  defaultItem.dataset.value = ""
  defaultItem.addEventListener("click", () => selectVoice("", "System Default"))
  voiceDropdownMenu.appendChild(defaultItem)

  // English voices first
  if (voicesByLang["en"]) {
    const englishGroup = document.createElement("div")
    englishGroup.className = "custom-dropdown-group"
    englishGroup.textContent = "English"
    voiceDropdownMenu.appendChild(englishGroup)

    voicesByLang["en"].forEach(voice => {
      const item = document.createElement("div")
      item.className = "custom-dropdown-item" + (voice.default ? " default-voice" : "")
      item.textContent = voice.name + (voice.default ? " (Default)" : "")
      item.dataset.value = voice.voiceURI
      item.addEventListener("click", () => selectVoice(voice.voiceURI, voice.name))
      voiceDropdownMenu.appendChild(item)
    })
  }

  // Other languages
  Object.keys(voicesByLang).sort().forEach(lang => {
    if (lang === "en") return
    const langNames = { "es": "Spanish", "fr": "French", "de": "German", "it": "Italian", "pt": "Portuguese", "ja": "Japanese", "ko": "Korean", "zh": "Chinese" }

    const group = document.createElement("div")
    group.className = "custom-dropdown-group"
    group.textContent = langNames[lang] || lang.toUpperCase()
    voiceDropdownMenu.appendChild(group)

    voicesByLang[lang].forEach(voice => {
      const item = document.createElement("div")
      item.className = "custom-dropdown-item"
      item.textContent = voice.name
      item.dataset.value = voice.voiceURI
      item.addEventListener("click", () => selectVoice(voice.voiceURI, voice.name))
      voiceDropdownMenu.appendChild(item)
    })
  })
}

// Select a voice
function selectVoice(voiceURI, voiceName) {
  if (voiceSelect) voiceSelect.value = voiceURI
  if (voiceSelectedText) voiceSelectedText.textContent = voiceName || "System Default"
  selectedVoice = availableVoices.find(v => v.voiceURI === voiceURI)
  closeVoiceDropdown()
  saveVoicePreference()

  // Update selected styling in dropdown
  if (voiceDropdownMenu) {
    voiceDropdownMenu.querySelectorAll(".custom-dropdown-item").forEach(item => {
      item.classList.toggle("selected", item.dataset.value === voiceURI)
    })
  }
}

// Load available voices
function loadVoices() {
  const voices = window.speechSynthesis.getVoices()
  if (voices.length === 0) return

  // Don't reload if already populated
  if (voicesLoaded && availableVoices.length === voices.length) {
    return
  }

  availableVoices = voices
  voicesLoaded = true

  // Group voices by language
  const voicesByLang = {}
  voices.forEach(voice => {
    const lang = voice.lang.split("-")[0]
    if (!voicesByLang[lang]) voicesByLang[lang] = []
    voicesByLang[lang].push(voice)
  })

  // Build custom dropdown
  buildVoiceDropdown(voicesByLang)

  // Load saved preference
  loadVoicePreference()
}

// Load saved voice preference from storage
async function loadVoicePreference() {
  try {
    const saved = await window.api.storeGet("voiceSettings")
    if (saved) {
      if (saved.voiceURI) {
        const voice = availableVoices.find(v => v.voiceURI === saved.voiceURI)
        if (voice) {
          selectVoice(saved.voiceURI, voice.name)
        }
      }
      if (saved.rate !== undefined && voiceRateSlider) {
        voiceRate = saved.rate
        voiceRateSlider.value = saved.rate
        if (voiceRateValue) voiceRateValue.textContent = saved.rate.toFixed(1) + "x"
      }
      if (saved.pitch !== undefined && voicePitchSlider) {
        voicePitch = saved.pitch
        voicePitchSlider.value = saved.pitch
        if (voicePitchValue) voicePitchValue.textContent = saved.pitch.toFixed(1)
      }
    }
  } catch (e) {
    console.error("[Voice] Failed to load preferences:", e)
  }
}

// Save voice preference
async function saveVoicePreference() {
  try {
    const settings = {
      voiceURI: selectedVoice ? selectedVoice.voiceURI : null,
      rate: voiceRate,
      pitch: voicePitch
    }
    await window.api.storeSet("voiceSettings", settings)
  } catch (e) {
    console.error("[Voice] Failed to save preferences:", e)
  }
}

// Get selected voice for TTS
function getSelectedVoice() {
  if (selectedVoice) return selectedVoice
  if (voiceSelect && voiceSelect.value) {
    selectedVoice = availableVoices.find(v => v.voiceURI === voiceSelect.value)
    return selectedVoice
  }
  return null
}

// Initialize voice settings
if (voiceDropdownTrigger) {
  // Load voices when available
  if (window.speechSynthesis) {
    if (window.speechSynthesis.onvoiceschanged !== undefined) {
      window.speechSynthesis.onvoiceschanged = loadVoices
    }
    loadVoices()
  }

  // Toggle dropdown on click
  voiceDropdownTrigger.addEventListener("click", (e) => {
    e.stopPropagation()
    toggleVoiceDropdown()
  })

  // Close dropdown when clicking outside
  document.addEventListener("click", (e) => {
    if (voiceDropdownMenu && !voiceDropdownMenu.contains(e.target) && !voiceDropdownTrigger.contains(e.target)) {
      closeVoiceDropdown()
    }
  })
}

// Handle rate slider
if (voiceRateSlider && voiceRateValue) {
  voiceRateSlider.addEventListener("input", () => {
    voiceRate = parseFloat(voiceRateSlider.value)
    voiceRateValue.textContent = voiceRate.toFixed(1) + "x"
  })

  voiceRateSlider.addEventListener("change", () => {
    saveVoicePreference()
  })
}

// Handle pitch slider
if (voicePitchSlider && voicePitchValue) {
  voicePitchSlider.addEventListener("input", () => {
    voicePitch = parseFloat(voicePitchSlider.value)
    voicePitchValue.textContent = voicePitch.toFixed(1)
  })

  voicePitchSlider.addEventListener("change", () => {
    saveVoicePreference()
  })
}

// Test voice button
if (voiceTestBtn && voiceStatus) {
  voiceTestBtn.addEventListener("click", () => {
    if (window.speechSynthesis.speaking) {
      window.speechSynthesis.cancel()
      voiceStatus.textContent = ""
      voiceTestBtn.innerHTML = "<span>&#127908;</span> Test Voice"
      return
    }

    const testText = "This is a test of the selected voice. The quick brown fox jumps over the lazy dog."
    const utterance = new SpeechSynthesisUtterance(testText)

    const voice = getSelectedVoice()
    if (voice) utterance.voice = voice
    utterance.rate = voiceRate
    utterance.pitch = voicePitch

    utterance.onstart = () => {
      voiceStatus.textContent = "Speaking..."
      voiceTestBtn.innerHTML = "<span>&#9208;</span> Stop"
    }

    utterance.onend = () => {
      voiceStatus.textContent = ""
      voiceTestBtn.innerHTML = "<span>&#127908;</span> Test Voice"
    }

    utterance.onerror = (e) => {
      voiceStatus.textContent = "Error: " + e.error
      voiceTestBtn.innerHTML = "<span>&#127908;</span> Test Voice"
    }

    window.speechSynthesis.speak(utterance)
  })
}

// Override the read button functionality to use selected voice
// This modifies the existing read buttons in addMessage
const originalAddMessageForVoice = addMessage
addMessage = window.addMessage = function(role, text) {
  const msg = originalAddMessageForVoice(role, text)

  // Find and enhance the read button if this is an assistant message
  if (role === "assistant" && msg) {
    const readBtn = msg.querySelector(".msg-read-btn")
    if (readBtn) {
      // Replace the click handler
      readBtn.replaceWith(readBtn.cloneNode(true))
      const newReadBtn = msg.querySelector(".msg-read-btn")

      newReadBtn.addEventListener("click", () => {
        const bubble = msg.querySelector(".msg-bubble")
        const textToSpeak = bubble?.dataset.fullText || bubble?.innerText || text || ""
        if (!textToSpeak.trim()) return

        if (window.speechSynthesis.speaking) {
          window.speechSynthesis.cancel()
          newReadBtn.textContent = "Read"
          return
        }

        const utterance = new SpeechSynthesisUtterance(textToSpeak)

        // Apply selected voice settings
        const voice = getSelectedVoice()
        if (voice) utterance.voice = voice
        utterance.rate = voiceRate
        utterance.pitch = voicePitch

        utterance.onend = () => { newReadBtn.textContent = "Read" }
        utterance.onerror = () => { newReadBtn.textContent = "Read" }

        window.speechSynthesis.speak(utterance)
        newReadBtn.textContent = "Pause"
      })
    }
  }

  return msg
}

console.log("[AI Response] Enhanced chat functionality initialized")

// ==============================
// VOICE CLONE
// ==============================
const cloneModelName = document.getElementById("cloneModelName")
const cloneUploadArea = document.getElementById("cloneUploadArea")
const cloneAudioFiles = document.getElementById("cloneAudioFiles")
const cloneSelectedFiles = document.getElementById("cloneSelectedFiles")
const cloneCreateBtn = document.getElementById("cloneCreateBtn")
const cloneCreateStatus = document.getElementById("cloneCreateStatus")
const cloneModelsList = document.getElementById("cloneModelsList")
const cloneTestModel = document.getElementById("cloneTestModel")
const cloneTestText = document.getElementById("cloneTestText")
const cloneTestBtn = document.getElementById("cloneTestBtn")
const cloneTestResult = document.getElementById("cloneTestResult")

let selectedAudioFiles = []
let voiceModels = []

function initVoiceClone() {
  if (!cloneUploadArea || !cloneAudioFiles) return
  cloneUploadArea.addEventListener("click", (e) => {
    if (e.target !== cloneAudioFiles) cloneAudioFiles.click()
  })
  cloneAudioFiles.addEventListener("change", (e) => {
    if (e.target.files.length > 0) {
      addAudioFiles(e.target.files)
      e.target.value = ""
    }
  })
  cloneUploadArea.addEventListener("dragover", (e) => {
    e.preventDefault()
    cloneUploadArea.classList.add("dragover")
  })
  cloneUploadArea.addEventListener("dragleave", () => {
    cloneUploadArea.classList.remove("dragover")
  })
  cloneUploadArea.addEventListener("drop", (e) => {
    e.preventDefault()
    cloneUploadArea.classList.remove("dragover")
    const files = Array.from(e.dataTransfer.files).filter(f => f.type.startsWith("audio/"))
    if (files.length > 0) addAudioFiles(files)
  })
  if (cloneCreateBtn) cloneCreateBtn.addEventListener("click", createVoiceModel)
  if (cloneTestBtn) cloneTestBtn.addEventListener("click", testVoiceSynthesis)
  loadVoiceModels()
  loadGalleryVoices()
}

function addAudioFiles(files) {
  selectedAudioFiles = [...selectedAudioFiles, ...files]
  renderSelectedFiles()
  updateCreateButton()
}

window.removeAudioFile = function(index) {
  selectedAudioFiles.splice(index, 1)
  renderSelectedFiles()
  updateCreateButton()
}

function renderSelectedFiles() {
  if (!cloneSelectedFiles) return
  if (selectedAudioFiles.length === 0) {
    cloneSelectedFiles.innerHTML = ""
    return
  }
  cloneSelectedFiles.innerHTML = selectedAudioFiles.map((file, index) => `
    <div class="clone-file-item">
      <span class="clone-file-name">${escapeHtml(file.name)}</span>
      <span class="clone-file-size">${formatFileSize(file.size)}</span>
      <button class="clone-file-remove" onclick="removeAudioFile(${index})" title="Remove">&#10005;</button>
    </div>
  `).join('')
}

function formatFileSize(bytes) {
  if (bytes < 1024) return bytes + " B"
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB"
  return (bytes / (1024 * 1024)).toFixed(1) + " MB"
}

function updateCreateButton() {
  if (!cloneCreateBtn) return
  const hasName = cloneModelName?.value.trim()
  const hasFiles = selectedAudioFiles.length > 0
  cloneCreateBtn.disabled = !hasName || !hasFiles

  // Visual hint if files added but name missing
  if (hasFiles && !hasName && cloneModelName) {
    cloneModelName.style.borderColor = '#f59e0b'
    cloneModelName.placeholder = 'Enter a name to enable Create button'
  } else if (cloneModelName) {
    cloneModelName.style.borderColor = ''
    if (!hasFiles) {
      cloneModelName.placeholder = 'e.g., My Interview Voice'
    }
  }
}

if (cloneModelName) {
  cloneModelName.addEventListener("input", updateCreateButton)
}

async function createVoiceModel() {
  const name = cloneModelName?.value.trim()
  if (!name || selectedAudioFiles.length === 0) return
  cloneCreateBtn.disabled = true
  cloneCreateStatus.innerHTML = '<div class="clone-status-training">Training... <span class="clone-spinner">&#9696;</span></div>'
  try {
    const formData = new FormData()
    formData.append("name", name)
    selectedAudioFiles.forEach((file, index) => formData.append('audio_' + index, file))
    const response = await fetch(`${API_BASE}/voice-clone/create`, { method: "POST", body: formData })
    const result = await response.json()
    if (result.error) throw new Error(result.error)
    cloneCreateStatus.innerHTML = '<div class="clone-status-training">Training model... <span class="clone-spinner">&#9696;</span></div>'
    pollModelStatus(result.model_id)
    selectedAudioFiles = []
    renderSelectedFiles()
    if (cloneModelName) cloneModelName.value = ""
    updateCreateButton()
  } catch (e) {
    console.error("Failed to create voice model:", e)
    cloneCreateStatus.innerHTML = '<div class="clone-status-error">Failed: ' + escapeHtml(e.message) + '</div>'
    updateCreateButton()
  }
}

async function pollModelStatus(modelId) {
  const checkStatus = async () => {
    try {
      const response = await fetch(`${API_BASE}/voice-clone/${modelId}/status`)
      const result = await response.json()
      if (result.status === "ready") {
        cloneCreateStatus.innerHTML = '<div class="clone-status-ready">Voice model ready! Scroll down to Test Voice Synthesis section.</div>'
        await loadVoiceModels()
      } else if (result.status === "error") {
        cloneCreateStatus.innerHTML = '<div class="clone-status-error">Training failed</div>'
      } else {
        setTimeout(checkStatus, 2000)
      }
    } catch (e) {
      console.error("Status check failed:", e)
      setTimeout(checkStatus, 5000)
    }
  }
  checkStatus()
}

async function loadVoiceModels() {
  if (!cloneModelsList) return
  try {
    const response = await fetch(`${API_BASE}/voice-clone/models`)
    const result = await response.json()
    voiceModels = result.models || []
    renderVoiceModels()
    updateTestModelSelect()
  } catch (e) {
    console.error("Failed to load voice models:", e)
    if (cloneModelsList) cloneModelsList.innerHTML = '<div class="clone-empty">Failed to load models</div>'
  }
}

function renderVoiceModels() {
  if (!cloneModelsList) return
  if (voiceModels.length === 0) {
    cloneModelsList.innerHTML = '<div class="clone-empty">No voice models yet. Create one above or install from gallery.</div>'
    return
  }
  const sourceLabels = { edge_tts: "Edge TTS", rvc: "RVC", gallery: "Gallery", uploaded: "Uploaded", trained: "Trained" }
  cloneModelsList.innerHTML = voiceModels.map(model => {
    const sourceLabel = sourceLabels[model.source] || model.source || "Edge TTS"
    const sourceBadge = model.source && model.source !== "edge_tts"
      ? `<span class="clone-source-badge" data-source="${model.source}">${sourceLabel}</span>`
      : ''
    return `
    <div class="clone-model-item" data-id="${model.id}">
      <div class="clone-model-info">
        <div class="clone-model-name">${escapeHtml(model.name)} ${sourceBadge}</div>
        <div class="clone-model-meta">${model.sample_count} samples • ${formatDateFromSeconds(model.created_at)}</div>
      </div>
      <div class="clone-model-status ${model.status}">${model.status}</div>
      <button class="clone-model-delete" onclick="deleteVoiceModel('${model.id}')" title="Delete">&#10005;</button>
    </div>
  `}).join('')
}

function updateTestModelSelect() {
  if (!cloneTestModel) return
  const cloneTestInfo = document.getElementById("cloneTestInfo")
  const readyModels = voiceModels.filter(m => m.status === "ready")

  if (readyModels.length === 0) {
    // No ready models - disable test section
    cloneTestModel.innerHTML = '<option value="">No voice models available - create one first</option>'
    cloneTestModel.disabled = true
    if (cloneTestText) cloneTestText.disabled = true
    if (cloneTestBtn) cloneTestBtn.disabled = true
    if (cloneTestInfo) cloneTestInfo.classList.remove("hidden")
    return
  }

  // Have ready models - enable test section
  cloneTestModel.innerHTML = '<option value="">Select a voice model...</option>' +
    readyModels.map(model => '<option value="' + model.id + '">' + escapeHtml(model.name) + '</option>').join('')
  cloneTestModel.disabled = false
  if (cloneTestText) cloneTestText.disabled = false
  if (cloneTestBtn) cloneTestBtn.disabled = false
  if (cloneTestInfo) cloneTestInfo.classList.add("hidden")
}

function formatDateFromSeconds(timestamp) {
  return new Date(timestamp * 1000).toLocaleDateString()
}

window.deleteVoiceModel = async function(modelId) {
  try {
    const response = await fetch(`${API_BASE}/voice-clone/models/${modelId}`, { method: "DELETE" })
    if (response.ok) await loadVoiceModels()
    else throw new Error("Delete failed")
  } catch (e) {
    console.error("Failed to delete voice model:", e)
    alert("Failed to delete voice model")
  }
}

// Install a gallery voice model
window.installGalleryVoice = async function(galleryId) {
  try {
    const response = await fetch(`${API_BASE}/voice-clone/gallery/${galleryId}/install`, { method: "POST" })
    const result = await response.json()
    if (result.error) throw new Error(result.error)
    showToast(`Voice "${result.name || galleryId}" installed!`, "success")
    await loadVoiceModels()
  } catch (e) {
    console.error("Failed to install gallery voice:", e)
    showToast("Failed to install voice: " + e.message, "error")
  }
}

// Load and display gallery voices
async function loadGalleryVoices() {
  const galleryContainer = document.getElementById("voiceGallery")
  if (!galleryContainer) return
  try {
    const response = await fetch(`${API_BASE}/voice-clone/gallery`)
    const result = await response.json()
    const voices = result.voices || []
    if (voices.length === 0) {
      galleryContainer.innerHTML = '<div class="clone-empty">No gallery voices available</div>'
      return
    }
    const genderLabels = { male: "M", female: "F", neutral: "N" }
    galleryContainer.innerHTML = voices.map(v => `
      <div class="clone-model-item gallery-item" data-gallery-id="${v.id}">
        <div class="clone-model-info">
          <div class="clone-model-name">${genderLabels[v.gender] ? '[' + genderLabels[v.gender] + '] ' : ''}${escapeHtml(v.name)}</div>
          <div class="clone-model-meta">${v.category} • ${v.accent} accent</div>
        </div>
        <button class="clone-test-btn" style="font-size:12px;padding:4px 10px" onclick="installGalleryVoice('${v.id}')">Install</button>
      </div>
    `).join('')
  } catch (e) {
    console.error("Failed to load gallery:", e)
  }
}

async function testVoiceSynthesis() {
  const modelId = cloneTestModel?.value
  const text = cloneTestText?.value.trim()
  if (!modelId) {
    if (cloneTestResult) cloneTestResult.innerHTML = '<div class="clone-status-error">Please select a voice model</div>'
    return
  }
  if (!text) {
    if (cloneTestResult) cloneTestResult.innerHTML = '<div class="clone-status-error">Please enter text to synthesize</div>'
    return
  }
  cloneTestBtn.disabled = true
  if (cloneTestResult) cloneTestResult.innerHTML = '<div class="clone-status-training">Synthesizing... <span class="clone-spinner">&#9696;</span></div>'
  try {
    const response = await fetch(`${API_BASE}/voice-clone/${modelId}/synthesize`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text })
    })
    const result = await response.json()

    // Check for HTTP error or backend error
    if (!response.ok || result.error) {
      const errorMsg = result.error || result.detail || 'Request failed'
      // Show error with fallback option
      if (cloneTestResult) {
        const btnId = 'browserTtsBtn_' + Date.now()
        cloneTestResult.innerHTML = `
          <div class="clone-status-error">${escapeHtml(errorMsg)}</div>
          <div class="clone-tts-fallback">
            <p>Click to hear with browser voice:</p>
            <button id="${btnId}" class="clone-test-btn" style="margin-top:8px;background:var(--primary);color:#fff;">
              ▶ Play Speech
            </button>
          </div>
        `
        // Add click handler after a short delay to ensure DOM is updated
        setTimeout(() => {
          const ttsBtn = document.getElementById(btnId)
          if (ttsBtn) {
            ttsBtn.addEventListener('click', () => {
              if (window.speechSynthesis.speaking) {
                window.speechSynthesis.cancel()
                ttsBtn.textContent = '▶ Play Speech'
                return
              }
              const utterance = new SpeechSynthesisUtterance(text)
              utterance.onend = () => { ttsBtn.textContent = '▶ Play Speech' }
              utterance.onerror = () => { ttsBtn.textContent = '▶ Play Speech' }
              window.speechSynthesis.speak(utterance)
              ttsBtn.textContent = '⏸ Pause'
            })
          }
        }, 10)
      }
      return
    }

    if (result.audio_url && cloneTestResult) {
      // Server-generated audio available — play it
      const audioSrc = API_BASE + result.audio_url
      const voiceName = escapeHtml(result.voice_name || modelId)
      const duration = result.duration_estimate ? `(~${result.duration_estimate.toFixed(1)}s)` : ''
      cloneTestResult.innerHTML = `
        <div class="clone-status-success">Synthesis complete ${duration} — Voice: ${voiceName}</div>
        <div class="clone-audio-player" style="margin-top:8px">
          <audio controls autoplay src="${audioSrc}" style="width:100%;border-radius:8px">
            Your browser does not support audio playback.
          </audio>
        </div>
      `
    } else if (result.browser_tts && cloneTestResult) {
      // Browser TTS fallback — no server audio available
      const btnId = 'browserTtsBtn_' + Date.now()
      const voiceName = escapeHtml(result.voice_name || modelId)
      const duration = result.duration_estimate ? `(~${result.duration_estimate.toFixed(1)}s)` : ''
      cloneTestResult.innerHTML = `
        <div class="clone-status-success">Synthesis complete ${duration}</div>
        <div class="clone-tts-fallback">
          <p>Voice: ${voiceName} (browser TTS)</p>
          <button id="${btnId}" class="clone-test-btn" style="margin-top:8px;background:var(--primary);color:#fff;">
            ▶ Play Speech
          </button>
        </div>
      `
      setTimeout(() => {
        const ttsBtn = document.getElementById(btnId)
        if (ttsBtn) {
          ttsBtn.addEventListener('click', () => {
            if (window.speechSynthesis.speaking) {
              window.speechSynthesis.cancel()
              ttsBtn.textContent = '▶ Play Speech'
              return
            }
            const utterance = new SpeechSynthesisUtterance(text)
            utterance.onend = () => { ttsBtn.textContent = '▶ Play Speech' }
            utterance.onerror = () => { ttsBtn.textContent = '▶ Play Speech' }
            // Try to pick a voice that matches
            const voices = window.speechSynthesis.getVoices()
            if (voices.length > 0) {
              const englishVoice = voices.find(v => v.lang.startsWith('en'))
              if (englishVoice) utterance.voice = englishVoice
            }
            window.speechSynthesis.speak(utterance)
            ttsBtn.textContent = '⏸ Pause'
          })
        }
      }, 10)
    }
  } catch (e) {
    console.error("Synthesis failed:", e)
    // Show fallback even on network errors
    if (cloneTestResult) {
      cloneTestResult.innerHTML = `
        <div class="clone-status-error">Synthesis failed: ${escapeHtml(e.message)}</div>
        <div class="clone-tts-fallback">
          <p>Using browser TTS as fallback:</p>
          <button id="browserTtsBtn" class="clone-test-btn" style="margin-top:8px">
            <span><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;margin-right:4px"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><path d="M15.54 8.46a5 5 0 0 1 0 7.07"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14"/></svg></span>Play with Browser Voice
          </button>
        </div>
      `
      const ttsBtn = document.getElementById('browserTtsBtn')
      if (ttsBtn) {
        ttsBtn.addEventListener('click', () => {
          const utterance = new SpeechSynthesisUtterance(text)
          window.speechSynthesis.speak(utterance)
        })
      }
    }
  } finally {
    cloneTestBtn.disabled = false
  }
}

// ==============================
// VOICE CLONE LIVE RECORDING
// ==============================
const cloneRecordBtn = document.getElementById("cloneRecordBtn")
const cloneRecordingUi = document.getElementById("cloneRecordingUi")
const cloneRecordingTimer = document.getElementById("cloneRecordingTimer")
const cloneRecordingWave = document.getElementById("cloneRecordingWave")
const cloneStopRecordBtn = document.getElementById("cloneStopRecordBtn")

console.log("[Voice Clone] Recording elements:", { cloneRecordBtn: !!cloneRecordBtn, cloneRecordingUi: !!cloneRecordingUi, cloneStopRecordBtn: !!cloneStopRecordBtn })

let cloneMediaRecorder = null
let cloneRecordedChunks = []
let cloneRecordingStartTime = 0
let cloneRecordingTimerInterval = null
let cloneAudioContext = null
let cloneAnalyser = null
let cloneDataArray = null
let cloneVisualizerInterval = null

function initVoiceCloneRecording() {
  console.log("[Voice Clone] initVoiceCloneRecording called")
  if (!cloneRecordBtn || !cloneStopRecordBtn) {
    console.log("[Voice Clone] Recording buttons not found, skipping init")
    return
  }

  // Create wave bars
  if (cloneRecordingWave) {
    for (let i = 0; i < 9; i++) {
      const bar = document.createElement('div')
      bar.className = 'wave-bar'
      cloneRecordingWave.appendChild(bar)
    }
  }

  cloneRecordBtn.addEventListener("click", startRecording)
  cloneStopRecordBtn.addEventListener("click", stopRecording)
}

async function startRecording() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })

    // Show recording UI
    cloneRecordBtn.style.display = 'none'
    cloneRecordingUi.style.display = 'block'

    // Setup MediaRecorder
    cloneMediaRecorder = new MediaRecorder(stream)
    cloneRecordedChunks = []

    cloneMediaRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) cloneRecordedChunks.push(e.data)
    }

    cloneMediaRecorder.onstop = () => {
      console.log("[Voice Clone] Recording stopped, processing...")
      const blob = new Blob(cloneRecordedChunks, { type: 'audio/webm' })
      const duration = Math.floor((Date.now() - cloneRecordingStartTime) / 1000)
      console.log("[Voice Clone] Blob size:", blob.size, "duration:", duration)
      addRecordedFile(blob, duration)

      // Stop all tracks
      stream.getTracks().forEach(track => track.stop())

      // Reset UI
      cloneRecordingUi.style.display = 'none'
      cloneRecordBtn.style.display = 'flex'
      stopTimer()
      stopVisualizer()
    }

    // Setup audio visualization
    setupVisualizer(stream)

    // Start recording
    cloneMediaRecorder.start(100)
    cloneRecordingStartTime = Date.now()
    startTimer()

  } catch (err) {
    console.error("Recording failed:", err)
    alert("Could not access microphone. Please check permissions.")
  }
}

function stopRecording() {
  if (cloneMediaRecorder && cloneMediaRecorder.state !== 'inactive') {
    cloneMediaRecorder.stop()
  }
}

function startTimer() {
  cloneRecordingTimerInterval = setInterval(() => {
    const elapsed = Math.floor((Date.now() - cloneRecordingStartTime) / 1000)
    const mins = Math.floor(elapsed / 60).toString().padStart(2, '0')
    const secs = (elapsed % 60).toString().padStart(2, '0')
    if (cloneRecordingTimer) cloneRecordingTimer.textContent = `${mins}:${secs}`
  }, 100)
}

function stopTimer() {
  if (cloneRecordingTimerInterval) {
    clearInterval(cloneRecordingTimerInterval)
    cloneRecordingTimerInterval = null
  }
  if (cloneRecordingTimer) cloneRecordingTimer.textContent = '00:00'
}

function setupVisualizer(stream) {
  try {
    cloneAudioContext = new (window.AudioContext || window.webkitAudioContext)()
    const source = cloneAudioContext.createMediaStreamSource(stream)
    cloneAnalyser = cloneAudioContext.createAnalyser()
    cloneAnalyser.fftSize = 64
    source.connect(cloneAnalyser)

    cloneDataArray = new Uint8Array(cloneAnalyser.frequencyBinCount)

    cloneVisualizerInterval = setInterval(() => {
      if (!cloneAnalyser || !cloneRecordingWave) return
      cloneAnalyser.getByteFrequencyData(cloneDataArray)

      const bars = cloneRecordingWave.querySelectorAll('.wave-bar')
      const step = Math.floor(cloneDataArray.length / bars.length)

      bars.forEach((bar, i) => {
        const value = cloneDataArray[i * step] || 0
        const percent = Math.max(20, (value / 255) * 100)
        bar.style.height = percent + '%'
      })
    }, 50)
  } catch (e) {
    console.error("Visualizer setup failed:", e)
  }
}

function stopVisualizer() {
  if (cloneVisualizerInterval) {
    clearInterval(cloneVisualizerInterval)
    cloneVisualizerInterval = null
  }
  if (cloneAudioContext) {
    cloneAudioContext.close()
    cloneAudioContext = null
  }
  // Reset wave bars
  if (cloneRecordingWave) {
    const bars = cloneRecordingWave.querySelectorAll('.wave-bar')
    bars.forEach(bar => bar.style.height = '')
  }
}

function addRecordedFile(blob, duration) {
  console.log("[Voice Clone] addRecordedFile called, duration:", duration)
  const timestamp = new Date().toLocaleTimeString()
  const filename = `Recording ${timestamp}.webm`
  const file = new File([blob], filename, { type: 'audio/webm' })
  file.duration = duration
  file.isRecorded = true

  selectedAudioFiles.push(file)
  console.log("[Voice Clone] File added, total files:", selectedAudioFiles.length)
  renderSelectedFiles()
  updateCreateButton()

  // Auto-focus name field if empty
  if (cloneModelName && !cloneModelName.value.trim()) {
    cloneModelName.focus()
  }
}

// Override renderSelectedFiles to handle recorded items
const originalRenderSelectedFiles = renderSelectedFiles
renderSelectedFiles = function() {
  if (!cloneSelectedFiles) return

  if (selectedAudioFiles.length === 0) {
    cloneSelectedFiles.innerHTML = ""
    return
  }

  cloneSelectedFiles.innerHTML = selectedAudioFiles.map((file, index) => {
    const isRecorded = file.isRecorded
    const durationStr = file.duration ?
      `${Math.floor(file.duration / 60)}:${(file.duration % 60).toString().padStart(2, '0')}` :
      formatFileSize(file.size)

    if (isRecorded) {
      return `
        <div class="clone-recorded-item">
          <span class="recorded-badge">● LIVE</span>
          <span class="recorded-name">${escapeHtml(file.name)}</span>
          <span class="recorded-duration">${durationStr}</span>
          <button class="clone-file-remove" onclick="removeAudioFile(${index})" title="Remove">&#10005;</button>
        </div>
      `
    } else {
      return `
        <div class="clone-file-item">
          <span class="clone-file-name">${escapeHtml(file.name)}</span>
          <span class="clone-file-size">${formatFileSize(file.size)}</span>
          <button class="clone-file-remove" onclick="removeAudioFile(${index})" title="Remove">&#10005;</button>
        </div>
      `
    }
  }).join('')
}

// Voice clone init moved to initFeatures() to wait for auth
console.log("[Voice Clone] Module initialized (will fully init after auth)")
