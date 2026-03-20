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
const chatArea = document.getElementById("chatArea")
const chatWelcome = document.getElementById("chatWelcome")
const menuBtn = document.getElementById("menuBtn")

// ==============================
// GLOBAL ENTER KEY LISTENER
// ==============================
document.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.ctrlKey && !e.shiftKey && !e.altKey && !e.metaKey) {
    const tag = document.activeElement.tagName.toLowerCase()
    if (tag === "input" || tag === "textarea" || tag === "select") return
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
  chatArea.scrollTop = chatArea.scrollHeight
}

function addMessage(role, text) {
  removeWelcome()

  const msg = document.createElement("div")
  msg.className = "chat-message " + role

  const label = role === "user" ? "You" : "AI"
  const bubble = document.createElement("div")
  bubble.className = "msg-bubble"
  bubble.textContent = text

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

function streamMessage(role, text) {
  removeWelcome()

  if (latestBotMessage && latestBotMessage.role === "assistant") {
    latestBotMessage.bubble.textContent += text
    scrollChat()
    return latestBotMessage.element
  }

  const msg = document.createElement("div")
  msg.className = "chat-message " + role

  const label = role === "user" ? "You" : "AI"
  const bubble = document.createElement("div")
  bubble.className = "msg-bubble"
  bubble.textContent = text

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
    return
  }

  if (!response.ok) {
    addErrorMessage("Transcription failed")
    return
  }

  const data = await response.json()

  if (data.text) {
    streamMessage("user", data.text)
  } else {
    setProcessingUI(false)
    return
  }

  if (data.response) {
    const modelInfo = data.model ? ` [${data.mode} · ${data.model}]` : ` [${data.mode}]`
    streamMessage("assistant", data.response + modelInfo)
  }

  setProcessingUI(false)
  finishStream()
}

// ==============================
// START / STOP LISTENING
// ==============================
listenBtn.addEventListener("click", async () => {
  if (isStarting) return

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
fontSizeSelect.addEventListener("change", () => {
  document.documentElement.style.setProperty("--font-size", fontSizeSelect.value + "px")
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
// INIT
// ==============================
async function init() {
  try {
    await waitForBackend()
  } catch (e) {
    console.error(e)
  }
}

init()
