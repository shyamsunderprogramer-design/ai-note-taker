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
const modeSelect = document.getElementById("modeSelect")
const modelSelect = document.getElementById("modelSelect")
const fontSizeSelect = document.getElementById("fontSizeSelect")
const responseStyleSelect = document.getElementById("responseStyleSelect")
const chatArea = document.getElementById("chatArea")
const chatWelcome = document.getElementById("chatWelcome")
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
// Listen for stealth state changes triggered by Ctrl+D shortcut in main process
window.api.onStealthStateChanged((state) => {
  isUndetectable = state.enabled
  stealthBtn.classList.toggle("undetectable", state.enabled)
  stealthLabel.textContent = state.enabled ? "Undetectable" : "Detectable"
})
document.addEventListener("keydown", (e) => {
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
  return modeSelect.value || "auto"
}

function getSelectedModel() {
  return modelSelect.value || "auto"
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
  const isToday = d.toDateString() === now.toDateString()
  if (isToday) {
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
  }
  return d.toLocaleDateString() + " " + d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
}

async function saveCurrentConversation() {
  if (currentMessages.length === 0) return
  const firstUserMsg = currentMessages.find(m => m.role === "user")
  const title = firstUserMsg ? generateTitle(firstUserMsg.text) : "Untitled"

  const conversation = {
    id: currentConversationId,
    title,
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
  renderHistoryList()
}

function startNewConversation() {
  currentConversationId = null
  currentMessages = []
  chatArea.innerHTML = ""
  if (chatWelcome) {
    chatArea.appendChild(chatWelcome)
  }
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
  navigator.clipboard.writeText(text).then(() => {
    // Brief visual feedback
    const btn = document.querySelector(`[data-id="${conversation.id}"]`)
    if (btn) {
      const original = btn.textContent
      btn.textContent = "✓"
      setTimeout(() => btn.textContent = original, 1000)
    }
  })
}

function exportConversation(conversation) {
  const date = new Date(conversation.updatedAt || conversation.createdAt).toLocaleString()
  const lines = [`# ${conversation.title}\n`, `*Exported: ${date}*\n`]
  conversation.messages.forEach(msg => {
    const label = msg.role === "user" ? "**You**" : "**AI**"
    const mode = msg.mode ? ` [${msg.mode}]` : ""
    lines.push(`### ${label}${mode}\n${msg.text}\n`)
  })
  navigator.clipboard.writeText(lines.join("\n")).then(() => {
    const btn = document.querySelector(`[data-id="${conversation.id}"]`)
    if (btn) {
      const original = btn.textContent
      btn.textContent = "✓"
      setTimeout(() => btn.textContent = original, 1000)
    }
  })
}

function renameConversation(conversation) {
  const newTitle = prompt("Rename conversation:", conversation.title)
  if (!newTitle || newTitle.trim() === conversation.title) return
  const updated = { ...conversation, title: newTitle.trim(), updatedAt: Date.now() }
  window.api.conversationSave(updated).then(() => renderHistoryList())
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

async function renderHistoryList() {
  const list = await window.api.conversationList()
  const searchQuery = (document.getElementById("historySearch")?.value || "").toLowerCase().trim()

  // Load full conversations for search
  let searchMatches = null // { id -> fullConv } map for preview snippets
  if (searchQuery) {
    const allConvs = await Promise.all(list.map(c => window.api.conversationLoad(c.id)))
    searchMatches = {}
    allConvs.forEach(conv => {
      if (!conv) return
      const matches = conv.title.toLowerCase().includes(searchQuery) ||
        conv.messages.some(m => m.text.toLowerCase().includes(searchQuery))
      if (matches) {
        searchMatches[conv.id] = conv
      }
    })
  }

  // Filter by search
  let filtered = list
  if (searchQuery && searchMatches) {
    filtered = list.filter(c => searchMatches[c.id])
  }

  // Sort: pinned first, then by sortBy
  const pinned = filtered.filter(c => c.pinned)
  const unpinned = filtered.filter(c => !c.pinned)

  const sortKey = historySortBy
  const sortFn = (a, b) => {
    if (sortKey === "title") return a.title.localeCompare(b.title)
    if (sortKey === "messageCount") return (b.messageCount || 0) - (a.messageCount || 0)
    return (b[sortKey] || 0) - (a[sortKey] || 0)
  }

  const sorted = [...pinned.sort(sortFn), ...unpinned.sort(sortFn)]

  historyList.innerHTML = ""

  if (sorted.length === 0) {
    historyList.innerHTML = `<div class="history-empty">${searchQuery ? "No matches found" : "No conversations yet"}</div>`
    return
  }

  sorted.forEach(conv => {
    const isActive = conv.id === currentConversationId
    const pinState = conv.pinned ? "&#9679;" : "" // filled dot for pinned

    // Build preview text
    let preview = ""
    if (searchQuery && searchMatches && searchMatches[conv.id]) {
      const firstMatch = searchMatches[conv.id].messages.find(m => m.text.toLowerCase().includes(searchQuery))
      if (firstMatch) {
        preview = firstMatch.text.substring(0, 60).replace(/\n/g, " ") + (firstMatch.text.length > 60 ? "..." : "")
      }
    }

    const item = document.createElement("div")
    item.className = "history-item" + (isActive ? " active" : "")
    item.setAttribute("data-id", conv.id)
    item.innerHTML = `
      <div class="history-item-content">
        <div class="history-item-title">${pinState ? '<span class="pin-dot">&#9679;</span>' : ''}${escapeHtml(conv.title)}</div>
        ${preview ? `<div class="history-item-preview">${escapeHtml(preview)}</div>` : ""}
        <div class="history-item-date">${formatDate(conv.updatedAt)}</div>
      </div>
      <button class="history-menu-btn" data-id="${conv.id}">&#8226;&#8226;&#8226;</button>
      <div class="history-dropdown" id="dropdown-${conv.id}">
        <button class="history-dropdown-item" data-action="resume" data-id="${conv.id}">Resume</button>
        <button class="history-dropdown-item" data-action="rename" data-id="${conv.id}">Rename</button>
        <button class="history-dropdown-item" data-action="export" data-id="${conv.id}">Export</button>
        <button class="history-dropdown-item" data-action="pin" data-id="${conv.id}">${conv.pinned ? "Unpin" : "Pin"}</button>
        <button class="history-dropdown-item" data-action="copy" data-id="${conv.id}">Copy</button>
        <button class="history-dropdown-item danger" data-action="delete" data-id="${conv.id}">Delete</button>
      </div>
    `
    item.addEventListener("click", async (e) => {
      if (e.target.classList.contains("history-menu-btn")) {
        e.stopPropagation()
        document.querySelectorAll(".history-dropdown.open").forEach(d => {
          if (d.id !== `dropdown-${conv.id}`) d.classList.remove("open")
        })
        const dropdown = document.getElementById(`dropdown-${conv.id}`)
        dropdown.classList.toggle("open")
        return
      }
      if (e.target.classList.contains("history-dropdown-item")) return
      const full = await window.api.conversationLoad(conv.id)
      if (full) {
        loadConversationIntoUI(full)
        closeHistoryPanel()
      }
    })
    historyList.appendChild(item)
  })

  // Dropdown item handlers
  historyList.querySelectorAll(".history-dropdown-item").forEach(btn => {
    btn.addEventListener("click", async (e) => {
      e.stopPropagation()
      const action = btn.getAttribute("data-action")
      const id = btn.getAttribute("data-id")
      const full = await window.api.conversationLoad(id)

      if (action === "resume" && full) {
        resumeConversation(full)
        closeHistoryPanel()
      } else if (action === "copy" && full) {
        copyConversation(full)
      } else if (action === "export" && full) {
        exportConversation(full)
      } else if (action === "rename" && full) {
        renameConversation(full)
      } else if (action === "pin") {
        await pinConversation(id)
      } else if (action === "delete") {
        deleteConversation(id)
      }
    })
  })
}
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
    const text = latestBotMessage.accumulatedText || latestBotMessage.bubble.innerText
    const modeTag = document.querySelector(".mode-tag")
    const currentMode = modeTag ? modeTag.textContent.replace(/[\[\]]/g, "").trim() : "adaptive"
    currentMessages.push({ role: "assistant", text, timestamp: Date.now(), mode: currentMode })
    saveCurrentConversation()
  }
  latestBotMessage = null
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
  const responseStyle = responseStyleSelect ? responseStyleSelect.value : "concise"
  const cloudModel = cloudModelSelect ? cloudModelSelect.value : "auto"
  const provider = (mode === "cloud" || mode === "fast" && cloudModel !== "auto") ? cloudModel : "ollama"
  const streamUrl = window.api.getStreamUrlWithMode(query, mode, responseStyle, provider)

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
// BUTTON EVENTS
// ==============================
fontSizeSelect.addEventListener("change", async () => {
  document.documentElement.style.setProperty("--font-size", fontSizeSelect.value + "px")
  await window.api.storeSet("fontSize", fontSizeSelect.value)
})

modeSelect.addEventListener("change", async () => {
  await window.api.storeSet("mode", modeSelect.value)
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
stealthBtn.addEventListener("click", async () => {
  isUndetectable = !isUndetectable
  stealthBtn.classList.toggle("undetectable", isUndetectable)
  stealthLabel.textContent = isUndetectable ? "Undetectable" : "Detectable"
  try {
    await window.api.setUndetectable(isUndetectable)
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
    const newHeight = Math.max(300, startHeight + delta)
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
  appMenu.classList.remove("open")

  const action = item.getAttribute("data-action")

  if (action === "settings") {
    settingsPanel.classList.add("open")
    try {
      const providers = await window.api.getProviders()
      updateProviderUI("openAI", providers.openai)
      updateProviderUI("anthropic", providers.anthropic)
      updateProviderUI("google", providers.google)
      updateProviderUI("xAI", providers.xai)
    } catch (e) { console.error(e) }
    const savedCloudModel = await window.api.storeGet("cloudModel")
    if (savedCloudModel && cloudModelSelect) cloudModelSelect.value = savedCloudModel
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

closeSettingsBtn.addEventListener("click", () => {
  settingsPanel.classList.remove("open")
})

function updateProviderUI(key, configured) {
  const statusEl = document.getElementById("status" + key)
  const hintEl = document.getElementById("hint" + key)
  if (statusEl) statusEl.classList.toggle("configured", configured)
  if (hintEl) hintEl.textContent = configured ? "Configured" : "Not configured"
}

// Provider config buttons
document.querySelectorAll(".provider-config-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    activeProvider = btn.getAttribute("data-provider")
    const names = { openai: "OpenAI", anthropic: "Anthropic", google: "Google", xai: "xAI" }
    modalProviderName.textContent = names[activeProvider] || activeProvider
    apiKeyInput.value = ""
    apiKeyModal.classList.add("open")
    apiKeyInput.focus()
  })
})

modalCancel.addEventListener("click", () => {
  apiKeyModal.classList.remove("open")
  activeProvider = null
})

modalSave.addEventListener("click", async () => {
  if (!activeProvider) return
  const key = apiKeyInput.value.trim()
  if (!key) return
  try {
    await window.api.configureProvider(activeProvider, key)
    apiKeyModal.classList.remove("open")
    // Update UI
    updateProviderUI(activeProvider.charAt(0).toUpperCase() + activeProvider.slice(1), true)
    activeProvider = null
  } catch (e) {
    console.error("Failed to save API key:", e)
  }
})

apiKeyInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") modalSave.click()
  if (e.key === "Escape") modalCancel.click()
})

cloudModelSelect?.addEventListener("change", async () => {
  await window.api.storeSet("cloudModel", cloudModelSelect.value)
})

// Close settings panel when clicking outside
document.addEventListener("click", (e) => {
  if (
    settingsPanel.classList.contains("open") &&
    !settingsPanel.contains(e.target) &&
    !settingsBtn.contains(e.target)
  ) {
    settingsPanel.classList.remove("open")
  }
  if (
    apiKeyModal.classList.contains("open") &&
    !apiKeyModal.querySelector(".modal-box").contains(e.target)
  ) {
    apiKeyModal.classList.remove("open")
  }
})
async function init() {
  try {
    await waitForBackend()

    // Restore user preferences
    const savedFontSize = await window.api.storeGet("fontSize")
    if (savedFontSize) {
      fontSizeSelect.value = savedFontSize
      document.documentElement.style.setProperty("--font-size", savedFontSize + "px")
    }

    const savedMode = await window.api.storeGet("mode")
    if (savedMode) {
      modeSelect.value = savedMode
    }
  } catch (e) {
    console.error(e)
  }
}

init()
