// Popup Script — Meeting-aware UI with recording controls and transcription
const API_BASE = 'http://localhost:8000';

// Meeting URL patterns
const MEETING_PATTERNS = [
  { match: 'zoom.us', name: 'Zoom', icon: '📹' },
  { match: 'meet.google.com', name: 'Google Meet', icon: '📺' },
  { match: 'teams.microsoft.com', name: 'Microsoft Teams', icon: '💼' },
  { match: 'webex.com', name: 'WebEx', icon: '🌐' }
];

let recordingState = { status: 'idle' };
let selectedSource = 'tab';
let timerInterval = null;
let recordingStartTime = null;

document.addEventListener('DOMContentLoaded', async () => {
  const statusDot = document.getElementById('statusDot');
  const statusText = document.getElementById('statusText');
  const errorMessage = document.getElementById('errorMessage');
  const jobsCount = document.getElementById('jobsCount');
  const appsCount = document.getElementById('appsCount');
  const openAppBtn = document.getElementById('openAppBtn');
  const viewJobsBtn = document.getElementById('viewJobsBtn');
  const settingsLink = document.getElementById('settingsLink');

  // Meeting elements
  const meetingSection = document.getElementById('meetingSection');
  const meetingIcon = document.getElementById('meetingIcon');
  const meetingPlatformName = document.getElementById('meetingPlatformName');
  const meetingIdEl = document.getElementById('meetingId');
  const meetingTimer = document.getElementById('meetingTimer');
  const startBtn = document.getElementById('startBtn');
  const pauseBtn = document.getElementById('pauseBtn');
  const stopBtn = document.getElementById('stopBtn');
  const activeControls = document.getElementById('activeControls');
  const sourceSelector = document.getElementById('sourceSelector');
  const transcriptionSection = document.getElementById('transcriptionSection');
  const transcriptionBox = document.getElementById('transcriptionBox');
  const volumeFill = document.getElementById('volumeFill');

  // Check connection
  async function checkConnection() {
    try {
      const response = await fetch(`${API_BASE}/health`);
      if (response.ok) {
        statusDot.classList.remove('disconnected');
        statusText.textContent = 'Connected';
        errorMessage.classList.remove('show');
        return true;
      }
    } catch (e) {}
    statusDot.classList.add('disconnected');
    statusText.textContent = 'Not connected';
    errorMessage.classList.add('show');
    return false;
  }

  // Detect if active tab is a meeting
  async function detectMeetingTab() {
    try {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      if (!tab || !tab.url) return null;

      const url = tab.url;
      for (const pattern of MEETING_PATTERNS) {
        if (url.includes(pattern.match)) {
          let meetingId = '';
          if (url.includes('zoom.us')) {
            const m = url.match(/zoom\.us\/j\/(\d+)/);
            if (m) meetingId = m[1];
          } else if (url.includes('meet.google.com')) {
            const m = url.match(/meet\.google\.com\/([a-z]{3}-[a-z]{4}-[a-z]{3})/) ||
                       url.match(/meet\.google\.com\/([a-z0-9-]+)/);
            if (m) meetingId = m[1];
          } else if (url.includes('teams.microsoft.com')) {
            const m = url.match(/teams\.microsoft\.com\/l\/meeting\/([\w-]+)/);
            if (m) meetingId = m[1];
          }

          return {
            platform: pattern.name,
            icon: pattern.icon,
            meetingId: meetingId,
            tabId: tab.id
          };
        }
      }
    } catch (e) {}
    return null;
  }

  // Load stats
  async function loadStats() {
    try {
      const settings = await chrome.storage.local.get(['apiUrl', '_tk']);
      const baseUrl = settings.apiUrl || API_BASE;
      const token = settings._tk || '';
      const headers = {};
      if (token) headers['Authorization'] = 'Bearer ' + token;

      const response = await fetch(`${baseUrl}/job-tracker/stats`, { headers });
      if (response.ok) {
        const data = await response.json();
        jobsCount.textContent = data.total_jobs || data.total_saved || 0;
        appsCount.textContent = data.by_status?.applied || 0;
      } else {
        jobsCount.textContent = '-';
        appsCount.textContent = '-';
      }
    } catch (e) {
      jobsCount.textContent = '-';
      appsCount.textContent = '-';
    }
  }

  // Get recording state from background
  async function loadRecordingState() {
    return new Promise((resolve) => {
      chrome.runtime.sendMessage({ action: 'get-recording-state' }, (state) => {
        if (state) {
          recordingState = state;
          if (state.startTime) recordingStartTime = state.startTime;
          resolve(state);
        } else {
          resolve({ status: 'idle' });
        }
      });
    });
  }

  // Update UI based on recording state
  function updateRecordingUI() {
    if (recordingState.status === 'idle') {
      startBtn.style.display = 'block';
      activeControls.style.display = 'none';
      sourceSelector.style.display = 'flex';
      transcriptionSection.classList.remove('active');
      stopTimer();
    } else if (recordingState.status === 'capturing') {
      startBtn.style.display = 'none';
      activeControls.style.display = 'flex';
      pauseBtn.textContent = 'Pause';
      pauseBtn.className = 'record-btn record-btn-pause';
      sourceSelector.style.display = 'none';
      transcriptionSection.classList.add('active');
      startTimer();
    } else if (recordingState.status === 'paused') {
      startBtn.style.display = 'none';
      activeControls.style.display = 'flex';
      pauseBtn.textContent = 'Resume';
      pauseBtn.className = 'record-btn record-btn-resume';
      sourceSelector.style.display = 'none';
      transcriptionSection.classList.add('active');
      stopTimer();
    }
  }

  // Timer
  function startTimer() {
    stopTimer();
    timerInterval = setInterval(() => {
      if (recordingStartTime) {
        const elapsed = Math.floor((Date.now() - recordingStartTime) / 1000);
        const mins = Math.floor(elapsed / 60).toString().padStart(2, '0');
        const secs = (elapsed % 60).toString().padStart(2, '0');
        meetingTimer.textContent = `${mins}:${secs}`;
      }
    }, 1000);
  }

  function stopTimer() {
    if (timerInterval) {
      clearInterval(timerInterval);
      timerInterval = null;
    }
  }

  // Source selector
  sourceSelector.querySelectorAll('.source-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      sourceSelector.querySelectorAll('.source-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      selectedSource = btn.dataset.source;
    });
  });

  // Recording controls
  startBtn.addEventListener('click', () => {
    chrome.runtime.sendMessage({
      action: 'start-recording',
      tabId: meeting ? meeting.tabId : null,
      source: selectedSource,
      meetingId: meeting ? meeting.meetingId : ''
    }, (response) => {
      if (response && response.success) {
        recordingState.status = 'capturing';
        recordingStartTime = Date.now();
        updateRecordingUI();
      } else if (response && response.error === 'Already recording') {
        // Stale state from previous session — force stop then retry
        chrome.runtime.sendMessage({ action: 'stop-recording' }, () => {
          setTimeout(() => startBtn.click(), 500);
        });
      } else {
        errorMessage.textContent = response?.error || 'Failed to start recording';
        errorMessage.classList.add('show');
        setTimeout(() => errorMessage.classList.remove('show'), 3000);
      }
    });
  });

  pauseBtn.addEventListener('click', () => {
    if (recordingState.status === 'capturing') {
      chrome.runtime.sendMessage({ action: 'pause-recording' }, () => {
        recordingState.status = 'paused';
        updateRecordingUI();
      });
    } else if (recordingState.status === 'paused') {
      chrome.runtime.sendMessage({ action: 'resume-recording' }, () => {
        recordingState.status = 'capturing';
        updateRecordingUI();
      });
    }
  });

  stopBtn.addEventListener('click', () => {
    chrome.runtime.sendMessage({ action: 'stop-recording' }, () => {
      recordingState = { status: 'idle' };
      recordingStartTime = null;
      meetingTimer.textContent = '00:00';
      transcriptionBox.innerHTML = '<div class="transcription-empty">Waiting for audio...</div>';
      updateRecordingUI();
    });
  });

  // Listen for messages from background (transcription, audio level)
  chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    switch (message.action) {
      case 'transcription-partial':
        transcriptionSection.classList.add('active');
        let partialLine = transcriptionBox.querySelector('.transcription-partial');
        if (!partialLine) {
          const empty = transcriptionBox.querySelector('.transcription-empty');
          if (empty) empty.remove();
          partialLine = document.createElement('div');
          partialLine.className = 'transcription-partial';
          transcriptionBox.appendChild(partialLine);
        }
        partialLine.textContent = message.text;
        transcriptionBox.scrollTop = transcriptionBox.scrollHeight;
        break;

      case 'transcription-final':
        let existingPartial = transcriptionBox.querySelector('.transcription-partial');
        if (existingPartial) {
          existingPartial.className = '';
          existingPartial.textContent = message.text;
        } else {
          const empty = transcriptionBox.querySelector('.transcription-empty');
          if (empty) empty.remove();
          const line = document.createElement('div');
          line.textContent = message.text;
          transcriptionBox.appendChild(line);
        }
        transcriptionBox.scrollTop = transcriptionBox.scrollHeight;
        break;

      case 'audio-level':
        const percentage = Math.min(100, Math.max(0, message.rms * 400));
        volumeFill.style.width = percentage + '%';
        break;

      case 'capture-error':
        errorMessage.textContent = message.error;
        errorMessage.classList.add('show');
        recordingState = { status: 'idle' };
        updateRecordingUI();
        break;

      case 'auth-expired':
        errorMessage.textContent = 'Token expired. Update in Settings.';
        errorMessage.classList.add('show');
        recordingState = { status: 'idle' };
        updateRecordingUI();
        break;
    }
    sendResponse({ received: true });
  });

  // Navigation buttons
  openAppBtn.addEventListener('click', () => {
    chrome.tabs.create({ url: 'http://localhost:8000/static' });
  });

  viewJobsBtn.addEventListener('click', () => {
    chrome.tabs.create({ url: 'http://localhost:8000/static/job-tracker.html' });
  });

  settingsLink.addEventListener('click', () => {
    chrome.runtime.openOptionsPage();
  });

  // Initialize
  await checkConnection();
  const meeting = await detectMeetingTab();

  if (meeting) {
    meetingSection.classList.add('active');
    meetingIcon.textContent = meeting.icon;
    meetingPlatformName.textContent = meeting.platform;
    meetingIdEl.textContent = meeting.meetingId ? `ID: ${meeting.meetingId}` : '';

    // Load current recording state
    await loadRecordingState();
    updateRecordingUI();
  }

  await loadStats();
});