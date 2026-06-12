// ==========================================================================
// Status Bar Logic (Simulation for development)
// FILE: temp_status_bar_logic.js
// PURPOSE: Handles the backend status updates and renders them into the #backendStatusIndicator.
// NOTE: This code is designed to be read by, or merged into, apps/web/app.js
// =========================================================================

/**
 * @type {HTMLElement} The target DOM element for the status message.
 */
let backendStatusElement;

/**
 * Initializes and sets up the IPC listener for backend status updates.
 * Must be called after the window is fully loaded.
 */
function initializeStatusBar() {
  backendStatusElement = document.getElementById('backendStatusIndicator');
  if (!backendStatusElement) {
    console.error("FATAL: #backendStatusIndicator not found in DOM. Status Bar cannot initialize.");
    return;
  }

  // --- IPC Listener Implementation ---
  // This assumes the main Electron process is sending 'backend:status' messages.
  ipcRenderer.on('backend:status', (event, statusData) => {
    console.log('[Status Bar] Received backend status update:', statusData);
    updateStatusBar(statusData);
  });

  // Initial check when the app starts up
  window.addEventListener('load', () => {
      // Trigger an initial status poll to set the correct starting state
      ipcRenderer.send('backend:get-initial-status'); // (Hypothetical send command)
  });
}


/**
 * Renders the backend status into the DOM element using a structured, visual approach.
 * @param {object} data - The status data received from the backend IPC event.
 */
function updateStatusBar(data) {
    if (!backendStatusElement) return;

    let content = '';
    let className = 'status-default'; // Default class for basic styling

    // Clear existing classes and reset appearance first
    backendStatusElement.className = 'backend-status';

    const { status, processRunning, restartAttempts, maxAttempts } = data;

    if (!status) {
        content = 'Connecting...';
        className = 'status-connecting';
    } else if (status === 'ready') {
        content = `🟢 Connected • ${data.message || 'Backend Operational'}`;
        className = 'status-ready';
        // Add any specific readiness info here (e.g., 'Model: GPT-4o')

    } else if (status === 'starting') {
        content = '🔵 Initializing Backend...';
        className = 'status-loading';

    } else if (status === 'error' || status === 'dead') {
        let reason = data.reason ? ` (${data.reason})` : '';
        if (status === 'error' && data.restartAttempt) {
            content = `🔴 ERROR: ${data.message || 'Backend failed to start.'} Retrying in ${data.retryInMs / 1000}s...`;
            className = 'status-error';
        } else if (status === 'dead') {
            content = `❌ CRITICAL FAILURE: Backend is dead. (${data.reason || ''})`;
            className = 'status-fatal';
        } else {
            content = `🔴 ERROR: ${data.message || 'Unknown backend error.'}`;
            className = 'status-error';
        }
    } else if (status === 'unknown') {
        content = '🟡 Unknown State • Checking connection...';
        className = 'status-warning';
    }

    // Apply the new content and style class
    backendStatusElement.innerHTML = content;
    backendStatusElement.classList.add(className);

    console.log(`[Status Bar] Updated to: ${content}`);
}


/**
 * Placeholder function: This must be called when the app launches to initialize handlers.
 */
function setupStatusBar() {
    initializeStatusBar();
}

// --- End of Status Bar Logic Script ---