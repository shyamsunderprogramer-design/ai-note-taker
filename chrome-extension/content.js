// Content Script — Full Stealth Build
// No identifiable IDs, classes, globals, or console output.
// Uses closed Shadow DOM to prevent page scripts from detecting the overlay.
// All network calls relayed through background service worker (not page context).
(function() {
    'use strict';

    // ===== STEALTH: Randomized prefix generated per session =====
    // No predictable "ant-" prefix. Changes every page load.
    const _p = '_' + Math.random().toString(36).substring(2, 8);
    const _s = _p + '_'; // short prefix for IDs/classes

    // ===== STEALTH: No global property detection =====
    // Use a Symbol (not enumerable, not discoverable by `in` or `for..in`)
    const _injected = Symbol('ext');
    if (window[_injected]) return;
    window[_injected] = true;

    // ===== STEALTH: No console output =====
    // All console.log/error removed. Use silent error handling only.

    // State
    let overlayVisible = false;
    let currentMeetingInfo = null;
    let suggestions = [];
    let recordingState = { status: 'idle', source: 'tab' };
    let transcriptionText = '';
    let recordingStartTime = null;
    let timerInterval = null;
    let selectedSource = 'tab';
    let volumeLevel = 0;
    let shadowHost = null;
    let shadowRoot = null;
    let lastSaveTime = 0;

    // ===== STEALTH: Anti-detection watchdog =====
    // Detects if the page tries to probe for extension fingerprints.
    // If detected, self-destructs the overlay to avoid exposure.
    const _origQSA = Document.prototype.querySelectorAll;
    const _origGEID = Document.prototype.getElementById;
    const _origQS = Document.prototype.querySelector;
    const _origQSAAll = Element.prototype.querySelectorAll;
    const _origQSAll = Element.prototype.querySelector;

    let _selfDestruct = false;
    let _probeCount = 0;

    // Monitor DOM mutations that look like fingerprinting probes
    // (e.g., page script creating a MutationObserver on our host element)
    function _checkForProbes() {
        _probeCount++;
        // If we detect suspicious probing patterns, self-destruct
        if (_probeCount > 500) {
            // Extremely high probe rate suggests automated scanning
            _selfDestruct = true;
        }
        if (_selfDestruct && shadowHost && shadowHost.parentNode) {
            shadowHost.remove();
            overlayVisible = false;
            shadowHost = null;
            shadowRoot = null;
        }
    }

    // Watch for the page trying to access chrome.runtime (extension detection)
    try {
        const _origGetter = Object.getOwnPropertyDescriptor(Window.prototype, 'chrome')?.get;
        if (_origGetter) {
            Object.defineProperty(window, 'chrome', {
                get: function() {
                    _probeCount += 10; // Significant probe activity
                    return _origGetter.call(this);
                },
                configurable: true
            });
        }
    } catch (e) {}

    // Periodic cleanup check — remove overlay if self-destruct triggered
    setInterval(() => {
        if (_selfDestruct && shadowHost && shadowHost.parentNode) {
            shadowHost.remove();
            overlayVisible = false;
            shadowHost = null;
            shadowRoot = null;
        }
    }, 2000);

    // ===== STEALTH: All API calls go through background (not page context) =====
    // Also prevent page from detecting our fetch calls via PerformanceObserver
    try {
        // Override PerformanceObserver to filter out our localhost connections
        const _origPO = window.PerformanceObserver;
        if (_origPO) {
            window.PerformanceObserver = function(callback) {
                const wrappedCallback = function(entries) {
                    // Filter out entries to localhost (our backend)
                    const filtered = entries.filter?.(entry => {
                        const name = entry.name || '';
                        return !name.includes('127.0.0.1') && !name.includes('localhost');
                    });
                    if (filtered) {
                        callback(filtered);
                    }
                };
                return new _origPO(wrappedCallback);
            };
            window.PerformanceObserver.prototype = _origPO.prototype;
            window.PerformanceObserver.supportedEntryTypes = _origPO.supportedEntryTypes;
        }
    } catch (e) {}
    // Never call fetch() or XMLHttpRequest from the content script to localhost.
    // Relay everything through chrome.runtime.sendMessage.

    function sendToBackground(action, data) {
        return new Promise((resolve) => {
            chrome.runtime.sendMessage({ action, ...data }, (response) => {
                if (chrome.runtime.lastError) {
                    resolve(null);
                } else {
                    resolve(response);
                }
            });
        });
    }

    // ==================== JOB PAGE DETECTION ====================

    function detectJobPage() {
        const url = window.location.href;
        if (url.includes('linkedin.com/jobs')) return 'linkedin';
        if (url.includes('indeed.com')) return 'indeed';
        if (url.includes('glassdoor.com')) return 'glassdoor';
        if (url.includes('greenhouse.io')) return 'greenhouse';
        if (url.includes('lever.co')) return 'lever';
        if (url.includes('workday.com')) return 'workday';
        if (url.includes('icims.com')) return 'icims';
        return null;
    }

    // ==================== MEETING PAGE DETECTION ====================

    function detectMeetingPlatform() {
        const url = window.location.href;
        const title = document.title.toLowerCase();

        if (url.includes('zoom.us/j') || url.includes('zoom.us/meeting') || title.includes('zoom')) {
            return 'zoom';
        }
        if (url.includes('meet.google.com') || title.includes('google meet')) {
            return 'google-meet';
        }
        if (url.includes('teams.microsoft.com') || title.includes('microsoft teams')) {
            return 'teams';
        }
        if (url.includes('webex.com')) {
            return 'webex';
        }
        return null;
    }

    function isMeetingActive() {
        const platform = detectMeetingPlatform();
        if (!platform) return false;

        try {
            switch (platform) {
                case 'zoom':
                    return document.querySelector('[aria-label*="Leave"]') !== null ||
                           document.querySelector('[class*="leave-button"]') !== null;
                case 'google-meet':
                    return document.querySelector('[class*="pill"]') !== null ||
                           document.querySelector('[aria-label*="Leave"]') !== null;
                case 'teams':
                    return document.querySelector('[data-is-meeting]') !== null ||
                           document.querySelector('[aria-label*="call"]') !== null;
                case 'webex':
                    return document.querySelector('[class*="leave"]') !== null;
            }
        } catch (e) {}
        return false;
    }

    function extractMeetingInfo() {
        const platform = detectMeetingPlatform();
        if (!platform) return null;

        const info = {
            platform: platform,
            url: window.location.href,
            title: document.title,
            started_at: new Date().toISOString(),
            participants: 0,
            meeting_id: ''
        };

        try {
            const url = window.location.href;
            switch (platform) {
                case 'zoom':
                    const zoomMatch = url.match(/zoom\.us\/j\/(\d+)/);
                    if (zoomMatch) info.meeting_id = zoomMatch[1];
                    break;
                case 'google-meet':
                    const meetMatch = url.match(/meet\.google\.com\/([a-z-]+)/);
                    if (meetMatch) info.meeting_id = meetMatch[1];
                    break;
                case 'teams':
                    const teamsMatch = url.match(/teams\.microsoft.com\/l\/meeting\/([\w-]+)/);
                    if (teamsMatch) info.meeting_id = teamsMatch[1];
                    break;
            }

            const participantElements = document.querySelectorAll('[class*="avatar"]');
            if (participantElements.length > 0) {
                info.participants = participantElements.length;
            }
        } catch (e) {}

        return info;
    }

    // ==================== JOB DATA EXTRACTION ====================

    function extractJobData(platform) {
        const data = {
            platform: platform,
            url: window.location.href,
            title: '',
            company: '',
            location: '',
            description: '',
            salary: '',
            extracted_at: new Date().toISOString()
        };

        try {
            switch (platform) {
                case 'linkedin':
                    data.title = document.querySelector('h1')?.textContent?.trim() ||
                                document.querySelector('.top-card-layout__title')?.textContent?.trim() || '';
                    data.company = document.querySelector('.top-card-layout__entity-info a')?.textContent?.trim() ||
                                   document.querySelector('[class*="company"]')?.textContent?.trim() || '';
                    data.location = document.querySelector('.top-card-layout__entity-info')?.textContent?.match(/\w+,?\s*\w+\s*\d*/)?.[0] || '';
                    data.description = document.querySelector('.description__text')?.textContent?.trim() ||
                                       document.querySelector('[class*="description"]')?.textContent?.trim() || '';
                    break;
                case 'indeed':
                    data.title = document.querySelector('h1')?.textContent?.trim() ||
                                document.querySelector('.jobsearch-JobInfoHeader-title')?.textContent?.trim() || '';
                    data.company = document.querySelector('[data-testid="company-name"]')?.textContent?.trim() ||
                                   document.querySelector('[class*="companyName"]')?.textContent?.trim() || '';
                    data.location = document.querySelector('[data-testid="job-location"]')?.textContent?.trim() || '';
                    data.description = document.querySelector('[data-testid="job-description-text"]')?.textContent?.trim() ||
                                       document.querySelector('#jobDescriptionText')?.textContent?.trim() || '';
                    data.salary = document.querySelector('[data-testid="job-salary"]')?.textContent?.trim() || '';
                    break;
                case 'glassdoor':
                    data.title = document.querySelector('h1')?.textContent?.trim() || '';
                    data.company = document.querySelector('[data-test="employer-name"]')?.textContent?.trim() || '';
                    data.location = document.querySelector('[data-test="location"]')?.textContent?.trim() || '';
                    data.description = document.querySelector('[data-test="job-description"]')?.textContent?.trim() || '';
                    break;
                case 'greenhouse':
                case 'lever':
                    data.title = document.querySelector('h1')?.textContent?.trim() || '';
                    data.company = document.querySelector('.company-name')?.textContent?.trim() ||
                                   document.querySelector('[class*="company"]')?.textContent?.trim() || '';
                    data.location = document.querySelector('.location')?.textContent?.trim() || '';
                    data.description = document.querySelector('.description')?.textContent?.trim() ||
                                       document.body.innerText.substring(0, 2000);
                    break;
                case 'workday':
                    data.title = document.querySelector('[data-automation-id="jobTitle"]')?.textContent?.trim() || '';
                    data.company = document.querySelector('[data-automation-id="companyName"]')?.textContent?.trim() || '';
                    data.location = document.querySelector('[data-automation-id="jobLocation"]')?.textContent?.trim() || '';
                    data.description = document.querySelector('[data-automation-id="jobDescription"]')?.textContent?.trim() || '';
                    break;
                case 'icims':
                    data.title = document.querySelector('.iCIMS_SubHeader span')?.textContent?.trim() ||
                                 document.querySelector('[class*="jobTitle"]')?.textContent?.trim() || '';
                    data.company = document.querySelector('[class*="companyName"]')?.textContent?.trim() || '';
                    data.location = document.querySelector('[class*="location"]')?.textContent?.trim() || '';
                    data.description = document.querySelector('[class*="description"]')?.textContent?.trim() || '';
                    break;
            }
        } catch (e) {}

        return data;
    }

    // ==================== RECORDING CONTROL HANDLERS ====================

    async function startRecording() {
        const meetingInfo = extractMeetingInfo();
        const meetingId = meetingInfo?.meeting_id || '';

        const response = await sendToBackground('start-recording', {
            tabId: null,
            source: selectedSource,
            meetingId: meetingId
        });

        if (response && response.success) {
            recordingState.status = 'capturing';
            recordingStartTime = Date.now();
            updateRecordingUI();
            startTimer();
            showOverlayNotification('Recording started', 'success');
        } else {
            showOverlayNotification(response?.error || 'Failed to start recording', 'error');
        }
    }

    async function stopRecording() {
        await sendToBackground('stop-recording', {});
        recordingState.status = 'idle';
        recordingStartTime = null;
        stopTimer();
        updateRecordingUI();
        showOverlayNotification('Recording stopped', 'info');
    }

    async function pauseRecording() {
        await sendToBackground('pause-recording', {});
        recordingState.status = 'paused';
        stopTimer();
        updateRecordingUI();
    }

    async function resumeRecording() {
        await sendToBackground('resume-recording', {});
        recordingState.status = 'capturing';
        startTimer();
        updateRecordingUI();
    }

    function startTimer() {
        stopTimer();
        timerInterval = setInterval(() => {
            const timerEl = shadowRoot?.getElementById?.(_s + 'timer');
            if (recordingStartTime && timerEl) {
                const elapsed = Math.floor((Date.now() - recordingStartTime) / 1000);
                const mins = Math.floor(elapsed / 60).toString().padStart(2, '0');
                const secs = (elapsed % 60).toString().padStart(2, '0');
                timerEl.textContent = `${mins}:${secs}`;
            }
        }, 1000);
    }

    function stopTimer() {
        if (timerInterval) {
            clearInterval(timerInterval);
            timerInterval = null;
        }
    }

    function updateRecordingUI() {
        if (!shadowRoot) return;
        const startBtn = shadowRoot.getElementById(_s + 'recStart');
        const pauseBtn = shadowRoot.getElementById(_s + 'recPause');
        const stopBtn = shadowRoot.getElementById(_s + 'recStop');
        const sourceSel = shadowRoot.getElementById(_s + 'srcSel');
        const indicator = shadowRoot.getElementById(_s + 'recInd');

        if (!startBtn) return;

        if (recordingState.status === 'idle') {
            startBtn.style.display = 'block';
            startBtn.textContent = 'Start Recording';
            startBtn.className = _s + 'rec-btn ' + _s + 'rec-start';
            pauseBtn.style.display = 'none';
            stopBtn.style.display = 'none';
            sourceSel.style.display = 'flex';
            indicator.style.display = 'none';
        } else if (recordingState.status === 'capturing') {
            startBtn.style.display = 'none';
            pauseBtn.style.display = 'block';
            pauseBtn.textContent = 'Pause';
            pauseBtn.className = _s + 'rec-btn ' + _s + 'rec-pause';
            stopBtn.style.display = 'block';
            sourceSel.style.display = 'none';
            indicator.style.display = 'flex';
        } else if (recordingState.status === 'paused') {
            startBtn.style.display = 'none';
            pauseBtn.style.display = 'block';
            pauseBtn.textContent = 'Resume';
            pauseBtn.className = _s + 'rec-btn ' + _s + 'rec-resume';
            stopBtn.style.display = 'block';
            sourceSel.style.display = 'none';
            indicator.style.display = 'flex';
        }
    }

    // ==================== STEALTH OVERLAY (Closed Shadow DOM) ====================

    function createOverlay() {
        if (shadowHost && shadowHost.parentNode) return shadowHost;

        // Create host element with no identifiable attributes
        shadowHost = document.createElement('div');
        // STEALTH: No ID, no class, random style to blend in
        shadowHost.style.cssText = 'position:fixed;top:0;left:0;width:0;height:0;pointer-events:none;z-index:2147483647;';

        // STEALTH: Closed shadow root — page scripts CANNOT peek inside
        shadowRoot = shadowHost.attachShadow({ mode: 'closed' });

        // Styles inside shadow (completely invisible to page)
        const style = document.createElement('style');
        style.textContent = `
            .${_s}overlay {
                position: fixed;
                top: 20px; right: 20px;
                width: 320px; max-height: 500px;
                background: linear-gradient(135deg, rgba(30,30,40,0.95), rgba(20,20,30,0.95));
                border-radius: 12px;
                box-shadow: 0 8px 32px rgba(0,0,0,0.4);
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                color: #fff; font-size: 13px;
                backdrop-filter: blur(10px);
                border: 1px solid rgba(255,255,255,0.1);
                overflow: hidden; pointer-events: auto;
                transition: all 0.3s ease;
            }
            .${_s}overlay.minimized { max-height: 48px; overflow: hidden; }
            .${_s}overlay.minimized .${_s}content,
            .${_s}overlay.minimized .${_s}footer { display: none; }
            .${_s}header {
                display: flex; justify-content: space-between; align-items: center;
                padding: 12px 16px;
                background: rgba(255,255,255,0.05);
                border-bottom: 1px solid rgba(255,255,255,0.1);
            }
            .${_s}title { display: flex; align-items: center; gap: 8px; font-weight: 600; font-size: 14px; }
            .${_s}controls { display: flex; gap: 4px; }
            .${_s}ctrl-btn {
                width: 28px; height: 28px; border: none;
                background: rgba(255,255,255,0.1); border-radius: 6px;
                color: #fff; cursor: pointer;
                display: flex; align-items: center; justify-content: center;
                font-size: 14px; transition: background 0.2s;
            }
            .${_s}ctrl-btn:hover { background: rgba(255,255,255,0.2); }
            .${_s}dot {
                width: 8px; height: 8px; border-radius: 50%;
                background: #22c55e; animation: ${_s}pulse 2s infinite;
            }
            @keyframes ${_s}pulse { 0%,100%{opacity:1} 50%{opacity:.5} }
            .${_s}content { max-height: 400px; overflow-y: auto; padding: 12px; }
            .${_s}trans-panel { background: rgba(0,0,0,0.3); border-radius: 8px; margin-bottom: 12px; overflow: hidden; }
            .${_s}trans-header {
                padding: 8px 12px; font-weight: 500; color: #a0a0a0;
                font-size: 12px; display: flex; justify-content: space-between; align-items: center;
            }
            .${_s}timer { font-size: 11px; color: #ef4444; font-weight: 600; }
            .${_s}trans-body {
                max-height: 120px; overflow-y: auto; padding: 8px 12px;
                font-size: 13px; line-height: 1.5; color: #e0e0e0;
            }
            .${_s}trans-body::-webkit-scrollbar { width: 4px; }
            .${_s}trans-body::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.2); border-radius: 2px; }
            .${_s}partial { color: #22c55e; font-style: italic; }
            .${_s}empty { color: #666; font-style: italic; text-align: center; padding: 12px; }
            .${_s}vol-bar { height: 3px; background: rgba(255,255,255,0.1); border-radius: 2px; overflow: hidden; margin-top: 4px; }
            .${_s}vol-fill { height: 100%; background: linear-gradient(90deg, #22c55e, #3b82f6); border-radius: 2px; transition: width 0.1s; width: 0%; }
            .${_s}rec-controls { display: flex; flex-wrap: wrap; gap: 6px; padding: 10px 0 4px; }
            .${_s}rec-btn {
                flex: 1; min-width: 80px; padding: 8px 12px;
                border: none; border-radius: 6px; font-size: 12px;
                font-weight: 600; cursor: pointer; transition: all 0.2s;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }
            .${_s}rec-start { background: linear-gradient(135deg, #ef4444, #dc2626); color: white; }
            .${_s}rec-start:hover { background: linear-gradient(135deg, #dc2626, #b91c1c); }
            .${_s}rec-stop { background: rgba(239,68,68,0.2); color: #ef4444; border: 1px solid rgba(239,68,68,0.4); }
            .${_s}rec-pause { background: rgba(245,158,11,0.2); color: #f59e0b; border: 1px solid rgba(245,158,11,0.4); }
            .${_s}rec-resume { background: rgba(34,197,94,0.2); color: #22c55e; border: 1px solid rgba(34,197,94,0.4); }
            .${_s}src-sel { display: flex; gap: 4px; width: 100%; padding: 4px 0; }
            .${_s}src-btn {
                flex: 1; padding: 6px 8px;
                border: 1px solid rgba(255,255,255,0.15);
                background: rgba(255,255,255,0.05); color: #aaa;
                border-radius: 4px; font-size: 11px; cursor: pointer;
                transition: all 0.2s; font-family: inherit;
            }
            .${_s}src-btn.active { background: rgba(59,130,246,0.2); color: #3b82f6; border-color: rgba(59,130,246,0.4); }
            .${_s}src-btn:hover { background: rgba(255,255,255,0.1); }
            .${_s}sug-panel { background: rgba(255,255,255,0.05); border-radius: 8px; margin-bottom: 12px; }
            .${_s}sug-header { padding: 8px 12px; font-weight: 500; color: #a0a0a0; font-size: 12px; }
            .${_s}sug-list { padding: 8px 12px; }
            .${_s}sug-empty { color: #666; font-style: italic; text-align: center; padding: 12px; }
            .${_s}sug-item {
                padding: 8px 10px; background: rgba(59,130,246,0.15);
                border-left: 3px solid #3b82f6; border-radius: 0 6px 6px 0;
                margin-bottom: 8px; animation: ${_s}slideIn 0.3s ease;
            }
            @keyframes ${_s}slideIn { from{opacity:0;transform:translateX(20px)} to{opacity:1;transform:translateX(0)} }
            .${_s}info { background: rgba(255,255,255,0.03); border-radius: 8px; padding: 12px; }
            .${_s}info-row { display: flex; justify-content: space-between; margin-bottom: 6px; }
            .${_s}info-row:last-child { margin-bottom: 0; }
            .${_s}info-label { color: #888; }
            .${_s}info-value { color: #fff; font-weight: 500; max-width: 180px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
            .${_s}footer { padding: 10px 16px; background: rgba(255,255,255,0.03); border-top: 1px solid rgba(255,255,255,0.05); }
            .${_s}rec-ind { display: flex; align-items: center; gap: 8px; color: #ef4444; font-size: 12px; font-weight: 500; }
            .${_s}rec-dot { width: 8px; height: 8px; background: #ef4444; border-radius: 50%; animation: ${_s}blink 1s infinite; }
            @keyframes ${_s}blink { 0%,100%{opacity:1} 50%{opacity:.3} }
            .${_s}notif {
                position: absolute; top: 50px; right: 10px; left: 10px;
                padding: 10px; border-radius: 6px; color: white;
                font-size: 12px; font-weight: 500;
            }
            .${_s}notif-success { background: rgba(34,197,94,0.9); }
            .${_s}notif-error { background: rgba(239,68,68,0.9); }
            .${_s}notif-warning { background: rgba(245,158,11,0.9); }
            .${_s}notif-info { background: rgba(59,130,246,0.9); }
        `;
        shadowRoot.appendChild(style);

        // Overlay container
        const overlay = document.createElement('div');
        overlay.className = _s + 'overlay';
        overlay.innerHTML = `
            <div class="${_s}header">
                <div class="${_s}title">
                    <span style="font-size:18px">📝</span>
                    <span>Notes</span>
                    <span class="${_s}dot"></span>
                </div>
                <div class="${_s}controls">
                    <button class="${_s}ctrl-btn" id="${_s}toggleSug" title="Toggle">💡</button>
                    <button class="${_s}ctrl-btn" id="${_s}screenshot" title="Screenshot">📸</button>
                    <button class="${_s}ctrl-btn" id="${_s}minimize" title="Min">➖</button>
                    <button class="${_s}ctrl-btn" id="${_s}close" title="Close">✕</button>
                </div>
            </div>
            <div class="${_s}content">
                <div class="${_s}trans-panel">
                    <div class="${_s}trans-header">
                        <span>Transcription</span>
                        <span class="${_s}timer" id="${_s}timer">00:00</span>
                    </div>
                    <div class="${_s}trans-body" id="${_s}transBody">
                        <div class="${_s}empty">Waiting for audio...</div>
                    </div>
                    <div class="${_s}vol-bar"><div class="${_s}vol-fill" id="${_s}volFill"></div></div>
                </div>
                <div class="${_s}rec-controls">
                    <div class="${_s}src-sel" id="${_s}srcSel">
                        <button class="${_s}src-btn active" data-source="tab">Tab</button>
                        <button class="${_s}src-btn" data-source="mic">Mic</button>
                        <button class="${_s}src-btn" data-source="both">Both</button>
                    </div>
                    <button class="${_s}rec-btn ${_s}rec-start" id="${_s}recStart">Start</button>
                    <button class="${_s}rec-btn ${_s}rec-pause" id="${_s}recPause" style="display:none">Pause</button>
                    <button class="${_s}rec-btn ${_s}rec-stop" id="${_s}recStop" style="display:none">Stop</button>
                </div>
                <div class="${_s}sug-panel" id="${_s}sugPanel">
                    <div class="${_s}sug-header"><span>Suggestions</span></div>
                    <div class="${_s}sug-list" id="${_s}sugList">
                        <div class="${_s}sug-empty">Listening...</div>
                    </div>
                </div>
                <div class="${_s}info">
                    <div class="${_s}info-row"><span class="${_s}info-label">Meeting:</span><span class="${_s}info-value" id="${_s}mtgTitle">-</span></div>
                    <div class="${_s}info-row"><span class="${_s}info-label">Platform:</span><span class="${_s}info-value" id="${_s}mtgPlatform">-</span></div>
                    <div class="${_s}info-row"><span class="${_s}info-label">Started:</span><span class="${_s}info-value" id="${_s}mtgStarted">-</span></div>
                </div>
            </div>
            <div class="${_s}footer">
                <div class="${_s}rec-ind" id="${_s}recInd" style="display:none">
                    <span class="${_s}rec-dot"></span><span>REC</span>
                </div>
            </div>
        `;
        shadowRoot.appendChild(overlay);
        document.body.appendChild(shadowHost);

        // Wire up controls (inside shadow)
        shadowRoot.getElementById(_s + 'minimize').addEventListener('click', () => {
            overlay.classList.add('minimized');
        });
        shadowRoot.getElementById(_s + 'close').addEventListener('click', () => {
            if (recordingState.status !== 'idle') stopRecording();
            shadowHost.remove();
            overlayVisible = false;
            shadowHost = null;
            shadowRoot = null;
        });
        shadowRoot.getElementById(_s + 'toggleSug').addEventListener('click', () => {
            const panel = shadowRoot.getElementById(_s + 'sugPanel');
            panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
        });
        shadowRoot.getElementById(_s + 'screenshot').addEventListener('click', captureAndSendScreenshot);

        // Recording buttons
        shadowRoot.getElementById(_s + 'recStart').addEventListener('click', startRecording);
        shadowRoot.getElementById(_s + 'recPause').addEventListener('click', () => {
            if (recordingState.status === 'capturing') pauseRecording();
            else if (recordingState.status === 'paused') resumeRecording();
        });
        shadowRoot.getElementById(_s + 'recStop').addEventListener('click', stopRecording);

        // Source selector
        overlay.querySelectorAll('.' + _s + 'src-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                overlay.querySelectorAll('.' + _s + 'src-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                selectedSource = btn.dataset.source;
            });
        });

        return shadowHost;
    }

    async function captureAndSendScreenshot() {
        // STEALTH: Screenshot is relayed through background, not fetched from page context
        // This is a simplified version — the actual capture happens via chrome API in background
        try {
            await sendToBackground('capture-screenshot', {
                meetingUrl: window.location.href,
                platform: detectMeetingPlatform()
            });
        } catch (e) {}
    }

    function showOverlayNotification(message, type) {
        if (!shadowRoot) return;
        const overlay = shadowRoot.querySelector('.' + _s + 'overlay');
        if (!overlay) return;

        const notif = document.createElement('div');
        notif.className = _s + 'notif ' + _s + 'notif-' + type;
        notif.textContent = message;
        overlay.appendChild(notif);
        setTimeout(() => notif.remove(), 3000);
    }

    function updateTranscriptionDisplay(text, isFinal) {
        if (!shadowRoot) return;
        const body = shadowRoot.getElementById(_s + 'transBody');
        if (!body) return;

        transcriptionText = text;

        if (isFinal) {
            let partialLine = body.querySelector('.' + _s + 'partial');
            if (partialLine) {
                partialLine.className = '';
                partialLine.textContent = text;
            } else {
                const empty = body.querySelector('.' + _s + 'empty');
                if (empty) empty.remove();
                const line = document.createElement('div');
                line.textContent = text;
                body.appendChild(line);
            }
        } else {
            let partialLine = body.querySelector('.' + _s + 'partial');
            if (!partialLine) {
                const empty = body.querySelector('.' + _s + 'empty');
                if (empty) empty.remove();
                partialLine = document.createElement('div');
                partialLine.className = _s + 'partial';
                body.appendChild(partialLine);
            }
            partialLine.textContent = text;
        }
        body.scrollTop = body.scrollHeight;
    }

    function updateVolumeBar(rms) {
        if (!shadowRoot) return;
        const fill = shadowRoot.getElementById(_s + 'volFill');
        if (!fill) return;
        const percentage = Math.min(100, Math.max(0, rms * 400));
        fill.style.width = percentage + '%';
    }

    function updateOverlaySuggestions(newSuggestions) {
        if (!shadowRoot) return;
        const list = shadowRoot.getElementById(_s + 'sugList');
        if (!list) return;

        suggestions = [...newSuggestions, ...suggestions].slice(0, 10);

        if (suggestions.length === 0) {
            list.innerHTML = `<div class="${_s}sug-empty">Listening...</div>`;
            return;
        }

        list.innerHTML = suggestions.map(s => `
            <div class="${_s}sug-item">
                <div style="font-size:10px;text-transform:uppercase;color:#888;margin-bottom:4px">${s.type || 'general'}</div>
                <div style="font-size:13px;line-height:1.4">${s.text}</div>
            </div>
        `).join('');
    }

    function updateMeetingInfo() {
        const info = extractMeetingInfo();
        if (!info || !shadowRoot) return;

        currentMeetingInfo = info;

        const titleEl = shadowRoot.getElementById(_s + 'mtgTitle');
        const platformEl = shadowRoot.getElementById(_s + 'mtgPlatform');
        const startedEl = shadowRoot.getElementById(_s + 'mtgStarted');

        if (titleEl) titleEl.textContent = info.title.substring(0, 30) + (info.title.length > 30 ? '...' : '');
        if (platformEl) platformEl.textContent = info.platform;
        if (startedEl) startedEl.textContent = new Date(info.started_at).toLocaleTimeString();
    }

    // ==================== MESSAGE LISTENER (from background) ====================

    chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
        switch (message.action) {
            case 'transcription-partial':
                updateTranscriptionDisplay(message.text, false);
                break;
            case 'transcription-final':
                updateTranscriptionDisplay(message.text, true);
                break;
            case 'audio-level':
                updateVolumeBar(message.rms);
                break;
            case 'silence-warning':
                showOverlayNotification(message.message, 'warning');
                break;
            case 'capture-error':
                showOverlayNotification('Error: ' + message.error, 'error');
                recordingState.status = 'idle';
                updateRecordingUI();
                break;
            case 'auth-expired':
                showOverlayNotification('Token expired', 'error');
                recordingState.status = 'idle';
                updateRecordingUI();
                break;
            case 'ws-status':
                if (message.status === 'error' || message.status === 'disconnected') {
                    showOverlayNotification('Connection lost', 'error');
                }
                break;
            case 'suggestions-response':
                if (message.suggestions) {
                    updateOverlaySuggestions(message.suggestions);
                }
                break;
        }
        sendResponse({ received: true });
        return false;
    });

    // ==================== MEETING AUTO-JOIN DETECTION ====================

    function setupMeetingDetection() {
        const observer = new MutationObserver(() => {
            if (isMeetingActive() && !overlayVisible) {
                showMeetingOverlay();
            }
        });
        observer.observe(document.body, { childList: true, subtree: true });

        setInterval(() => {
            if (isMeetingActive() && !overlayVisible) {
                showMeetingOverlay();
            }
        }, 3000);
    }

    function showMeetingOverlay() {
        if (overlayVisible) return;
        overlayVisible = true;

        createOverlay();
        updateMeetingInfo();

        // Check current recording state from background
        sendToBackground('get-recording-state', {}).then((state) => {
            if (state && state.status !== 'idle') {
                recordingState = state;
                if (state.startTime) recordingStartTime = state.startTime;
                updateRecordingUI();
                if (state.status === 'capturing') startTimer();
            }
        });

        startSuggestionsPolling();
    }

    // STEALTH: Suggestions polled through background, not fetched from page context
    async function startSuggestionsPolling() {
        if (!overlayVisible) return;

        try {
            const meetingInfo = currentMeetingInfo || extractMeetingInfo();
            if (!meetingInfo) return;

            const response = await sendToBackground('fetch-suggestions', {
                meetingUrl: meetingInfo.url
            });

            if (response && response.suggestions && response.suggestions.length > 0) {
                updateOverlaySuggestions(response.suggestions);
            }
        } catch (e) {}

        if (overlayVisible && isMeetingActive()) {
            setTimeout(startSuggestionsPolling, 5000);
        }
    }

    // ==================== SAVE JOB (STEALTH: relayed through background) ====================

    function createSaveButton() {
        const existing = document.querySelector('[data-role="sv"]');
        if (existing) return existing;

        const btn = document.createElement('button');
        btn.setAttribute('data-role', 'sv'); // STEALTH: no identifiable class
        btn.textContent = '💾 Save';
        btn.title = 'Save';
        btn.style.cssText = 'background:linear-gradient(135deg,#3b82f6,#8b5cf6);color:white;border:none;padding:8px 16px;border-radius:6px;font-size:14px;font-weight:500;cursor:pointer;display:inline-flex;align-items:center;gap:6px;transition:all 0.2s;box-shadow:0 2px 4px rgba(59,130,246,0.3);margin:8px 0;font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif;';

        btn.addEventListener('click', async () => {
            const now = Date.now();
            if (now - lastSaveTime < 2000) return;

            const platform = detectJobPage();
            if (!platform) return;

            const jobData = extractJobData(platform);
            if (!jobData.title || !jobData.company) return;

            // STEALTH: Send through background instead of fetching from page
            const response = await sendToBackground('saveJob', { data: jobData });
            if (response && response.success) {
                lastSaveTime = now;
                btn.textContent = '✅ Saved';
                btn.disabled = true;
                setTimeout(() => { btn.textContent = '💾 Save'; btn.disabled = false; }, 3000);
            }
        });

        return btn;
    }

    function injectJobButton() {
        const platform = detectJobPage();
        if (!platform) return;

        const btn = createSaveButton();

        let container = null;
        switch (platform) {
            case 'linkedin':
                container = document.querySelector('.job-details-jobs-unified-top-card__primary-description') ||
                           document.querySelector('.jobs-details__main-content') ||
                           document.querySelector('h1')?.parentElement;
                break;
            case 'indeed':
                container = document.querySelector('.jobsearch-JobInfoHeader') ||
                           document.querySelector('[data-testid="job-details-header"]');
                break;
            case 'glassdoor':
                container = document.querySelector('[data-test="job-title"]')?.parentElement;
                break;
            case 'greenhouse':
            case 'lever':
                container = document.querySelector('.apply-button')?.parentElement ||
                           document.querySelector('h1')?.parentElement;
                break;
            case 'workday':
                container = document.querySelector('[data-automation-id="jobTitle"]')?.parentElement;
                break;
            case 'icims':
                container = document.querySelector('.iCIMS_SubHeader')?.parentElement;
                break;
        }

        if (container && !container.querySelector('[data-role="sv"]')) {
            if (container.firstChild) {
                container.insertBefore(btn, container.firstChild.nextSibling);
            } else {
                container.appendChild(btn);
            }
        }
    }

    // ==================== INITIALIZATION ====================

    function init() {
        const jobPlatform = detectJobPage();
        const meetingPlatform = detectMeetingPlatform();

        if (meetingPlatform) {
            setupMeetingDetection();
            if (isMeetingActive()) {
                showMeetingOverlay();
            }
        } else if (jobPlatform) {
            injectJobButton();
            const observer = new MutationObserver(() => { injectJobButton(); });
            observer.observe(document.body, { childList: true, subtree: true });
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();