/**
 * Shell Component - Main application container
 * Coordinates header, controls, response window, and input
 */

import { State } from '../core/state.js';
import { Events, EventNames } from '../core/events.js';
import { API } from '../core/api.js';

export class Shell {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
    if (!this.container) {
      throw new Error(`Shell container #${containerId} not found`);
    }

    this.init();
  }

  init() {
    // Initialize state
    State.init();

    // Check backend status
    API.startHealthCheck((status) => {
      State.set('backendStatus', status);
      Events.emit(status === 'ready' ? EventNames.BACKEND_READY : EventNames.BACKEND_ERROR);
    });

    // Setup global keyboard shortcuts
    this.setupShortcuts();

    // Handle window controls
    this.setupWindowControls();

    console.log('[Shell] Initialized');
  }

  setupShortcuts() {
    document.addEventListener('keydown', (e) => {
      // Ctrl+N - New conversation
      if ((e.ctrlKey || e.metaKey) && e.key === 'n') {
        e.preventDefault();
        Events.emit(EventNames.CONVERSATION_NEW);
      }

      // Escape - Close panels
      if (e.key === 'Escape') {
        Events.emit(EventNames.SETTINGS_CLOSE);
        Events.emit(EventNames.HISTORY_CLOSE);
      }
    });
  }

  setupWindowControls() {
    // Minimize
    document.getElementById('minBtn')?.addEventListener('click', () => {
      window.api?.minimizeWindow?.();
    });

    // Maximize/Restore
    document.getElementById('maxBtn')?.addEventListener('click', () => {
      window.api?.toggleMaximize?.();
    });

    // Close
    document.getElementById('closeBtn')?.addEventListener('click', () => {
      window.api?.closeWindow?.();
    });
  }
}
