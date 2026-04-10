/**
 * ANT (AI Note Taker) - Main Entry Point
 * Modular architecture with component-based design
 */

import { State } from './core/state.js';
import { Events, EventNames } from './core/events.js';
import { Shell } from './components/Shell.js';
import { SettingsPanel } from './components/SettingsPanel.js';

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  initApp();
});

async function initApp() {
  console.log('[ANT] Initializing...');

  try {
    // Initialize core Shell component
    const shell = new Shell('app');

    // Initialize Settings Panel
    const settingsPanel = new SettingsPanel();

    // Setup menu button
    const menuBtn = document.getElementById('menuBtn');
    menuBtn?.addEventListener('click', () => {
      const isOpen = State.get('settingsOpen');
      if (isOpen) {
        Events.emit(EventNames.SETTINGS_CLOSE);
      } else {
        Events.emit(EventNames.SETTINGS_OPEN);
      }
    });

    // Setup stealth button
    const stealthBtn = document.getElementById('stealthBtn');
    stealthBtn?.addEventListener('click', () => {
      const current = State.get('stealth');
      State.set('stealth', !current);
      stealthBtn.classList.toggle('undetectable', !current);

      // Toggle via Electron API
      window.api?.toggleStealth?.();
    });

    // Listen for backend status to update UI
    Events.on(EventNames.BACKEND_READY, () => {
      updateStatus('ready');
    });

    Events.on(EventNames.BACKEND_ERROR, () => {
      updateStatus('error');
    });

    // Global error handler
    window.addEventListener('error', (e) => {
      console.error('[ANT] Global error:', e.error);
    });

    // Expose for debugging
    window.ant = { State, Events, EventNames };

    console.log('[ANT] Initialized successfully');
  } catch (err) {
    console.error('[ANT] Initialization failed:', err);
  }
}

function updateStatus(status) {
  const indicator = document.getElementById('backendStatusIndicator');
  if (!indicator) return;

  indicator.className = 'backend-status visible';
  indicator.classList.add(status);

  const dot = indicator.querySelector('.backend-status-dot');
  const text = indicator.querySelector('.backend-status-text');

  const labels = {
    starting: 'Starting...',
    ready: 'Ready',
    error: 'Error',
    dead: 'Disconnected'
  };

  if (text) text.textContent = labels[status] || status;
}
