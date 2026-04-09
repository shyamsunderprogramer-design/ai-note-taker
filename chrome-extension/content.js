// Content Script - Injected into job and meeting pages
(function() {
    'use strict';

    // Avoid duplicate injection
    if (window.antExtensionInjected) return;
    window.antExtensionInjected = true;

    console.log('[ANT] Content script loaded');

    // Configuration
    const API_BASE = 'http://localhost:8000';
    const COOLDOWN_MS = 2000;
    let lastSaveTime = 0;

    // State
    let overlayVisible = false;
    let currentMeetingInfo = null;
    let suggestions = [];
    let transcriptionActive = false;

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
            // Extract meeting ID based on platform
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

            // Count participants (rough estimates based on platform)
            const participantElements = document.querySelectorAll('[class*="avatar"]');
            if (participantElements.length > 0) {
                info.participants = participantElements.length;
            }
        } catch (e) {
            console.error('[ANT] Error extracting meeting info:', e);
        }

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
        } catch (e) {
            console.error('[ANT] Error extracting job data:', e);
        }

        return data;
    }

    // ==================== OVERLAY UI ====================

    function createOverlay() {
        const existing = document.getElementById('ant-meeting-overlay');
        if (existing) return existing;

        const overlay = document.createElement('div');
        overlay.id = 'ant-meeting-overlay';
        overlay.innerHTML = `
            <div class="ant-overlay-header">
                <div class="ant-overlay-title">
                    <span class="ant-logo">🐜</span>
                    <span>ANT Live</span>
                    <span class="ant-status-dot" id="antTranscriptionStatus"></span>
                </div>
                <div class="ant-overlay-controls">
                    <button class="ant-overlay-btn" id="antToggleSuggestions" title="Toggle Suggestions">
                        💡
                    </button>
                    <button class="ant-overlay-btn" id="antScreenshotBtn" title="Capture Screenshot">
                        📸
                    </button>
                    <button class="ant-overlay-btn" id="antMinimizeOverlay" title="Minimize">
                        ➖
                    </button>
                    <button class="ant-overlay-btn" id="antCloseOverlay" title="Close">
                        ✕
                    </button>
                </div>
            </div>
            <div class="ant-overlay-content">
                <div class="ant-suggestions-panel" id="antSuggestionsPanel">
                    <div class="ant-suggestions-header">
                        <span>💡 Real-time Suggestions</span>
                    </div>
                    <div class="ant-suggestions-list" id="antSuggestionsList">
                        <div class="ant-suggestion-empty">Listening for questions...</div>
                    </div>
                </div>
                <div class="ant-meeting-info" id="antMeetingInfo">
                    <div class="ant-info-row">
                        <span class="ant-info-label">Meeting:</span>
                        <span class="ant-info-value" id="antMeetingTitle">-</span>
                    </div>
                    <div class="ant-info-row">
                        <span class="ant-info-label">Platform:</span>
                        <span class="ant-info-value" id="antMeetingPlatform">-</span>
                    </div>
                    <div class="ant-info-row">
                        <span class="ant-info-label">Started:</span>
                        <span class="ant-info-value" id="antMeetingStarted">-</span>
                    </div>
                </div>
            </div>
            <div class="ant-overlay-footer">
                <div class="ant-recording-indicator" id="antRecordingIndicator">
                    <span class="ant-recording-dot"></span>
                    <span>Recording</span>
                </div>
            </div>
        `;

        // Add styles
        const style = document.createElement('style');
        style.id = 'ant-overlay-styles';
        style.textContent = `
            #ant-meeting-overlay {
                position: fixed;
                top: 20px;
                right: 20px;
                width: 320px;
                max-height: 400px;
                background: linear-gradient(135deg, rgba(30, 30, 40, 0.95), rgba(20, 20, 30, 0.95));
                border-radius: 12px;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
                z-index: 2147483647;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                color: #fff;
                font-size: 13px;
                backdrop-filter: blur(10px);
                border: 1px solid rgba(255, 255, 255, 0.1);
                overflow: hidden;
                transition: all 0.3s ease;
            }
            #ant-meeting-overlay.minimized {
                max-height: 48px;
                overflow: hidden;
            }
            #ant-meeting-overlay.minimized .ant-overlay-content,
            #ant-meeting-overlay.minimized .ant-overlay-footer {
                display: none;
            }
            .ant-overlay-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 12px 16px;
                background: rgba(255, 255, 255, 0.05);
                border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            }
            .ant-overlay-title {
                display: flex;
                align-items: center;
                gap: 8px;
                font-weight: 600;
                font-size: 14px;
            }
            .ant-logo {
                font-size: 18px;
            }
            .ant-status-dot {
                width: 8px;
                height: 8px;
                border-radius: 50%;
                background: #22c55e;
                animation: pulse 2s infinite;
            }
            @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.5; }
            }
            .ant-overlay-controls {
                display: flex;
                gap: 4px;
            }
            .ant-overlay-btn {
                width: 28px;
                height: 28px;
                border: none;
                background: rgba(255, 255, 255, 0.1);
                border-radius: 6px;
                color: #fff;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 14px;
                transition: background 0.2s;
            }
            .ant-overlay-btn:hover {
                background: rgba(255, 255, 255, 0.2);
            }
            .ant-overlay-content {
                max-height: 300px;
                overflow-y: auto;
                padding: 12px;
            }
            .ant-suggestions-panel {
                background: rgba(255, 255, 255, 0.05);
                border-radius: 8px;
                margin-bottom: 12px;
            }
            .ant-suggestions-header {
                padding: 8px 12px;
                font-weight: 500;
                color: #a0a0a0;
                font-size: 12px;
            }
            .ant-suggestions-list {
                padding: 8px 12px;
            }
            .ant-suggestion-empty {
                color: #666;
                font-style: italic;
                text-align: center;
                padding: 12px;
            }
            .ant-suggestion-item {
                padding: 8px 10px;
                background: rgba(59, 130, 246, 0.15);
                border-left: 3px solid #3b82f6;
                border-radius: 0 6px 6px 0;
                margin-bottom: 8px;
                animation: slideIn 0.3s ease;
            }
            @keyframes slideIn {
                from { opacity: 0; transform: translateX(20px); }
                to { opacity: 1; transform: translateX(0); }
            }
            .ant-suggestion-item.interview {
                background: rgba(34, 197, 94, 0.15);
                border-left-color: #22c55e;
            }
            .ant-suggestion-item.technical {
                background: rgba(168, 85, 247, 0.15);
                border-left-color: #a855f7;
            }
            .ant-suggestion-type {
                font-size: 10px;
                text-transform: uppercase;
                color: #888;
                margin-bottom: 4px;
            }
            .ant-suggestion-text {
                font-size: 13px;
                line-height: 1.4;
            }
            .ant-meeting-info {
                background: rgba(255, 255, 255, 0.03);
                border-radius: 8px;
                padding: 12px;
            }
            .ant-info-row {
                display: flex;
                justify-content: space-between;
                margin-bottom: 6px;
            }
            .ant-info-row:last-child {
                margin-bottom: 0;
            }
            .ant-info-label {
                color: #888;
            }
            .ant-info-value {
                color: #fff;
                font-weight: 500;
                max-width: 180px;
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
            }
            .ant-overlay-footer {
                padding: 10px 16px;
                background: rgba(255, 255, 255, 0.03);
                border-top: 1px solid rgba(255, 255, 255, 0.05);
            }
            .ant-recording-indicator {
                display: flex;
                align-items: center;
                gap: 8px;
                color: #ef4444;
                font-size: 12px;
                font-weight: 500;
            }
            .ant-recording-dot {
                width: 8px;
                height: 8px;
                background: #ef4444;
                border-radius: 50%;
                animation: blink 1s infinite;
            }
            @keyframes blink {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.3; }
            }
            .ant-screenshot-preview {
                max-width: 100%;
                border-radius: 6px;
                margin-top: 8px;
            }
        `;

        document.head.appendChild(style);
        document.body.appendChild(overlay);

        // Wire up controls
        document.getElementById('antMinimizeOverlay').addEventListener('click', () => {
            overlay.classList.add('minimized');
        });

        document.getElementById('antCloseOverlay').addEventListener('click', () => {
            overlay.remove();
            overlayVisible = false;
            if (style.parentNode) style.remove();
        });

        document.getElementById('antToggleSuggestions').addEventListener('click', () => {
            const panel = document.getElementById('antSuggestionsPanel');
            panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
        });

        document.getElementById('antScreenshotBtn').addEventListener('click', captureAndSendScreenshot);

        return overlay;
    }

    async function captureAndSendScreenshot() {
        try {
            const btn = document.getElementById('antScreenshotBtn');
            btn.textContent = '⏳';
            btn.disabled = true;

            // Use chrome.desktopCapture if available
            const stream = await navigator.mediaDevices.getUserMedia({ video: { mediaSource: 'screen' } });
            const track = stream.getVideoTracks()[0];
            const imageCapture = new ImageCapture(track);

            const blob = await imageCapture.takePhoto();
            track.stop();

            const formData = new FormData();
            formData.append('screenshot', blob, 'screenshot.png');
            formData.append('meeting_url', window.location.href);
            formData.append('platform', detectMeetingPlatform());

            const response = await fetch(`${API_BASE}/meetings/screenshot`, {
                method: 'POST',
                body: formData
            });

            if (response.ok) {
                btn.textContent = '✅';
                showOverlayNotification('Screenshot captured!', 'success');
            } else {
                throw new Error('Upload failed');
            }
        } catch (e) {
            console.error('[ANT] Screenshot error:', e);
            showOverlayNotification('Screenshot failed', 'error');
        } finally {
            setTimeout(() => {
                const btn = document.getElementById('antScreenshotBtn');
                if (btn) {
                    btn.textContent = '📸';
                    btn.disabled = false;
                }
            }, 2000);
        }
    }

    function showOverlayNotification(message, type = 'info') {
        const overlay = document.getElementById('ant-meeting-overlay');
        if (!overlay) return;

        const notif = document.createElement('div');
        notif.className = `ant-notification ant-notification-${type}`;
        notif.textContent = message;
        notif.style.cssText = 'position: absolute; top: 50px; right: 10px; left: 10px;';
        overlay.appendChild(notif);

        setTimeout(() => {
            notif.remove();
        }, 3000);
    }

    function updateOverlaySuggestions(newSuggestions) {
        const list = document.getElementById('antSuggestionsList');
        if (!list) return;

        suggestions = [...newSuggestions, ...suggestions].slice(0, 10);

        if (suggestions.length === 0) {
            list.innerHTML = '<div class="ant-suggestion-empty">Listening for questions...</div>';
            return;
        }

        list.innerHTML = suggestions.map(s => `
            <div class="ant-suggestion-item ${s.type || ''}">
                <div class="ant-suggestion-type">${s.type || 'general'}</div>
                <div class="ant-suggestion-text">${s.text}</div>
            </div>
        `).join('');
    }

    function updateMeetingInfo() {
        const info = extractMeetingInfo();
        if (!info) return;

        currentMeetingInfo = info;

        const titleEl = document.getElementById('antMeetingTitle');
        const platformEl = document.getElementById('antMeetingPlatform');
        const startedEl = document.getElementById('antMeetingStarted');

        if (titleEl) titleEl.textContent = info.title.substring(0, 30) + (info.title.length > 30 ? '...' : '');
        if (platformEl) platformEl.textContent = info.platform;
        if (startedEl) startedEl.textContent = new Date(info.started_at).toLocaleTimeString();
    }

    // ==================== MEETING AUTO-JOIN DETECTION ====================

    function setupMeetingDetection() {
        // Detect when user joins a meeting
        const observer = new MutationObserver((mutations) => {
            if (isMeetingActive() && !overlayVisible) {
                showMeetingOverlay();
            }
        });

        observer.observe(document.body, {
            childList: true,
            subtree: true
        });

        // Also poll periodically for meeting state changes
        setInterval(() => {
            if (isMeetingActive() && !overlayVisible) {
                showMeetingOverlay();
            }
        }, 3000);
    }

    function showMeetingOverlay() {
        if (overlayVisible) return;
        overlayVisible = true;

        const overlay = createOverlay();
        updateMeetingInfo();

        // Start fetching suggestions
        startSuggestionsPolling();
    }

    async function startSuggestionsPolling() {
        if (!overlayVisible) return;

        try {
            const meetingInfo = currentMeetingInfo || extractMeetingInfo();
            if (!meetingInfo) return;

            const response = await fetch(`${API_BASE}/interview/suggestions?meeting_url=${encodeURIComponent(meetingInfo.url)}`);

            if (response.ok) {
                const data = await response.json();
                if (data.suggestions && data.suggestions.length > 0) {
                    updateOverlaySuggestions(data.suggestions);
                }
            }
        } catch (e) {
            console.log('[ANT] Suggestions poll failed:', e);
        }

        // Poll every 5 seconds while in meeting
        if (overlayVisible && isMeetingActive()) {
            setTimeout(startSuggestionsPolling, 5000);
        }
    }

    // ==================== SAVE JOB FUNCTIONALITY ====================

    function createSaveButton() {
        const existing = document.getElementById('ant-save-job-btn');
        if (existing) return existing;

        const btn = document.createElement('button');
        btn.id = 'ant-save-job-btn';
        btn.className = 'ant-save-job-button';
        btn.innerHTML = '🐜 Save Job';
        btn.title = 'Save job to AI Note Taker';

        btn.addEventListener('click', async () => {
            const now = Date.now();
            if (now - lastSaveTime < COOLDOWN_MS) {
                showNotification('Please wait before saving another job', 'warning');
                return;
            }

            const platform = detectJobPage();
            if (!platform) {
                showNotification('Could not detect job page', 'error');
                return;
            }

            const jobData = extractJobData(platform);

            if (!jobData.title || !jobData.company) {
                showNotification('Could not extract job details. Please wait for page to fully load.', 'error');
                return;
            }

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
                        source: platform
                    })
                });

                if (response.ok) {
                    lastSaveTime = now;
                    showNotification('Job saved to AI Note Taker!', 'success');
                    btn.innerHTML = '✅ Saved';
                    btn.disabled = true;
                    setTimeout(() => {
                        btn.innerHTML = '🐜 Save Job';
                        btn.disabled = false;
                    }, 3000);
                } else {
                    const error = await response.json();
                    showNotification(`Failed to save: ${error.error || 'Unknown error'}`, 'error');
                }
            } catch (e) {
                console.error('[ANT] Save error:', e);
                showNotification('Failed to connect to AI Note Taker. Is it running?', 'error');
            }
        });

        return btn;
    }

    function showNotification(message, type = 'info') {
        const existing = document.querySelector('.ant-notification');
        if (existing) existing.remove();

        const notif = document.createElement('div');
        notif.className = `ant-notification ant-notification-${type}`;
        notif.textContent = message;

        document.body.appendChild(notif);

        setTimeout(() => {
            notif.classList.add('fade-out');
            setTimeout(() => notif.remove(), 300);
        }, 3000);
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

        if (container && !container.querySelector('#ant-save-job-btn')) {
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
            console.log('[ANT] Meeting platform detected:', meetingPlatform);
            setupMeetingDetection();

            // Show overlay if meeting is already active
            if (isMeetingActive()) {
                showMeetingOverlay();
            }
        } else if (jobPlatform) {
            console.log('[ANT] Job platform detected:', jobPlatform);
            injectJobButton();

            // Watch for SPA navigation
            const observer = new MutationObserver(() => {
                injectJobButton();
            });

            observer.observe(document.body, {
                childList: true,
                subtree: true
            });
        }
    }

    // Run when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
