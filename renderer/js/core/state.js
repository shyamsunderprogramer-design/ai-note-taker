/**
 * State Management - Centralized reactive state store
 * Simple pub/sub pattern for state changes
 */

class StateStore {
  constructor() {
    this.state = {};
    this.listeners = new Map();
    this.initialized = false;
  }

  /**
   * Get current state value
   * @param {string} key - State key
   * @returns {any} Current value
   */
  get(key) {
    return this.state[key];
  }

  /**
   * Set state value and notify listeners
   * @param {string} key - State key
   * @param {any} value - New value
   */
  set(key, value) {
    const oldValue = this.state[key];
    this.state[key] = value;

    // Notify listeners
    if (this.listeners.has(key)) {
      this.listeners.get(key).forEach(callback => {
        try {
          callback(value, oldValue);
        } catch (err) {
          console.error(`[State] Error in listener for ${key}:`, err);
        }
      });
    }
  }

  /**
   * Subscribe to state changes
   * @param {string} key - State key to watch
   * @param {function} callback - Function to call on change
   * @returns {function} Unsubscribe function
   */
  on(key, callback) {
    if (!this.listeners.has(key)) {
      this.listeners.set(key, new Set());
    }
    this.listeners.get(key).add(callback);

    // Return unsubscribe function
    return () => {
      this.listeners.get(key).delete(callback);
    };
  }

  /**
   * Initialize state from localStorage or defaults
   */
  init() {
    if (this.initialized) return;

    // Load saved preferences
    const savedMode = localStorage.getItem('ant:mode') || 'instant';
    const savedModel = localStorage.getItem('ant:model') || 'auto';
    const savedStealth = localStorage.getItem('ant:stealth') === 'true';

    this.state = {
      // App state
      mode: savedMode,
      model: savedModel,
      stealth: savedStealth,

      // UI state
      settingsOpen: false,
      historyOpen: false,
      menuOpen: false,

      // Data
      messages: [],
      currentConversationId: null,
      conversations: [],

      // Backend
      backendStatus: 'unknown', // starting, ready, error, dead

      // Providers
      providers: {},

      // Documents
      documents: [],
    };

    // Subscribe to persistence
    this.on('mode', (mode) => localStorage.setItem('ant:mode', mode));
    this.on('model', (model) => localStorage.setItem('ant:model', model));
    this.on('stealth', (stealth) => localStorage.setItem('ant:stealth', stealth));

    this.initialized = true;
    console.log('[State] Initialized');
  }
}

// Export singleton instance
export const State = new StateStore();
