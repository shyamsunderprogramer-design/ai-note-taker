/**
 * ANT State Management
 * Centralized application state with reactive updates
 */

export const State = {
  // Backend status
  backendStatus: 'starting', // 'starting' | 'ready' | 'error' | 'dead'
  backendRestartAttempts: 0,

  // Recording state
  isRecording: false,
  isProcessing: false,
  recordingDuration: 0,
  recordingTimer: null,

  // Audio
  mediaRecorder: null,
  mediaStream: null,
  audioChunks: [],

  // Always-on mic
  alwaysOnActive: false,
  alwaysOnTranscriptionBuffer: '',
  alwaysOnLastHeardTime: 0,

  // Conversation
  currentConversationId: null,
  messages: [],
  isFirstMessage: true,

  // Settings
  mode: 'adaptive',
  responseStyle: 'concise',
  contextLength: 3,
  smartMode: false,
  autoScreenshot: false,

  // UI State
  commandPaletteOpen: false,
  historyPanelOpen: false,
  settingsPanelOpen: false,
  activeCommandIndex: 0,
  commandFilter: '',

  // History
  conversations: [],
  historySearchQuery: '',
  historySortBy: 'updatedAt',

  // Suggestions
  suggestions: [],
  suggestionsEnabled: false,

  // Waveform
  waveformActive: false,

  // Callbacks for reactive updates
  _listeners: new Map(),

  // Subscribe to state changes
  on(key, callback) {
    if (!this._listeners.has(key)) {
      this._listeners.set(key, new Set());
    }
    this._listeners.get(key).add(callback);

    // Return unsubscribe function
    return () => {
      this._listeners.get(key).delete(callback);
    };
  },

  // Set state and notify listeners
  set(key, value) {
    const oldValue = this[key];
    if (oldValue === value) return;

    this[key] = value;

    // Notify listeners
    if (this._listeners.has(key)) {
      this._listeners.get(key).forEach(cb => cb(value, oldValue));
    }
  },

  // Get current state
  get(key) {
    return this[key];
  },

  // Batch multiple updates
  batch(updates) {
    Object.entries(updates).forEach(([key, value]) => {
      this[key] = value;
    });

    // Notify all affected listeners
    Object.keys(updates).forEach(key => {
      if (this._listeners.has(key)) {
        this._listeners.get(key).forEach(cb => cb(this[key]));
      }
    });
  }
};

// Convenience exports for common state access
export const getBackendStatus = () => State.get('backendStatus');
export const setBackendStatus = (status) => State.set('backendStatus', status);

export const getIsRecording = () => State.get('isRecording');
export const setIsRecording = (recording) => State.set('isRecording', recording);

export const getIsProcessing = () => State.get('isProcessing');
export const setIsProcessing = (processing) => State.set('isProcessing', processing);
