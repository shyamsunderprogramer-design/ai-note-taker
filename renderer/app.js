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

// ==============================
// GLOBAL ENTER KEY + F KEY LISTENERS
// ==============================
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
// CHAT FUNCTIONS
// ==============================
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
  chatArea.appendChild(msg)

  scrollChat()
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
    latestBotMessage.bubble.innerHTML += text
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;")
      .replace(/\n/g, "<br>")
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
  chatArea.appendChild(msg)

  scrollChat()

  latestBotMessage = { role, element: msg, bubble }
  return msg
}

function finishStream() {
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
  const streamUrl = window.api.getStreamUrlWithMode(query, mode, responseStyle)

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

menuBtn.addEventListener("click", () => {
  // Future: show settings/logs panel
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
// INIT
// ==============================
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
