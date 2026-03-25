// ==============================
// STATE
// ==============================
let isListening = false
let isStarting = false
let isBackendReady = false
let isUndetectable = false
let mediaRecorder = null
let mediaStream = null
let audioChunks = []
let latestBotMessage = null
let currentConversationId = null
let currentMessages = []
let suppressAutoSave = false
let historySortBy = "updatedAt" // "updatedAt" | "createdAt" | "title" | "messageCount"

// ==============================
// DOM REFS
// ==============================
const stealthBtn = document.getElementById("stealthBtn")
const stealthLabel = document.getElementById("stealthLabel")
const listenBtn = document.getElementById("listenBtn")
const listenLabel = document.getElementById("listenLabel")
const minBtn = document.getElementById("minBtn")
const maxBtn = document.getElementById("maxBtn")
const closeBtn = document.getElementById("closeBtn")
const modeSelect = document.getElementById("modeSelect") // hidden, kept for compatibility
const modelSelect = document.getElementById("modelSelect")
const fontSizeSelect = document.getElementById("fontSizeSelect") // hidden fallback
const fontSizeRange = document.getElementById("fontSizeRange")
const fontSizeValue = document.getElementById("fontSizeValue")
const responseStyleSelect = document.getElementById("responseStyleSelect") // hidden fallback
const responseStyleControl = document.getElementById("responseStyleControl")
const contextLengthSelect = document.getElementById("contextLengthSelect") // hidden fallback
const contextStepper = document.getElementById("contextStepper")
const contextValue = document.getElementById("contextValue")
const tokenLimitSelect = document.getElementById("tokenLimitSelect") // hidden fallback
const tokenStepper = document.getElementById("tokenStepper")
const tokenLimitValue = document.getElementById("tokenLimitValue")
const tokenCounter = document.getElementById("tokenCounter")
const chatArea = document.getElementById("chatArea")
const chatWelcome = document.getElementById("chatWelcome")
const summarizeBtn = document.getElementById("summarizeBtn")
const menuBtn = document.getElementById("menuBtn")
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
const cloudModelSelect = document.getElementById("cloudModelSelect")

// ==============================
// GLOBAL ENTER KEY + F KEY LISTENERS
// ==============================
// Listen for stealth state changes triggered by Alt+D shortcut in main process
window.api.onStealthStateChanged((state) => {
  isUndetectable = state.undetectable
  stealthBtn.classList.toggle("undetectable", state.undetectable)
  stealthLabel.textContent = state.undetectable ? "Undetectable" : "Detectable"
})
document.addEventListener("keydown", (e) => {
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
    // Enter elsewhere = toggle listening
    e.preventDefault()
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
  return modelSelect.value || "auto"
}

function getSelectedResponseStyle() {
  const activeSeg = document.querySelector(".seg-btn.active")
  return activeSeg ? activeSeg.getAttribute("data-value") : (responseStyleSelect?.value || "concise")
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
  return CONTEXT_STEPS[contextIdx] ?? 3
}

function getSelectedTokenLimit() {
  return TOKEN_STEPS[tokenIdx] ?? 128000
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
  if (processing) {
    listenBtn.classList.add("listening")
    listenBtn.disabled = true
    listenLabel.textContent = "Processing..."
  } else {
    listenBtn.classList.remove("listening")
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

function escapeHtml(text) {
  if (!text) return ""
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;")
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
    messages: currentMessages
  }

  try {
    const saved = await window.api.conversationSave(conversation)
    currentConversationId = saved.id
  } catch (err) {
    console.error("[Conversation] Save error:", err)
  }
}

function loadConversationIntoUI(conversation) {
  chatArea.innerHTML = ""
  currentMessages = []
  currentConversationId = conversation.id
  suppressAutoSave = true

  conversation.messages.forEach(msg => {
    if (msg.role === "user") {
      addMessage("user", msg.text)
    } else {
      addMessage("assistant", msg.text)
    }
  })

  suppressAutoSave = false
  hideSummarizeButton()
  renderHistoryList()
}

function startNewConversation() {
  currentConversationId = null
  currentMessages = []
  chatArea.innerHTML = ""
  if (chatWelcome) {
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

function showToast(message) {
  const existing = document.querySelector(".toast-message")
  if (existing) existing.remove()
  const toast = document.createElement("div")
  toast.className = "toast-message"
  toast.textContent = message
  toast.style.cssText = "position:fixed;bottom:80px;left:50%;transform:translateX(-50%);background:#22c55e;color:#fff;padding:8px 16px;border-radius:8px;font-size:13px;z-index:9999;animation:fadeOut 2s forwards"
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

function closeHistoryPanel() {
  historyPanel.classList.remove("open")
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

  // Load full conversations for search + preview snippets
  let searchMatches = null
  if (searchQuery) {
    const allConvs = await Promise.all(list.map(c => window.api.conversationLoad(c.id)))
    searchMatches = {}
    allConvs.forEach(conv => {
      if (!conv) return
      const ql = searchQuery.toLowerCase()
      const titleMatch = conv.title.toLowerCase().includes(ql)
      const msgMatch = conv.messages.find(m => m.text.toLowerCase().includes(ql))
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
  const sortedUnpinned = unpinned.sort(sortFn)

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
    groupHeader.textContent = groupName + (isPinnedSection ? "  ★ Pinned" : "")
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

      // Emoji icons for modes
      const modeEmoji = {
        adaptive: "⚡", auto: "⚡", fast: "🔥", cloud: "☁️",
        universal: "✨", interview: "💬", reasoning: "🧠", code: "💻"
      }
      const icon = modeEmoji[mode] || "💬"
      const previewIcon = previewRole === "user" ? "👤" : "🤖"

      const item = document.createElement("div")
      item.className = "history-item" + (isActive ? " active" : "")
      item.setAttribute("data-id", conv.id)

      item.innerHTML = `
        <div class="history-item-icon">${icon}</div>
        <div class="history-item-content">
          <div class="history-item-top">
            ${conv.pinned ? '<span class="pin-icon" title="Pinned">📌</span>' : ''}
            <div class="history-item-title">${highlightText(conv.title, searchQuery)}</div>
          </div>
          ${preview ? `<div class="history-item-preview"><span class="preview-role-icon">${previewIcon}</span> ${highlightText(preview, searchQuery)}</div>` : ""}
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

    // Position dropdown relative to menu button
    const rect = menuBtn.getBoundingClientRect()
    dropdown.style.position = "fixed"
    dropdown.style.top = rect.bottom + 4 + "px"
    dropdown.style.right = window.innerWidth - rect.right + "px"
    dropdown.style.zIndex = "99999"

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

  // Click on history item body (not a button) — resume conversation
  const historyItem = e.target.closest(".history-item")
  if (historyItem && !e.target.closest("button")) {
    const id = historyItem.getAttribute("data-id")
    if (id) {
      window.api.conversationLoad(id).then(full => {
        if (full) { loadConversationIntoUI(full); closeHistoryPanel() }
      })
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
  setBubbleText(bubble, text)

  msg.innerHTML = `<span class="msg-label">${label}</span>`
  msg.appendChild(bubble)

  // Add copy button for assistant messages
  if (role === "assistant") {
    const actions = document.createElement("div")
    actions.className = "msg-actions"
    const copyBtn = document.createElement("button")
    copyBtn.className = "msg-copy-btn"
    copyBtn.textContent = "Copy"
    copyBtn.addEventListener("click", () => {
      navigator.clipboard.writeText(text).then(() => {
        copyBtn.textContent = "✓"
        copyBtn.classList.add("copied")
        setTimeout(() => { copyBtn.textContent = "Copy"; copyBtn.classList.remove("copied") }, 1500)
      })
    })
    actions.appendChild(copyBtn)
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

// Helper to set text with newline support
function setBubbleText(bubble, text) {
  // Escape HTML and convert newlines to <br>
  const escaped = text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;")
    .replace(/\n/g, "<br>")
  bubble.innerHTML = escaped
}

function streamMessage(role, text) {
  removeWelcome()

  if (latestBotMessage && latestBotMessage.role === "assistant") {
    // Streaming chunk for assistant message - accumulate text
    latestBotMessage.bubble.innerHTML += text
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;")
      .replace(/\n/g, "<br>")
    if (latestBotMessage.accumulatedText !== undefined) {
      latestBotMessage.accumulatedText += text
    }
    scrollChat()
    return latestBotMessage.element
  }

  const msg = document.createElement("div")
  msg.className = "chat-message " + role

  const label = role === "user" ? "You" : "AI"
  const bubble = document.createElement("div")
  bubble.className = "msg-bubble"
  setBubbleText(bubble, text)

  msg.innerHTML = `<span class="msg-label">${label}</span>`
  msg.appendChild(bubble)

  // Add copy button for assistant streaming messages
  if (role === "assistant") {
    const actions = document.createElement("div")
    actions.className = "msg-actions"
    const copyBtn = document.createElement("button")
    copyBtn.className = "msg-copy-btn"
    copyBtn.textContent = "Copy"
    copyBtn.addEventListener("click", () => {
      const textToCopy = latestBotMessage && latestBotMessage.accumulatedText !== undefined
        ? latestBotMessage.accumulatedText
        : bubble.innerText.replace(/\[.*?\]\s*$/, "").trim()
      navigator.clipboard.writeText(textToCopy).then(() => {
        copyBtn.textContent = "✓"
        copyBtn.classList.add("copied")
        setTimeout(() => { copyBtn.textContent = "Copy"; copyBtn.classList.remove("copied") }, 1500)
      })
    })
    actions.appendChild(copyBtn)
    msg.appendChild(actions)
  }

  chatArea.appendChild(msg)

  scrollChat()

  latestBotMessage = { role, element: msg, bubble, accumulatedText: role === "assistant" ? text : undefined }

  // Track user messages
  if (!suppressAutoSave && role === "user") {
    const modeTag = document.querySelector(".mode-tag")
    const currentMode = modeTag ? modeTag.textContent.replace(/[\[\]]/g, "").trim() : "adaptive"
    currentMessages.push({ role, text, timestamp: Date.now(), mode: currentMode })
    saveCurrentConversation()
  }

  return msg
}

function finishStream() {
  // Save assistant message to currentMessages before clearing
  if (latestBotMessage && latestBotMessage.role === "assistant" && !suppressAutoSave) {
    // Get plain text, stripping the mode tag if present
    const rawText = latestBotMessage.bubble.innerText || ""
    const text = rawText.replace(/\[.*?\]\s*$/, "").trim()
    const modeTag = document.querySelector(".mode-tag")
    const currentMode = modeTag ? modeTag.textContent.replace(/[\[\]]/g, "").trim() : "adaptive"
    currentMessages.push({ role: "assistant", text, timestamp: Date.now(), mode: currentMode })
    saveCurrentConversation()
  }
  latestBotMessage = null
  showSummarizeButton()
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
  setProcessingUI(true)

  await window.api.setMode(getSelectedMode())

  streamMessage("user", text)
  await streamAIResponse(text)
}

// ==============================
// SUBMIT AUDIO
// ==============================
async function submitAudio(blob) {
  setProcessingUI(true)

  await window.api.setMode(getSelectedMode())

  const formData = new FormData()
  formData.append("file", blob, "audio.webm")

  let response
  try {
    response = await fetch(window.api.getTranscribeUrl(), {
      method: "POST",
      body: formData
    })
  } catch (e) {
    addErrorMessage("Backend unavailable")
    setProcessingUI(false)
    return
  }

  if (!response.ok) {
    addErrorMessage("Transcription failed")
    setProcessingUI(false)
    return
  }

  const data = await response.json()

  if (data.text) {
    streamMessage("user", data.text)
  } else {
    setProcessingUI(false)
    return
  }

  // Use streaming endpoint for AI response
  await streamAIResponse(data.text)
}

// ==============================
// STREAM AI RESPONSE
// ==============================
async function streamAIResponse(query) {
  const mode = getSelectedMode()
  const responseStyle = getSelectedResponseStyle()
  const selectedModel = modelSelect ? modelSelect.value : "auto"
  // If a cloud model is selected (has a provider prefix), use it as provider
  const isCloudModel = selectedModel && selectedModel !== "auto" && selectedModel.includes("-")
  const provider = isCloudModel ? selectedModel : "ollama"
  const contextMessages = getContextMessages()
  const streamUrl = window.api.getStreamUrlWithMode(query, mode, responseStyle, provider, contextMessages)

  try {
    const response = await fetch(streamUrl)
    if (!response.ok) {
      addErrorMessage("AI stream failed")
      setProcessingUI(false)
      return
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ""

    // Create assistant message element for streaming
    streamMessage("assistant", "")

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      if (latestBotMessage && latestBotMessage.bubble) {
        let processed = buffer
          .replace(/&/g, "&amp;")
          .replace(/</g, "&lt;")
          .replace(/>/g, "&gt;")
          .replace(/"/g, "&quot;")
          .replace(/'/g, "&#039;")

        // Ensure bullet points are on separate lines
        processed = processed.replace(/\* /g, "<br>* ")

        latestBotMessage.bubble.innerHTML += processed
        // Also update plain text accumulator for copy functionality
        if (latestBotMessage.accumulatedText !== undefined) {
          latestBotMessage.accumulatedText += buffer
        }
      }
      buffer = ""
      scrollChat()
    }

    // Add mode info
    const modelInfo = ` <span class="mode-tag">[${mode}]</span>`
    if (latestBotMessage && latestBotMessage.bubble) {
      latestBotMessage.bubble.innerHTML += modelInfo
    }
    scrollChat()
    finishStream()
    setProcessingUI(false)
  } catch (e) {
    console.error("Stream error:", e)
    addErrorMessage("AI response failed")
    setProcessingUI(false)
  }
}

// ==============================
// START / STOP LISTENING
// ==============================
listenBtn.addEventListener("click", async () => {
  if (isStarting) return

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

    if (!isBackendReady) {
      setProcessingUI(true)
      const ok = await waitForBackend()
      if (!ok) {
        addErrorMessage("Backend unavailable")
        setProcessingUI(false)
        isStarting = false
        return
      }
    }

    setListeningUI(true)
    mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true })
    mediaRecorder = new MediaRecorder(mediaStream)
    audioChunks = []

    mediaRecorder.addEventListener("dataavailable", (e) => {
      if (e.data && e.data.size > 0) {
        audioChunks.push(e.data)
      }
    })

    mediaRecorder.addEventListener("stop", async () => {
      const audioBlob = new Blob(audioChunks, { type: "audio/webm" })
      mediaRecorder = null
      audioChunks = []
      stopTracks()

      if (audioBlob.size === 0) {
        setListeningUI(false)
        return
      }

      setListeningUI(false)
      await submitAudio(audioBlob)
    })

    mediaRecorder.start()

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
  if (mediaRecorder && mediaRecorder.state !== "inactive") {
    mediaRecorder.stop()
  } else {
    setListeningUI(false)
  }
}

// ==============================
// TRACK CLEANUP
// ==============================
function stopTracks() {
  if (mediaStream) {
    for (const track of mediaStream.getTracks()) {
      track.stop()
    }
    mediaStream = null
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
// RESPONSE STYLE SEGMENTED CONTROL
// ==============================
document.querySelectorAll(".seg-btn", ).forEach(btn => {
  btn.addEventListener("click", async () => {
    const value = btn.getAttribute("data-value")
    document.querySelectorAll(".seg-btn").forEach(b => b.classList.remove("active"))
    btn.classList.add("active")
    if (responseStyleSelect) responseStyleSelect.value = value
    await window.api.storeSet("responseStyle", value)
  })
})

// ==============================
// CONTEXT STEPPER
// ==============================
const CONTEXT_STEPS = [0, 1, 3, 5, 10]
let contextIdx = 2 // default: 3

function updateContextStepper() {
  const val = CONTEXT_STEPS[contextIdx]
  if (contextValue) contextValue.textContent = val === 0 ? "Off" : val
  if (contextLengthSelect) contextLengthSelect.value = val
  return val
}

contextStepper?.querySelector(".stepper-minus")?.addEventListener("click", async () => {
  if (contextIdx > 0) {
    contextIdx--
    const val = updateContextStepper()
    await window.api.storeSet("contextLength", val)
  }
})

contextStepper?.querySelector(".stepper-plus")?.addEventListener("click", async () => {
  if (contextIdx < CONTEXT_STEPS.length - 1) {
    contextIdx++
    const val = updateContextStepper()
    await window.api.storeSet("contextLength", val)
  }
})

// ==============================
// TOKEN STEPPER
// ==============================
const TOKEN_STEPS = [8000, 32000, 128000, 256000, 512000, 1024000]
const TOKEN_LABELS = ["8K", "32K", "128K", "256K", "512K", "1M"]
let tokenIdx = 2 // default: 128K

function updateTokenStepper() {
  const val = TOKEN_STEPS[tokenIdx]
  const label = TOKEN_LABELS[tokenIdx]
  if (tokenLimitValue) tokenLimitValue.textContent = label
  if (tokenLimitSelect) tokenLimitSelect.value = val
  return val
}

tokenStepper?.querySelector(".stepper-minus")?.addEventListener("click", async () => {
  if (tokenIdx > 0) {
    tokenIdx--
    const val = updateTokenStepper()
    await window.api.storeSet("tokenLimit", val)
  }
})

tokenStepper?.querySelector(".stepper-plus")?.addEventListener("click", async () => {
  if (tokenIdx < TOKEN_STEPS.length - 1) {
    tokenIdx++
    const val = updateTokenStepper()
    await window.api.storeSet("tokenLimit", val)
  }
})

// ==============================
// FONT SIZE SLIDER
// ==============================
function updateSliderFill(slider) {
  const min = parseFloat(slider.min) || 0
  const max = parseFloat(slider.max) || 100
  const val = parseFloat(slider.value)
  const pct = ((val - min) / (max - min)) * 100
  slider.style.background = `linear-gradient(to right, var(--primary) ${pct}%, var(--line) ${pct}%)`
}

fontSizeRange?.addEventListener("input", async () => {
  const val = fontSizeRange.value
  if (fontSizeValue) fontSizeValue.textContent = val
  document.documentElement.style.setProperty("--font-size", val + "px")
  if (fontSizeSelect) fontSizeSelect.value = val
  updateSliderFill(fontSizeRange)
  await window.api.storeSet("fontSize", val)
})

// ==============================
// LEGACY SELECT EVENTS (kept for compatibility)
// ==============================
modelSelect?.addEventListener("change", async () => {
  await window.api.storeSet("model", modelSelect.value)
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
  maxBtn.textContent = result && result.isMaximized ? "▢" : "❐"
})

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

    // Call the AI summary endpoint
    const mode = getSelectedMode()
    const responseStyle = "detailed"
    const selectedModel = modelSelect ? modelSelect.value : "auto"
    const isCloudModel = selectedModel && selectedModel !== "auto" && selectedModel.includes("-")
    const provider = isCloudModel ? selectedModel : "ollama"

    // Build URL manually since we need a different prompt
    const healthUrl = window.api.getHealthUrl()
    const base = healthUrl.replace("/health", "")
    const params = new URLSearchParams({
      q: transcript,
      mode: "summary",
      style: responseStyle,
      provider
    })
    const url = `${base}/stream?${params.toString()}`

    const response = await fetch(url)
    if (!response.ok) throw new Error("Summary failed")

    // Stream the summary into a summary block
    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ""

    const summaryBlock = document.createElement("div")
    summaryBlock.className = "summary-block"
    summaryBlock.innerHTML = `<div class="summary-block-title">&#10022; Summary</div><div class="summary-block-content" id="summaryContent"></div>`
    chatArea.appendChild(summaryBlock)
    scrollChat()

    const summaryContent = document.getElementById("summaryContent")

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      summaryContent.innerHTML = buffer
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
      scrollChat()
    }

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
// HISTORY PANEL
// ==============================
historyBtn.addEventListener("click", () => {
  historyPanel.classList.toggle("open")
  if (historyPanel.classList.contains("open")) {
    renderHistoryList()
  }
})

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
    historyPanel.classList.contains("open") &&
    !historyPanel.contains(e.target) &&
    !historyBtn.contains(e.target)
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
  stealthBtn.classList.toggle("undetectable", undetectable)
  stealthLabel.textContent = undetectable ? "Undetectable" : "Detectable"
}

stealthBtn.addEventListener("click", async () => {
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
// MENU BUTTON + APP MENU
// ==============================
const appMenu = document.getElementById("appMenu")
const shortcutsModal = document.getElementById("shortcutsModal")
const aboutModal = document.getElementById("aboutModal")
const closeShortcutsBtn = document.getElementById("closeShortcutsModal")
const closeAboutBtn = document.getElementById("closeAboutModal")

menuBtn.addEventListener("click", (e) => {
  e.stopPropagation()
  appMenu.classList.toggle("open")
  shortcutsModal.classList.remove("open")
  aboutModal.classList.remove("open")
})

// Close menu when clicking outside
document.addEventListener("click", (e) => {
  if (appMenu.classList.contains("open") && !appMenu.contains(e.target) && !menuBtn.contains(e.target)) {
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
    settingsPanel.classList.add("open")
    try {
      const providers = await window.api.getProviders()
      updateProviderUI("openai", providers.openai)
      updateProviderUI("anthropic", providers.anthropic)
      updateProviderUI("google", providers.google)
      updateProviderUI("xai", providers.xai)
      updateProviderUI("deepseek", providers.deepseek)
      updateProviderUI("groq", providers.groq)
    } catch (e) { console.error(e) }
    const savedCloudModel = await window.api.storeGet("cloudModel")
    if (savedCloudModel && cloudModelSelect) cloudModelSelect.value = savedCloudModel
    updateActiveProviders()
  }
  else if (action === "shortcuts") {
    shortcutsModal.classList.add("open")
  }
  else if (action === "about") {
    aboutModal.classList.add("open")
    loadAboutStatus()
  }
  else if (action === "logs") {
    window.api.openLogs()
  }
  else if (action === "quit") {
    window.api.closeWindow()
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

  // Check Ollama
  try {
    const res = await fetch("http://127.0.0.1:11434/api/tags", { method: "GET", signal: AbortSignal.timeout(3000) })
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
let isConfigPanelOpen = false

// DOM refs for config panel
const providerConfigPanel = document.getElementById("providerConfigPanel")
const settingsProvidersView = document.getElementById("settingsProvidersView")
const settingsBackBtn = document.getElementById("settingsBackBtn")
const settingsHeaderTitle = document.getElementById("settingsHeaderTitle")
const configProviderName = document.getElementById("configProviderName")
const configProviderStatus = document.getElementById("configProviderStatus")
const configProviderIcon = document.getElementById("configProviderIcon")
const configApiKeyInput = document.getElementById("configApiKeyInput")
const configToggleKeyVisibility = document.getElementById("configToggleKeyVisibility")
const configEnabledToggle = document.getElementById("configEnabledToggle")
const configEnabledStatus = document.getElementById("configEnabledStatus")
const configModelSelect = document.getElementById("configModelSelect")
const configTestBtn = document.getElementById("configTestBtn")
const configSaveBtn = document.getElementById("configSaveBtn")
const configTestResult = document.getElementById("configTestResult")

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
  }
}

// Open inline config panel for a provider
function openProviderConfig(provider) {
  activeProvider = provider
  isConfigPanelOpen = true

  const meta = PROVIDER_META[provider]
  if (!meta) return

  configProviderName.textContent = meta.name
  configProviderIcon.innerHTML = "&#9679;"
  configProviderIcon.style.color = {
    openai: "#6ee7b7",
    anthropic: "#fcd34d",
    google: "#fcd34d",
    xai: "rgba(255,255,255,0.8)",
    deepseek: "#7dd3fc",
    groq: "#fca5a5",
  }[provider] || "rgba(255,255,255,0.5)"

  // Load stored config
  loadProviderConfig(provider)

  // Populate model select
  configModelSelect.innerHTML = ""
  meta.models.forEach(m => {
    const opt = document.createElement("option")
    opt.value = m.value
    opt.textContent = m.label
    configModelSelect.appendChild(opt)
  })

  // Switch views
  settingsProvidersView.style.display = "none"
  providerConfigPanel.classList.add("open")
  settingsBackBtn.style.display = "flex"
  settingsHeaderTitle.textContent = meta.name

  configApiKeyInput.focus()
}

function closeProviderConfig() {
  isConfigPanelOpen = false
  activeProvider = null
  providerConfigPanel.classList.remove("open")
  settingsProvidersView.style.display = ""
  settingsBackBtn.style.display = "none"
  settingsHeaderTitle.textContent = "Settings"
  configTestResult.classList.remove("show", "success", "error")
  configTestResult.textContent = ""
}

// Load provider config from store
async function loadProviderConfig(provider) {
  const stored = await window.api.storeGet("provider_" + provider) || {}
  const hasKey = await checkProviderHasKey(provider)

  configApiKeyInput.value = stored.apiKey || ""
  configEnabledToggle.checked = stored.enabled !== false && hasKey

  const statusEl = document.getElementById("configProviderStatus")
  const statusText = document.getElementById("configStatusText")
  if (hasKey) {
    if (statusEl) statusEl.className = "config-card-status configured"
    if (statusText) statusText.textContent = "Configured"
  } else {
    if (statusEl) statusEl.className = "config-card-status"
    if (statusText) statusText.textContent = "Not configured"
  }

  if (stored.model) {
    configModelSelect.value = stored.model
  }
}

// Check if provider has API key configured (from backend)
async function checkProviderHasKey(provider) {
  try {
    const providers = await window.api.getProviders()
    return !!providers[provider]
  } catch {
    return false
  }
}

// Update enabled status in config panel header
function updateEnabledStatus() {
  const enabled = configEnabledToggle.checked
  const statusEl = document.getElementById("configProviderStatus")
  const statusText = document.getElementById("configStatusText")
  if (enabled) {
    if (statusEl) statusEl.className = "config-card-status enabled"
    if (statusText) statusText.textContent = "Enabled"
  } else {
    if (statusEl) statusEl.className = "config-card-status"
    if (statusText) statusText.textContent = "Configured"
  }
}

// Toggle key visibility
configToggleKeyVisibility.addEventListener("click", () => {
  const isPassword = configApiKeyInput.type === "password"
  configApiKeyInput.type = isPassword ? "text" : "password"
  configToggleKeyVisibility.textContent = isPassword ? "&#128064;" : "&#128065;"
})

// Enable toggle
configEnabledToggle.addEventListener("change", () => {
  updateEnabledStatus()
})

// Back button
settingsBackBtn.addEventListener("click", closeProviderConfig)

// Close settings panel
closeSettingsBtn.addEventListener("click", () => {
  if (isConfigPanelOpen) {
    closeProviderConfig()
  } else {
    settingsPanel.classList.remove("open")
  }
})

// Test button
configTestBtn.addEventListener("click", async () => {
  const apiKey = configApiKeyInput.value.trim()
  if (!apiKey) {
    configTestResult.className = "provider-config-test-result show error"
    configTestResult.textContent = "Enter an API key first"
    return
  }

  configTestResult.className = "provider-config-test-result show"
  configTestResult.style.color = "var(--text-dim)"
  configTestResult.textContent = "Testing..."

  try {
    // Try to call the backend configure endpoint
    const result = await window.api.configureProvider(activeProvider, apiKey)
    if (result.error) throw new Error(result.error)

    // Send a minimal test request
    const healthUrl = window.api.getHealthUrl()
    const base = healthUrl.replace("/health", "")
    const testUrl = `${base}/providers`
    const resp = await fetch(testUrl)
    const data = await resp.json()

    if (data[activeProvider]) {
      configTestResult.className = "provider-config-test-result show success"
      configTestResult.textContent = "Connection successful"
    } else {
      configTestResult.className = "provider-config-test-result show error"
      configTestResult.textContent = "Key saved but not detected — restart backend"
    }
  } catch (e) {
    configTestResult.className = "provider-config-test-result show error"
    configTestResult.textContent = "Test failed: " + e.message
  }
})

// Save button
configSaveBtn.addEventListener("click", async () => {
  const apiKey = configApiKeyInput.value.trim()
  const enabled = configEnabledToggle.checked
  const model = configModelSelect.value

  try {
    // Save API key to backend
    if (apiKey) {
      await window.api.configureProvider(activeProvider, apiKey)
    }

    // Save config to local store
    await window.api.storeSet("provider_" + activeProvider, {
      apiKey,
      enabled,
      model
    })

    // Update UI
    updateProviderUI(activeProvider, !!apiKey)
    updateActiveProviders()

    // Show success
    configTestResult.className = "provider-config-test-result show success"
    configTestResult.textContent = "Saved successfully"

    // Auto-close after short delay
    setTimeout(() => {
      closeProviderConfig()
    }, 800)
  } catch (e) {
    configTestResult.className = "provider-config-test-result show error"
    configTestResult.textContent = "Save failed: " + e.message
  }
})

// Enter/Escape on config panel input
configApiKeyInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") configTestBtn.click()
})

function updateProviderUI(key, configured) {
  const card = document.getElementById("card-" + key)
  const hintNames = { openai: "OpenAI", anthropic: "Anthropic", google: "Google", xai: "XAI", deepseek: "DeepSeek", groq: "Groq", ollama: "Ollama" }
  const hintId = "hint" + (hintNames[key] || key.charAt(0).toUpperCase() + key.slice(1))
  const hintEl = document.getElementById(hintId)
  if (card) card.classList.toggle("configured", configured)
  if (hintEl) hintEl.textContent = configured ? "Ready" : "Not configured"
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
  }
  const activeKey = activeMap[selected]

  // Clear all active bars
  document.querySelectorAll(".provider-active-bar").forEach(el => el.classList.remove("active"))
  document.querySelectorAll(".provider-row").forEach(el => el.classList.remove("active"))

  // Set active for the current cloud model provider, or ollama
  if (activeKey) {
    const bar = document.getElementById("active-" + activeKey)
    if (bar) bar.classList.add("active")
    const card = document.getElementById("card-" + activeKey)
    if (card) card.classList.add("active")
  } else {
    // Ollama is active (default/local mode)
    const bar = document.getElementById("active-ollama")
    if (bar) bar.classList.add("active")
    const card = document.getElementById("card-ollama")
    if (card) card.classList.add("active")
  }
}

// Provider config buttons — open inline panel
document.querySelectorAll(".provider-config-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    const provider = btn.getAttribute("data-provider")
    if (!provider) return
    openProviderConfig(provider)
  })
})

// Close settings when clicking outside
document.addEventListener("click", (e) => {
  if (
    settingsPanel.classList.contains("open") &&
    !settingsPanel.contains(e.target) &&
    !menuBtn.contains(e.target)
  ) {
    if (isConfigPanelOpen) {
      closeProviderConfig()
    } else {
      settingsPanel.classList.remove("open")
    }
  }
})
async function init() {
  try {
    await waitForBackend()

    // Restore user preferences

    // Font size
    const savedFontSize = await window.api.storeGet("fontSize")
    if (savedFontSize) {
      if (fontSizeRange) fontSizeRange.value = savedFontSize
      if (fontSizeValue) fontSizeValue.textContent = savedFontSize
      if (fontSizeSelect) fontSizeSelect.value = savedFontSize
      document.documentElement.style.setProperty("--font-size", savedFontSize + "px")
      if (fontSizeRange) updateSliderFill(fontSizeRange)
    } else {
      if (fontSizeRange) updateSliderFill(fontSizeRange)
    }

    // Mode
    const savedMode = await window.api.storeGet("mode")
    if (savedMode && modeSelect) modeSelect.value = savedMode

    // Mode change handler
    modeSelect?.addEventListener("change", async () => {
      const value = modeSelect.value
      await window.api.storeSet("mode", value)
    })

    // Response style
    const savedResponseStyle = await window.api.storeGet("responseStyle")
    if (savedResponseStyle) {
      if (responseStyleSelect) responseStyleSelect.value = savedResponseStyle
      document.querySelectorAll(".seg-btn").forEach(b => {
        b.classList.toggle("active", b.getAttribute("data-value") === savedResponseStyle)
      })
    }

    // Context stepper
    const savedContextLength = await window.api.storeGet("contextLength")
    if (savedContextLength) {
      if (contextLengthSelect) contextLengthSelect.value = savedContextLength
      contextIdx = CONTEXT_STEPS.indexOf(parseInt(savedContextLength, 10))
      if (contextIdx < 0) contextIdx = 2
      updateContextStepper()
    }

    // Token stepper
    const savedTokenLimit = await window.api.storeGet("tokenLimit")
    if (savedTokenLimit) {
      if (tokenLimitSelect) tokenLimitSelect.value = savedTokenLimit
      tokenIdx = TOKEN_STEPS.indexOf(parseInt(savedTokenLimit, 10))
      if (tokenIdx < 0) tokenIdx = 2
      updateTokenStepper()
    }

    // Model
    const savedModel = await window.api.storeGet("model")
    if (savedModel && modelSelect) {
      modelSelect.value = savedModel
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
  } catch (e) {
    console.error(e)
  }
}

init()
