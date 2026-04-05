/**
 * ANT Main Entry Point
 * Initializes all components and handles global events
 */

import { State } from './core/state.js';
import { Events, EventNames } from './core/events.js';
import { API, ConversationStore } from './services/api.js';
import { ResponseWindow } from './components/ResponseWindow.js';
import { InputStrip } from './components/InputStrip.js';
import { CommandPalette } from './components/CommandPalette.js';
import { showToast, formatRelativeTime } from './utils/helpers.js';

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  const app = new ANTApp();
  app.init();

  // Expose to window for debugging
  window.antApp = app;
});

class ANTApp {
  constructor() {
    // Component instances
    this.components = {};

    // Initialize state
    this.initState();
  }

  initState() {
    // Set initial state from storage or defaults
    const savedMode = localStorage.getItem('ant:mode') || 'adaptive';
    const savedStyle = localStorage.getItem('ant:style') || 'concise';
    const savedContext = parseInt(localStorage.getItem('ant:context') || '3');

    State.set('mode', savedMode);
    State.set('responseStyle', savedStyle);
    State.set('contextLength', savedContext);

    // Subscribe to state changes for persistence
    State.on('mode', (mode) => localStorage.setItem('ant:mode', mode));
    State.on('responseStyle', (style) => localStorage.setItem('ant:style', style));
    State.on('contextLength', (ctx) => localStorage.setItem('ant:context', ctx.toString()));
  }

  async init() {
    console.log('[ANT] Initializing...');

    // Initialize components
    this.initComponents();

    // Check backend status
    await this.checkBackendStatus();

    // Set up backend status polling
    setInterval(() => this.checkBackendStatus(), 5000);

    // Set up event listeners
    this.setupEventListeners();

    // Set up window controls
    this.setupWindowControls();

    // Set up global shortcuts
    this.setupShortcuts();

    // Load conversations
    await this.loadConversations();

    console.log('[ANT] Initialized');
  }

  initComponents() {
    // Response Window
    this.components.responseWindow = new ResponseWindow('responseContainer');

    // Input Strip
    this.components.inputStrip = new InputStrip();

    // Command Palette
    this.components.commandPalette = new CommandPalette();

    // Expose components to window
    window.appComponents = this.components;
  }

  async checkBackendStatus() {
    try {
      const isHealthy = await API.checkHealth();
      const currentStatus = State.get('backendStatus');

      if (isHealthy && currentStatus !== 'ready') {
        State.set('backendStatus', 'ready');
        Events.emit(EventNames.BACKEND_READY);
      } else if (!isHealthy && currentStatus === 'ready') {
        State.set('backendStatus', 'error');
        Events.emit(EventNames.BACKEND_ERROR);
      }

      // Update UI
      this.updateStatusDot(isHealthy);
    } catch {
      if (State.get('backendStatus') === 'ready') {
        State.set('backendStatus', 'error');
      }
      this.updateStatusDot(false);
    }
  }

  updateStatusDot(isHealthy) {
    const statusDot = document.getElementById('backendStatus');
    if (!statusDot) return;

    statusDot.className = 'status-dot';
    if (isHealthy) {
      statusDot.classList.add('ready');
      statusDot.title = 'Backend: Connected';
    } else {
      statusDot.classList.add('error');
      statusDot.title = 'Backend: Disconnected';
    }
  }

  setupEventListeners() {
    // Backend events
    Events.on(EventNames.BACKEND_READY, () => {
      showToast('Connected to AI backend', 'success');
    });

    Events.on(EventNames.BACKEND_ERROR, () => {
      showToast('Lost connection to backend', 'error');
    });

    // Message events
    Events.on(EventNames.MESSAGE_SENT, async ({ text }) => {
      // Add to messages state
      const messages = State.get('messages');
      messages.push({
        role: 'user',
        text,
        timestamp: Date.now()
      });
      State.set('messages', messages);

      // Auto-save after first message
      if (State.get('isFirstMessage')) {
        State.set('isFirstMessage', false);
        this.createConversation();
      }
    });

    Events.on(EventNames.MESSAGE_STREAM_END, () => {
      // Save conversation
      this.saveConversation();
    });

    // Conversation events
    Events.on(EventNames.CONVERSATION_NEW, () => {
      this.newConversation();
    });

    Events.on(EventNames.CONVERSATION_SAVED, () => {
      this.saveConversation();
    });

    // UI events
    Events.on(EventNames.TOAST_SHOW, ({ message, type }) => {
      showToast(message, type);
    });

    // Panel toggles
    Events.on(EventNames.HISTORY_PANEL_TOGGLE, () => {
      this.togglePanel('history');
    });

    Events.on(EventNames.SETTINGS_PANEL_TOGGLE, () => {
      this.togglePanel('settings');
    });

    // Error handling
    window.addEventListener('error', (e) => {
      console.error('[ANT] Global error:', e.error);
    });

    window.addEventListener('unhandledrejection', (e) => {
      console.error('[ANT] Unhandled rejection:', e.reason);
    });
  }

  setupWindowControls() {
    // Minimize
    document.getElementById('minBtn')?.addEventListener('click', () => {
      window.api?.minimizeWindow?.();
    });

    // Close
    document.getElementById('closeBtn')?.addEventListener('click', () => {
      window.api?.closeWindow?.();
    });

    // History button
    document.getElementById('historyBtn')?.addEventListener('click', () => {
      this.togglePanel('history');
    });

    // Close history panel
    document.getElementById('closeHistoryBtn')?.addEventListener('click', () => {
      this.closePanel('history');
    });

    // History backdrop
    document.getElementById('historyBackdrop')?.addEventListener('click', () => {
      this.closePanel('history');
    });

    // Settings
    document.getElementById('menuBtn')?.addEventListener('click', () => {
      this.togglePanel('settings');
    });

    document.getElementById('closeSettingsBtn')?.addEventListener('click', () => {
      this.closePanel('settings');
    });

    document.getElementById('settingsBackdrop')?.addEventListener('click', () => {
      this.closePanel('settings');
    });

    // New chat
    document.getElementById('newChatBtn')?.addEventListener('click', () => {
      this.newConversation();
    });

    // Command trigger
    document.getElementById('commandTrigger')?.addEventListener('click', () => {
      State.set('commandPaletteOpen', true);
    });
  }

  setupShortcuts() {
    document.addEventListener('keydown', (e) => {
      // ⌘N or Ctrl+N - New conversation
      if ((e.metaKey || e.ctrlKey) && e.key === 'n') {
        e.preventDefault();
        this.newConversation();
      }

      // ⌘⇧H or Ctrl+Shift+H - Toggle history
      if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key === 'H') {
        e.preventDefault();
        this.togglePanel('history');
      }

      // Escape - Close panels
      if (e.key === 'Escape') {
        this.closeAllPanels();
      }
    });

    // Listen for global shortcuts from main process
    window.api?.onTriggerAI?.(() => {
      Events.emit(EventNames.SHORTCUT_TRIGGER_AI);
    });

    window.api?.onStealthStateChanged?.((state) => {
      console.log('[ANT] Stealth state:', state);
    });
  }

  togglePanel(panel) {
    const panelState = panel === 'history' ? 'historyPanelOpen' : 'settingsPanelOpen';
    const oppositePanel = panel === 'history' ? 'settingsPanelOpen' : 'historyPanelOpen';

    // Close opposite panel
    State.set(oppositePanel, false);

    // Toggle target panel
    const isOpen = State.get(panelState);
    State.set(panelState, !isOpen);

    // Update UI
    const panelEl = document.getElementById(`${panel}Panel`);
    const backdropEl = document.getElementById(`${panel}Backdrop`);

    if (!isOpen) {
      panelEl?.classList.add('open');
      backdropEl?.classList.add('open');
    } else {
      panelEl?.classList.remove('open');
      backdropEl?.classList.remove('open');
    }
  }

  closePanel(panel) {
    const panelState = panel === 'history' ? 'historyPanelOpen' : 'settingsPanelOpen';
    State.set(panelState, false);

    const panelEl = document.getElementById(`${panel}Panel`);
    const backdropEl = document.getElementById(`${panel}Backdrop`);

    panelEl?.classList.remove('open');
    backdropEl?.classList.remove('open');
  }

  closeAllPanels() {
    this.closePanel('history');
    this.closePanel('settings');
    State.set('commandPaletteOpen', false);
  }

  async newConversation() {
    State.set('currentConversationId', null);
    State.set('messages', []);
    State.set('isFirstMessage', true);

    this.components.responseWindow?.clear();

    showToast('New conversation started', 'success');
  }

  async createConversation() {
    const id = crypto.randomUUID ? crypto.randomUUID() : Date.now().toString(36);
    State.set('currentConversationId', id);
  }

  async saveConversation() {
    const id = State.get('currentConversationId');
    const messages = State.get('messages');

    if (!id || messages.length === 0) return;

    const firstUserMsg = messages.find(m => m.role === 'user');
    const title = firstUserMsg
      ? firstUserMsg.text.substring(0, 50) + (firstUserMsg.text.length > 50 ? '...' : '')
      : 'Untitled';

    try {
      await ConversationStore.save({
        id,
        title,
        messages,
        mode: State.get('mode'),
        updatedAt: Date.now(),
        createdAt: Date.now()
      });

      // Refresh history list
      await this.loadConversations();
    } catch (error) {
      console.error('Failed to save conversation:', error);
    }
  }

  async loadConversations() {
    try {
      const conversations = await ConversationStore.list();
      State.set('conversations', conversations);
      this.renderHistoryList(conversations);
    } catch (error) {
      console.error('Failed to load conversations:', error);
    }
  }

  renderHistoryList(conversations) {
    const historyList = document.getElementById('historyList');
    if (!historyList) return;

    if (conversations.length === 0) {
      historyList.innerHTML = `
        <div class="history-empty">
          <div class="history-empty-icon">💬</div>
          <div>No conversations yet</div>
        </div>
      `;
      return;
    }

    // Group by time
    const groups = this.groupConversations(conversations);

    let html = '';
    for (const [groupName, items] of Object.entries(groups)) {
      html += `<div class="history-group">`;
      html += `<div class="history-group-label">${groupName}</div>`;

      items.forEach(conv => {
        const isActive = conv.id === State.get('currentConversationId');
        html += `
          <div class="history-item ${isActive ? 'active' : ''}" data-id="${conv.id}">
            <span class="history-item-icon">💬</span>
            <div class="history-item-content">
              <div class="history-item-title">${this.escapeHtml(conv.title)}</div>
              <div class="history-item-meta">${formatRelativeTime(conv.updatedAt)} · ${conv.messageCount || 0} messages</div>
            </div>
            <span class="history-item-pin ${conv.pinned ? 'pinned' : ''}">${conv.pinned ? '★' : '☆'}</span>
          </div>
        `;
      });

      html += `</div>`;
    }

    historyList.innerHTML = html;

    // Add click handlers
    historyList.querySelectorAll('.history-item').forEach(item => {
      item.addEventListener('click', () => {
        const id = item.dataset.id;
        this.loadConversation(id);
      });
    });
  }

  groupConversations(conversations) {
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const yesterday = new Date(today.getTime() - 86400000);
    const weekAgo = new Date(today.getTime() - 7 * 86400000);

    const groups = {
      'Today': [],
      'Yesterday': [],
      'This Week': [],
      'Earlier': []
    };

    conversations.forEach(conv => {
      const date = new Date(conv.updatedAt);
      const dateOnly = new Date(date.getFullYear(), date.getMonth(), date.getDate());

      if (dateOnly.getTime() >= today.getTime()) {
        groups['Today'].push(conv);
      } else if (dateOnly.getTime() >= yesterday.getTime()) {
        groups['Yesterday'].push(conv);
      } else if (dateOnly.getTime() >= weekAgo.getTime()) {
        groups['This Week'].push(conv);
      } else {
        groups['Earlier'].push(conv);
      }
    });

    // Remove empty groups
    Object.keys(groups).forEach(key => {
      if (groups[key].length === 0) delete groups[key];
    });

    return groups;
  }

  async loadConversation(id) {
    try {
      const conversation = await ConversationStore.load(id);
      if (!conversation) return;

      State.set('currentConversationId', id);
      State.set('messages', conversation.messages || []);
      State.set('isFirstMessage', false);

      // Update response window
      this.components.responseWindow?.renderMessages();

      // Close history panel
      this.closePanel('history');

      showToast('Conversation loaded', 'success');
    } catch (error) {
      console.error('Failed to load conversation:', error);
    }
  }

  escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
}
