/**
 * Event Bus - Centralized event handling
 * Decoupled communication between components
 */

class EventBus {
  constructor() {
    this.events = new Map();
  }

  /**
   * Subscribe to an event
   * @param {string} event - Event name
   * @param {function} callback - Handler function
   * @returns {function} Unsubscribe function
   */
  on(event, callback) {
    if (!this.events.has(event)) {
      this.events.set(event, new Set());
    }
    this.events.get(event).add(callback);

    return () => this.off(event, callback);
  }

  /**
   * Unsubscribe from an event
   * @param {string} event - Event name
   * @param {function} callback - Handler to remove
   */
  off(event, callback) {
    if (this.events.has(event)) {
      this.events.get(event).delete(callback);
    }
  }

  /**
   * Emit an event with data
   * @param {string} event - Event name
   * @param {any} data - Event data
   */
  emit(event, data) {
    if (this.events.has(event)) {
      this.events.get(event).forEach(callback => {
        try {
          callback(data);
        } catch (err) {
          console.error(`[Events] Error in handler for ${event}:`, err);
        }
      });
    }
  }

  /**
   * Subscribe once to an event
   * @param {string} event - Event name
   * @param {function} callback - Handler function
   */
  once(event, callback) {
    const unsubscribe = this.on(event, (data) => {
      unsubscribe();
      callback(data);
    });
  }
}

// Export singleton instance
export const Events = new EventBus();

// Event name constants
export const EventNames = {
  // Backend
  BACKEND_STATUS_CHANGED: 'backend:statusChanged',
  BACKEND_READY: 'backend:ready',
  BACKEND_ERROR: 'backend:error',

  // Recording
  RECORDING_STARTED: 'recording:started',
  RECORDING_STOPPED: 'recording:stopped',

  // Messages
  MESSAGE_SENT: 'message:sent',
  MESSAGE_RECEIVED: 'message:received',
  MESSAGE_STREAM_START: 'message:streamStart',
  MESSAGE_STREAM_CHUNK: 'message:streamChunk',
  MESSAGE_STREAM_END: 'message:streamEnd',

  // UI
  SETTINGS_OPEN: 'ui:settingsOpen',
  SETTINGS_CLOSE: 'ui:settingsClose',
  HISTORY_OPEN: 'ui:historyOpen',
  HISTORY_CLOSE: 'ui:historyClose',
  MENU_TOGGLE: 'ui:menuToggle',

  // Conversation
  CONVERSATION_NEW: 'conversation:new',
  CONVERSATION_LOADED: 'conversation:loaded',
  CONVERSATION_SAVED: 'conversation:saved',

  // Input
  INPUT_SUBMIT: 'input:submit',

  // Shortcuts
  SHORTCUT_TRIGGER_AI: 'shortcut:triggerAI',
  SHORTCUT_TOGGLE_STEALTH: 'shortcut:toggleStealth',
};
