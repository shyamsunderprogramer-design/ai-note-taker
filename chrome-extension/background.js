// Background Service Worker — Central orchestration for tab capture, offscreen doc, and message routing

const API_BASE = 'http://localhost:8000';
const WS_BASE = 'ws://127.0.0.1:8000';

// Meeting URL patterns for auto-detection
const MEETING_PATTERNS = [
  { pattern: '*://*.zoom.us/j/*', platform: 'zoom' },
  { pattern: '*://*.zoom.us/meeting/*', platform: 'zoom' },
  { pattern: '*://meet.google.com/*', platform: 'google-meet' },
  { pattern: '*://*.teams.microsoft.com/l/meeting/*', platform: 'teams' },
  { pattern: '*://*.webex.com/*', platform: 'webex' }
];

// State
let offscreenDocCreated = false;
let recordingState = {
  status: 'idle', // idle | capturing | paused
  tabId: null,
  startTime: null,
  source: 'tab', // tab | mic | both
  meetingPlatform: null,
  meetingId: '',
  transcription: ''
};

// ===== INITIALIZATION =====

chrome.runtime.onInstalled.addListener(() => {
  chrome.storage.local.set({
    autoSave: false,
    notifications: true,
    apiUrl: API_BASE,
    _tk: '',
    defaultAudioSource: 'tab',
    autoDetectMeetings: true
  });
  chrome.action.setBadgeText({ text: '' });
});

// Reset stale recording state on startup (e.g. after extension reload)
chrome.runtime.onStartup.addListener(() => {
  recordingState = {
    status: 'idle',
    tabId: null,
    startTime: null,
    source: 'tab',
    meetingPlatform: null,
    meetingId: '',
    transcription: ''
  };
  chrome.storage.local.set({ recordingState: { status: 'idle' } });
  chrome.action.setBadgeText({ text: '' });
});

// ===== OFFSCREEN DOCUMENT LIFECYCLE =====

async function ensureOffscreenDocument() {
  if (offscreenDocCreated) return;

  try {
    // Check if offscreen document already exists
    const existingContexts = await chrome.runtime.getContexts({
      contextTypes: ['OFFSCREEN_DOCUMENT'],
      documentUrls: [chrome.runtime.getURL('offscreen.html')]
    });
    if (existingContexts.length > 0) {
      offscreenDocCreated = true;
      return;
    }
  } catch (e) {
    // getContexts might not be available in all Chrome versions
  }

  try {
    await chrome.offscreen.createDocument({
      url: 'offscreen.html',
      reasons: ['AUDIO_PLAYBACK'],
      justification: 'Capture tab audio for meeting transcription via WebSocket'
    });
    offscreenDocCreated = true;
  } catch (e) {
    // If it already exists, Chrome throws an error — that's fine
    if (e.message.includes('Only a single offscreen')) {
      offscreenDocCreated = true;
    } else {
      console.error('Failed to create offscreen document:', e);
      throw e;
    }
  }
}

async function closeOffscreenDocument() {
  try {
    await chrome.offscreen.closeDocument();
    offscreenDocCreated = false;
  } catch (e) {
    // Ignore if already closed
  }
}

// ===== TAB CAPTURE ORCHESTRATION =====

async function startRecording(tabId, source, meetingId) {
  if (recordingState.status !== 'idle') {
    return { success: false, error: 'Already recording' };
  }

  try {
    await ensureOffscreenDocument();

    // Get settings
    const settings = await chrome.storage.local.get(['_tk', 'apiUrl', 'defaultAudioSource']);
    const backendUrl = settings.apiUrl || API_BASE;
    const token = settings._tk || '';
    const audioSource = source || settings.defaultAudioSource || 'tab';

    // Start tab capture if requested
    if (audioSource === 'tab' || audioSource === 'both') {
      // Get MediaStream ID for the target tab
      const streamId = await chrome.tabCapture.getMediaStreamId({
        targetTabId: tabId
      });

      // Send stream ID to offscreen document
      await sendMessageToOffscreen({
        action: 'start-capture',
        streamId: streamId,
        backendUrl: backendUrl,
        token: token,
        meetingId: meetingId || ''
      });
    }

    // Start mic capture if requested
    if (audioSource === 'mic' || audioSource === 'both') {
      await sendMessageToOffscreen({
        action: 'start-mic',
        backendUrl: backendUrl,
        token: token,
        meetingId: meetingId || ''
      });
    }

    // Update recording state
    recordingState = {
      status: 'capturing',
      tabId: tabId,
      startTime: Date.now(),
      source: audioSource,
      meetingPlatform: null,
      meetingId: meetingId || '',
      transcription: ''
    };

    // Detect meeting platform from tab URL
    try {
      const tab = await chrome.tabs.get(tabId);
      const url = tab.url || '';
      if (url.includes('zoom.us')) recordingState.meetingPlatform = 'zoom';
      else if (url.includes('meet.google.com')) recordingState.meetingPlatform = 'google-meet';
      else if (url.includes('teams.microsoft.com')) recordingState.meetingPlatform = 'teams';
      else if (url.includes('webex.com')) recordingState.meetingPlatform = 'webex';
    } catch (e) {}

    // Persist state
    await chrome.storage.local.set({ recordingState: { ...recordingState } });

    // Show recording badge
    chrome.action.setBadgeText({ text: 'REC' });
    chrome.action.setBadgeBackgroundColor({ color: '#ef4444' });

    return { success: true };
  } catch (e) {
    return { success: false, error: e.message };
  }
}

async function stopRecording() {
  if (recordingState.status === 'idle') {
    // Still reset state even if idle (handles stale state)
    recordingState = {
      status: 'idle',
      tabId: null,
      startTime: null,
      source: 'tab',
      meetingPlatform: null,
      meetingId: '',
      transcription: ''
    };
    await chrome.storage.local.set({ recordingState: { ...recordingState } });
    chrome.action.setBadgeText({ text: '' });
    return;
  }

  // Tell offscreen to stop (ignore errors if offscreen is gone)
  try {
    await sendMessageToOffscreen({
      action: 'stop-capture',
      source: recordingState.source === 'both' ? 'both' : recordingState.source
    });
  } catch (e) {
    // Offscreen document may have been destroyed on reload — that's fine
  }

  // Reset state
  recordingState = {
    status: 'idle',
    tabId: null,
    startTime: null,
    source: 'tab',
    meetingPlatform: null,
    meetingId: '',
    transcription: ''
  };

  await chrome.storage.local.set({ recordingState: { ...recordingState } });

  // Clear badge
  chrome.action.setBadgeText({ text: '' });
}

async function pauseRecording() {
  if (recordingState.status !== 'capturing') return;

  await sendMessageToOffscreen({ action: 'pause-capture' });
  recordingState.status = 'paused';
  await chrome.storage.local.set({ recordingState: { ...recordingState } });

  chrome.action.setBadgeText({ text: '⏸' });
  chrome.action.setBadgeBackgroundColor({ color: '#f59e0b' });
}

async function resumeRecording() {
  if (recordingState.status !== 'paused') return;

  await sendMessageToOffscreen({ action: 'resume-capture' });
  recordingState.status = 'capturing';
  await chrome.storage.local.set({ recordingState: { ...recordingState } });

  chrome.action.setBadgeText({ text: 'REC' });
  chrome.action.setBadgeBackgroundColor({ color: '#ef4444' });
}

function sendMessageToOffscreen(message) {
  return new Promise((resolve) => {
    chrome.runtime.sendMessage(message, (response) => {
      if (chrome.runtime.lastError) {
        console.warn('Offscreen message error:', chrome.runtime.lastError.message);
        resolve({ success: false, error: chrome.runtime.lastError.message });
      } else {
        resolve(response || { success: true });
      }
    });
  });
}

// ===== MESSAGE ROUTING =====

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  switch (request.action) {
    case 'saveJob':
      handleSaveJob(request.data).then(sendResponse);
      return true;

    case 'getStats':
      getJobStats().then(sendResponse);
      return true;

    case 'start-recording':
      startRecording(request.tabId, request.source, request.meetingId).then(sendResponse);
      return true;

    case 'stop-recording':
      stopRecording().then(() => sendResponse({ success: true }));
      return true;

    case 'pause-recording':
      pauseRecording().then(() => sendResponse({ success: true }));
      return true;

    case 'resume-recording':
      resumeRecording().then(() => sendResponse({ success: true }));
      return true;

    case 'get-recording-state':
      sendResponse({ ...recordingState });
      return false;

    // STEALTH: Relay fetch calls from content script (avoids page-context detection)
    case 'fetch-suggestions':
      handleFetchSuggestions(request).then(sendResponse);
      return true;

    case 'capture-screenshot':
      handleCaptureScreenshot(request.tabId || sender?.tab?.id).then(sendResponse);
      return true;

    // Forward transcription/audio messages from offscreen to popup/content scripts
    case 'transcription-partial':
    case 'transcription-final':
    case 'transcription-error':
    case 'audio-level':
    case 'silence-warning':
    case 'capture-error':
    case 'ws-status':
    case 'auth-expired':
      // Store transcription
      if (request.action === 'transcription-partial' || request.action === 'transcription-final') {
        recordingState.transcription = request.text;
      }
      // These messages are forwarded automatically since they use chrome.runtime.sendMessage
      // which reaches all listeners. Just acknowledge.
      sendResponse({ received: true });
      return false;
  }
});

// ===== AUTO-STOP ON TAB CLOSE =====

chrome.tabs.onRemoved.addListener((tabId) => {
  if (recordingState.tabId === tabId && recordingState.status !== 'idle') {
    stopRecording();
    chrome.notifications.create({
      type: 'basic',
      iconUrl: 'icon128.png',
      title: 'Recording Stopped',
      message: 'The meeting tab was closed, so recording was automatically stopped.'
    });
  }
});

// ===== MEETING TAB DETECTION & AUTO-INJECTION =====

chrome.tabs.onUpdated.addListener(async (tabId, changeInfo, tab) => {
  if (changeInfo.status !== 'complete') return;

  const url = tab.url || '';
  const isMeetingUrl = url.includes('zoom.us/j') ||
                       url.includes('zoom.us/meeting') ||
                       url.includes('meet.google.com') ||
                       url.includes('teams.microsoft.com/l/meeting') ||
                       url.includes('webex.com');

  if (!isMeetingUrl) return;

  const settings = await chrome.storage.local.get(['autoDetectMeetings']);
  if (!settings.autoDetectMeetings) return;

  // Programmatically inject content script if not already injected
  try {
    await chrome.scripting.executeScript({
      target: { tabId: tabId },
      files: ['content.js']
    });
    await chrome.scripting.insertCSS({
      target: { tabId: tabId },
      files: ['content.css']
    });
  } catch (e) {
    // Content script may already be injected or tab may not allow it
  }
});

// ===== STEALTH: RELAY HANDLERS (content → background → backend) =====
// These handle API calls that content.js used to make directly from page context.
// By relaying through background, we avoid detection via PerformanceObserver/fetch patching.

async function handleFetchSuggestions(request) {
  try {
    const settings = await chrome.storage.local.get(['apiUrl', '_tk']);
    const baseUrl = settings.apiUrl || API_BASE;
    const token = settings._tk || '';

    const headers = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = 'Bearer ' + token;

    const response = await fetch(`${baseUrl}/shadow/suggestions`, { headers });
    if (response.ok) {
      const data = await response.json();
      return { suggestions: data.suggestions || [] };
    }
    return { suggestions: [] };
  } catch (e) {
    return { suggestions: [] };
  }
}

async function handleCaptureScreenshot(tabId) {
  try {
    const settings = await chrome.storage.local.get(['apiUrl', '_tk']);
    const baseUrl = settings.apiUrl || API_BASE;
    const token = settings._tk || '';

    // Capture visible tab as JPEG data URL
    const dataUrl = await chrome.tabs.captureVisibleTab(null, {
      format: 'jpeg',
      quality: 80
    });

    // Strip the data:image/jpeg;base64, prefix
    const base64 = dataUrl.split(',')[1];

    const headers = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = 'Bearer ' + token;

    const response = await fetch(`${baseUrl}/ocr`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ image_b64: base64 })
    });

    if (response.ok) {
      const data = await response.json();
      return { text: data.text || '', method: data.method || 'none' };
    }
    return { text: '', method: 'none' };
  } catch (e) {
    return { text: '', method: 'none', error: e.message };
  }
}

// ===== JOB TRACKING (existing functionality) =====

async function handleSaveJob(jobData) {
  try {
    const response = await fetch(`${API_BASE}/job-tracker/application`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        company: jobData.company,
        role: jobData.title,
        location: jobData.location,
        job_url: jobData.url,
        description: jobData.description,
        salary_range: jobData.salary,
        status: 'saved',
        source: jobData.platform
      })
    });

    if (response.ok) {
      return { success: true, message: 'Job saved' };
    } else {
      const error = await response.json();
      return { success: false, error: error.error || 'Failed to save' };
    }
  } catch (e) {
    console.error('Background save error:', e);
    return { success: false, error: 'Network error' };
  }
}

async function getJobStats() {
  try {
    const response = await fetch(`${API_BASE}/job-tracker/stats`);
    if (response.ok) {
      return await response.json();
    }
  } catch (e) {
    // Stats fetch error
  }
  return { total_jobs: 0, by_status: {} };
}

// Periodic health check (every 5 minutes)
setInterval(async () => {
  try {
    await fetch(`${API_BASE}/health`);
  } catch (e) {
    // Backend might be temporarily down
  }
}, 5 * 60 * 1000);