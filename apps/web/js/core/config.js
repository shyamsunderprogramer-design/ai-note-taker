/**
 * API Configuration — Auto-detects backend URL
 * Loaded before all other scripts to set API_BASE globally.
 *
 * Detection priority:
 * 1. window.API_BASE already set (e.g., by Electron preload)
 * 2. Build-time window.__API_URL__ (for future build injection)
 * 3. Auto-detect: localhost → local backend, cloud → Render backend
 */
(function () {
  // If already set by Electron preload, don't override
  if (typeof window.API_BASE !== 'undefined' && window.API_BASE !== 'http://127.0.0.1:8000') {
    return;
  }

  // Build-time injection for cloud deployment
  if (typeof window.__API_URL__ !== 'undefined') {
    window.API_BASE = window.__API_URL__;
    return;
  }

  // Auto-detect: if served from cloud (not localhost), point to Render backend
  var isLocalhost =
    window.location.hostname === 'localhost' ||
    window.location.hostname === '127.0.0.1' ||
    window.location.protocol === 'file:';

  if (!isLocalhost) {
    // Cloud mode — backend runs on Render
    // Replace this URL if you rename your Render service
    window.API_BASE = 'https://ant-backend.onrender.com';
  } else {
    // Local / Electron mode
    window.API_BASE = 'http://127.0.0.1:8000';
  }
})();