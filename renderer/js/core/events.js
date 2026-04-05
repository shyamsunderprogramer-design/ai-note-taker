/**
 * ANT Event Bus
 * Centralized event handling for decoupled communication
 */

class EventBus {
  constructor() {
    this.events = new Map();
  }

  // Subscribe to an event
  on(event, callback) {
    if (!this.events.has(event)) {
      this.events.set(event, new Set());
    }
    this.events.get(event).add(callback);

    // Return unsubscribe function
    return () => this.off(event, callback);
  }

  // Unsubscribe from an event
  off(event, callback) {
    if (this.events.has(event)) {
      this.events.get(event).delete(callback);
    }
  }

  // Emit an event
  emit(event, data) {
    if (this.events.has(event)) {
      this.events.get(event).forEach(callback => {
        try {
          callback(data);
        } catch (error) {
          console.error(`Error in event handler for ${event}:`, error);
        }
      });
    }
  }

  // Emit with async handlers
  async emitAsync(event, data) {
    if (this.events.has(event)) {
      const promises = Array.from(this.events.get(event)).map(callback => {
        try {
          return Promise.resolve(callback(data));
        } catch (error) {
          return Promise.reject(error);
        }
      });
      await Promise.all(promises);
    }
  }

  // Subscribe to event once
  once(event, callback) {
    const unsubscribe = this.on(event, (data) => {
      unsubscribe();
      callback(data);
    });
  }
}

// Global event bus instance
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
  RECORDING_CHUNK: 'recording:chunk',

  // Messages
  MESSAGE_SENT: 'message:sent',
  MESSAGE_RECEIVED: 'message:received',
  MESSAGE_STREAM_START: 'message:streamStart',
  MESSAGE_STREAM_CHUNK: 'message:streamChunk',
  MESSAGE_STREAM_END: 'message:streamEnd',

  // UI
  COMMAND_PALETTE_TOGGLE: 'ui:commandPaletteToggle',
  HISTORY_PANEL_TOGGLE: 'ui:historyPanelToggle',
  SETTINGS_PANEL_TOGGLE: 'ui:settingsPanelToggle',
  SCROLL_TO_BOTTOM: 'ui:scrollToBottom',
  TOAST_SHOW: 'ui:toastShow',

  // Conversation
  CONVERSATION_NEW: 'conversation:new',
  CONVERSATION_LOADED: 'conversation:loaded',
  CONVERSATION_SAVED: 'conversation:saved',

  // Input
  INPUT_SUBMIT: 'input:submit',
  INPUT_FOCUS: 'input:focus',

  // Shortcuts
  SHORTCUT_TRIGGER_AI: 'shortcut:triggerAI',
  SHORTCUT_TOGGLE_STEALTH: 'shortcut:toggleStealth',
  SHORTCUT_HIDE_WINDOW: 'shortcut:hideWindow',
};
