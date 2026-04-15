// Offscreen Document — Audio capture and streaming engine
// Stealth: No identifiable strings in console output.

const TARGET_SAMPLE_RATE = 16000;
const CHUNK_SIZE = 1600; // 100ms at 16kHz

// State
let tabAudioContext = null;
let micAudioContext = null;
let tabStream = null;
let micStream = null;
let tabWorklet = null;
let micWorklet = null;
let tabWs = null;
let micWs = null;
let tabTranscription = '';
let micTranscription = '';
let isPaused = false;
let silenceWarningSent = false;
let tabAuthed = false;
let micAuthed = false;

// ===== TAB AUDIO CAPTURE =====

async function startTabCapture(streamId, backendUrl, token, meetingId) {
  try {
    // Create MediaStream from the tab capture stream ID
    tabStream = await navigator.mediaDevices.getUserMedia({
      audio: {
        mandatory: {
          chromeMediaSource: 'tab',
          chromeMediaSourceId: streamId
        }
      }
    });

    // Set up AudioContext and worklet pipeline
    tabAudioContext = new AudioContext({ sampleRate: TARGET_SAMPLE_RATE });
    const source = tabAudioContext.createMediaStreamSource(tabStream);

    // Register our custom downsample worklet
    await tabAudioContext.audioWorklet.addModule('audio-worklet-processor.js');
    tabWorklet = new AudioWorkletNode(tabAudioContext, 'downsample-processor');

    // Handle audio chunks from the worklet
    tabWorklet.port.onmessage = (event) => {
      if (event.data.type === 'audio-chunk') {
        if (!isPaused && tabWs && tabWs.readyState === WebSocket.OPEN && tabAuthed) {
          tabWs.send(event.data.data);
        }
        // Forward volume/silence info to background
        chrome.runtime.sendMessage({
          action: 'audio-level',
          source: 'tab',
          rms: event.data.rms,
          silenceSeconds: event.data.silenceSeconds
        });
        // Warn if silent for 60+ seconds
        if (event.data.silenceSeconds > 60 && !silenceWarningSent) {
          silenceWarningSent = true;
          chrome.runtime.sendMessage({
            action: 'silence-warning',
            message: 'No audio detected for 60 seconds. Is the meeting still active?'
          });
        }
      } else if (event.data.type === 'audio-flush') {
        if (tabWs && tabWs.readyState === WebSocket.OPEN && tabAuthed) {
          tabWs.send(event.data.data);
        }
      }
    };

    source.connect(tabWorklet);
    tabWorklet.connect(tabAudioContext.destination); // Must connect to destination for processing

    // Connect WebSocket to backend (token sent as first message, not in URL)
    const wsUrl = buildWebSocketUrl(backendUrl, 'tab', meetingId);
    tabWs = new WebSocket(wsUrl);
    tabAuthed = false;
    setupWebSocketHandlers(tabWs, 'tab', token);

    // Tab capture started
  } catch (e) {
    console.error('Tab capture error:', e);
    chrome.runtime.sendMessage({
      action: 'capture-error',
      source: 'tab',
      error: e.message
    });
  }
}

// ===== MICROPHONE CAPTURE =====

async function startMicCapture(backendUrl, token, meetingId) {
  try {
    micStream = await navigator.mediaDevices.getUserMedia({ audio: true });

    micAudioContext = new AudioContext({ sampleRate: TARGET_SAMPLE_RATE });
    const source = micAudioContext.createMediaStreamSource(micStream);

    await micAudioContext.audioWorklet.addModule('audio-worklet-processor.js');
    micWorklet = new AudioWorkletNode(micAudioContext, 'downsample-processor');

    micWorklet.port.onmessage = (event) => {
      if (event.data.type === 'audio-chunk') {
        if (!isPaused && micWs && micWs.readyState === WebSocket.OPEN && micAuthed) {
          micWs.send(event.data.data);
        }
        chrome.runtime.sendMessage({
          action: 'audio-level',
          source: 'mic',
          rms: event.data.rms
        });
      } else if (event.data.type === 'audio-flush') {
        if (micWs && micWs.readyState === WebSocket.OPEN && micAuthed) {
          micWs.send(event.data.data);
        }
      }
    };

    source.connect(micWorklet);
    micWorklet.connect(micAudioContext.destination);

    const wsUrl = buildWebSocketUrl(backendUrl, 'mic', meetingId);
    micWs = new WebSocket(wsUrl);
    micAuthed = false;
    setupWebSocketHandlers(micWs, 'mic', token);

    // Mic capture started
  } catch (e) {
    console.error('Mic capture error:', e);
    chrome.runtime.sendMessage({
      action: 'capture-error',
      source: 'mic',
      error: e.message
    });
  }
}

// ===== WEBSOCKET =====

// STEALTH: Token is sent as the first message after connection, NOT in the URL.
// This prevents token exposure in server logs, proxy logs, and browser history.
function buildWebSocketUrl(backendUrl, source, meetingId) {
  const wsBase = backendUrl.replace(/^http/, 'ws');
  let url = `${wsBase}/ws/transcribe?source=${source}`;
  if (meetingId) url += `&meeting_id=${encodeURIComponent(meetingId)}`;
  return url;
}

function setupWebSocketHandlers(ws, source, token) {
  let authed = !token; // If no token required, skip auth

  function setAuthed(val) {
    authed = val;
    if (source === 'tab') tabAuthed = val;
    else micAuthed = val;
  }

  ws.onopen = () => {
    // Send auth as first message (token NOT in URL for stealth)
    if (token) {
      ws.send(JSON.stringify({ type: 'auth', token: token }));
    } else {
      setAuthed(true); // No token needed, mark as authed immediately
    }
    chrome.runtime.sendMessage({
      action: 'ws-status',
      source: source,
      status: 'connected'
    });
  };

  ws.onmessage = (event) => {
    try {
      // Handle JSON messages (auth responses, transcriptions, errors)
      if (typeof event.data === 'string') {
        const data = JSON.parse(event.data);

        // Auth response
        if (data.type === 'auth_ok') {
          setAuthed(true);
          return;
        }
        if (data.type === 'auth_error') {
          setAuthed(false);
          chrome.runtime.sendMessage({
            action: 'auth-expired',
            source: source,
            error: data.message || 'Auth failed'
          });
          ws.close(4001);
          return;
        }

        // Error from server
        if (data.error) {
          console.error(`WS ${source} error:`, data.error);
          chrome.runtime.sendMessage({
            action: 'transcription-error',
            source: source,
            error: data.error
          });
          return;
        }

        // Transcription messages
        if (data.type === 'partial') {
          if (source === 'tab') tabTranscription = data.text;
          else micTranscription = data.text;

          chrome.runtime.sendMessage({
            action: 'transcription-partial',
            source: source,
            text: data.text,
            meetingId: data.meeting_id || ''
          });
        } else if (data.type === 'final') {
          if (source === 'tab') tabTranscription = data.text;
          else micTranscription = data.text;

          chrome.runtime.sendMessage({
            action: 'transcription-final',
            source: source,
            text: data.text,
            meetingId: data.meeting_id || ''
          });
        }
      }
    } catch (e) {
      console.error(`WS ${source} parse error:`, e);
    }
  };

  ws.onerror = (event) => {
    console.error(`WebSocket ${source} error:`, event);
    chrome.runtime.sendMessage({
      action: 'ws-status',
      source: source,
      status: 'error',
      error: 'WebSocket connection error'
    });
  };

  ws.onclose = (event) => {
    // WebSocket closed
    if (event.code === 4001) {
      chrome.runtime.sendMessage({
        action: 'auth-expired',
        source: source,
        message: 'Authentication token expired or invalid'
      });
    } else {
      chrome.runtime.sendMessage({
        action: 'ws-status',
        source: source,
        status: 'disconnected',
        code: event.code
      });
    }
  };
}

// ===== STOP / PAUSE =====

function stopCapture(source) {
  if (source === 'tab' || source === 'both') {
    if (tabWorklet) {
      tabWorklet.port.postMessage({ type: 'stop' });
    }
    if (tabWs && tabWs.readyState === WebSocket.OPEN) {
      tabWs.close(1000, 'User stopped recording');
    }
    if (tabStream) {
      tabStream.getTracks().forEach(t => t.stop());
      tabStream = null;
    }
    if (tabAudioContext) {
      tabAudioContext.close();
      tabAudioContext = null;
    }
    tabWorklet = null;
    tabWs = null;
    tabAuthed = false;
    tabTranscription = '';
    // Tab capture stopped
  }

  if (source === 'mic' || source === 'both') {
    if (micWorklet) {
      micWorklet.port.postMessage({ type: 'stop' });
    }
    if (micWs && micWs.readyState === WebSocket.OPEN) {
      micWs.close(1000, 'User stopped recording');
    }
    if (micStream) {
      micStream.getTracks().forEach(t => t.stop());
      micStream = null;
    }
    if (micAudioContext) {
      micAudioContext.close();
      micAudioContext = null;
    }
    micWorklet = null;
    micWs = null;
    micAuthed = false;
    micTranscription = '';
    // Mic capture stopped
  }

  isPaused = false;
  silenceWarningSent = false;
}

function pauseCapture() {
  isPaused = true;
  if (tabWorklet) tabWorklet.port.postMessage({ type: 'pause' });
  if (micWorklet) micWorklet.port.postMessage({ type: 'pause' });
  // Capture paused
}

function resumeCapture() {
  isPaused = false;
  if (tabWorklet) tabWorklet.port.postMessage({ type: 'resume' });
  if (micWorklet) micWorklet.port.postMessage({ type: 'resume' });
  silenceWarningSent = false;
  // Capture resumed
}

// ===== MESSAGE HANDLER =====

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  switch (message.action) {
    case 'start-capture':
      silenceWarningSent = false;
      startTabCapture(message.streamId, message.backendUrl, message.token, message.meetingId)
        .then(() => sendResponse({ success: true }))
        .catch(e => sendResponse({ success: false, error: e.message }));
      return true; // async response

    case 'start-mic':
      startMicCapture(message.backendUrl, message.token, message.meetingId)
        .then(() => sendResponse({ success: true }))
        .catch(e => sendResponse({ success: false, error: e.message }));
      return true;

    case 'stop-capture':
      stopCapture(message.source || 'both');
      sendResponse({ success: true });
      return false;

    case 'pause-capture':
      pauseCapture();
      sendResponse({ success: true });
      return false;

    case 'resume-capture':
      resumeCapture();
      sendResponse({ success: true });
      return false;

    case 'get-state':
      sendResponse({
        tabActive: !!tabStream,
        micActive: !!micStream,
        paused: isPaused,
        tabTranscription,
        micTranscription
      });
      return false;
  }
});

// Offscreen document ready