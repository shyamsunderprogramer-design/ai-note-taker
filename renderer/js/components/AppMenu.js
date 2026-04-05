/**
 * App Menu Component
 * Handles the application menu with sections and actions
 */

import { State } from '../core/state.js';
import { Events, EventNames } from '../core/events.js';
import { ConversationStore } from '../services/api.js';
import { showToast, formatRelativeTime } from '../utils/helpers.js';

export class AppMenu {
  constructor() {
    this.menuEl = document.getElementById('appMenu');
    this.recentSection = document.getElementById('recentConversationsSection');
    this.recentList = document.getElementById('recentConversationsList');
    this.isOpen = false;

    this.setupEventListeners();
  }

  setupEventListeners() {
    // Menu button click
    document.getElementById('menuBtn')?.addEventListener('click', (e) => {
      e.stopPropagation();
      this.toggle();
    });

    // Setup modal close handlers
    this.setupModalCloseHandlers();

    // Menu item clicks
    this.menuEl?.addEventListener('click', (e) => {
      const item = e.target.closest('.app-menu-item');
      if (item) {
        const action = item.dataset.action;
        this.handleAction(action);
      }
    });

    // Close on outside click
    document.addEventListener('click', (e) => {
      if (this.isOpen && !this.menuEl?.contains(e.target)) {
        this.close();
      }
    });

    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => {
      // Escape to close
      if (e.key === 'Escape' && this.isOpen) {
        this.close();
      }
    });

    // Update recent conversations when conversations change
    State.on('conversations', () => {
      this.updateRecentConversations();
    });
  }

  toggle() {
    if (this.isOpen) {
      this.close();
    } else {
      this.open();
    }
  }

  open() {
    this.isOpen = true;
    this.menuEl?.classList.add('open');
    this.updateRecentConversations();
  }

  close() {
    this.isOpen = false;
    this.menuEl?.classList.remove('open');
  }

  handleAction(action) {
    this.close();

    switch (action) {
      case 'new-chat':
        Events.emit(EventNames.CONVERSATION_NEW);
        showToast('New conversation started', 'success');
        break;

      case 'history':
        Events.emit(EventNames.HISTORY_PANEL_TOGGLE);
        break;

      case 'export':
        this.showExportModal();
        break;

      case 'clear':
        if (confirm('Clear current conversation?')) {
          Events.emit(EventNames.CONVERSATION_NEW);
        }
        break;

      case 'cognitive-graph':
        window.api?.openCognitiveGraph?.() || window.open('cognitive-graph.html', '_blank');
        break;

      case 'pre-interview':
        window.api?.openPreInterview?.() || window.open('pre-interview.html', '_blank');
        break;

      case 'analytics':
        this.showAnalyticsModal();
        break;

      case 'study-plan':
        window.open('study-plan.html', '_blank');
        break;

      case 'settings':
        Events.emit(EventNames.SETTINGS_PANEL_TOGGLE);
        break;

      case 'shortcuts':
        this.showShortcutsModal();
        break;

      case 'logs':
        window.api?.openLogs?.();
        break;

      case 'about':
        this.showAboutModal();
        break;

      case 'quit':
        window.api?.quitApp?.() || window.close();
        break;

      default:
        console.log('[AppMenu] Unknown action:', action);
    }
  }

  async updateRecentConversations() {
    if (!this.recentSection || !this.recentList) return;

    try {
      const conversations = await ConversationStore.list();
      const recent = conversations.slice(0, 5);

      if (recent.length === 0) {
        this.recentSection.style.display = 'none';
        return;
      }

      this.recentSection.style.display = 'block';
      this.recentList.innerHTML = recent.map(conv => `
        <div class="app-menu-conversation" data-conversation-id="${conv.id}">
          <span class="app-menu-icon">&#128172;</span>
          <span class="app-menu-conversation-title">${this.escapeHtml(conv.title)}</span>
          <span class="app-menu-conversation-time">${formatRelativeTime(conv.updatedAt)}</span>
        </div>
      `).join('');

      // Add click handlers
      this.recentList.querySelectorAll('.app-menu-conversation').forEach(el => {
        el.addEventListener('click', () => {
          const id = el.dataset.conversationId;
          this.loadConversation(id);
        });
      });
    } catch (error) {
      console.error('[AppMenu] Failed to load recent conversations:', error);
    }
  }

  async loadConversation(id) {
    this.close();
    try {
      const conversation = await ConversationStore.load(id);
      if (!conversation) return;

      State.set('currentConversationId', id);
      State.set('messages', conversation.messages || []);
      State.set('isFirstMessage', false);

      Events.emit(EventNames.CONVERSATION_LOADED, { conversation });
      showToast('Conversation loaded', 'success');
    } catch (error) {
      console.error('[AppMenu] Failed to load conversation:', error);
    }
  }

  showExportModal() {
    const modal = document.getElementById('exportModal');
    if (modal) {
      modal.classList.add('open');
    }
  }

  showShortcutsModal() {
    const modal = document.getElementById('shortcutsModal');
    if (modal) {
      modal.classList.add('open');
    }
  }

  showAnalyticsModal() {
    const modal = document.getElementById('analyticsModal');
    if (modal) {
      modal.classList.add('open');
      this.loadAnalytics();
    }
  }

  showAboutModal() {
    const modal = document.getElementById('aboutModal');
    if (modal) {
      modal.classList.add('open');
      this.updateAboutInfo();
    }
  }

  async loadAnalytics() {
    try {
      const conversations = await ConversationStore.list();
      const totalConversations = conversations.length;
      const totalMessages = conversations.reduce((sum, c) => sum + (c.messageCount || 0), 0);
      const avgDuration = totalConversations > 0
        ? Math.round(conversations.reduce((sum, c) => sum + (c.duration || 0), 0) / totalConversations / 60000)
        : 0;

      document.getElementById('analyticsTotalConversations').textContent = totalConversations;
      document.getElementById('analyticsTotalMessages').textContent = totalMessages;
      document.getElementById('analyticsAvgDuration').textContent = avgDuration + 'm';
      document.getElementById('analyticsSpeakerRatio').textContent = '1:1';
    } catch (error) {
      console.error('[AppMenu] Failed to load analytics:', error);
    }
  }

  async updateAboutInfo() {
    // Check backend status
    try {
      const response = await fetch('http://localhost:8000/health');
      const data = await response.json();
      document.getElementById('aboutBackend').textContent = data.status === 'ok' ? 'Connected' : 'Error';
      document.getElementById('aboutBackend').style.color = data.status === 'ok' ? 'var(--accent-green)' : 'var(--accent-red)';
    } catch {
      document.getElementById('aboutBackend').textContent = 'Disconnected';
      document.getElementById('aboutBackend').style.color = 'var(--accent-red)';
    }

    // Check Ollama
    try {
      const response = await fetch('http://localhost:11434/api/tags');
      document.getElementById('aboutOllama').textContent = response.ok ? 'Running' : 'Error';
      document.getElementById('aboutOllama').style.color = response.ok ? 'var(--accent-green)' : 'var(--accent-red)';
    } catch {
      document.getElementById('aboutOllama').textContent = 'Not Running';
      document.getElementById('aboutOllama').style.color = 'var(--text-tertiary)';
    }

    document.getElementById('aboutWhisper').textContent = 'Local (CT2)';
    document.getElementById('aboutWhisper').style.color = 'var(--accent-green)';
  }

  setupModalCloseHandlers() {
    // Close shortcuts modal
    document.getElementById('closeShortcutsModal')?.addEventListener('click', () => {
      document.getElementById('shortcutsModal')?.classList.remove('open');
    });

    // Close export modal
    document.getElementById('cancelExportBtn')?.addEventListener('click', () => {
      document.getElementById('exportModal')?.classList.remove('open');
    });

    document.getElementById('confirmExportBtn')?.addEventListener('click', () => {
      this.handleExport();
      document.getElementById('exportModal')?.classList.remove('open');
    });

    // Close analytics modal
    document.getElementById('closeAnalyticsBtn')?.addEventListener('click', () => {
      document.getElementById('analyticsModal')?.classList.remove('open');
    });

    // Close about modal
    document.getElementById('closeAboutModal')?.addEventListener('click', () => {
      document.getElementById('aboutModal')?.classList.remove('open');
    });

    // Close modals on backdrop click
    ['shortcutsModal', 'exportModal', 'analyticsModal', 'aboutModal', 'importModal'].forEach(id => {
      document.getElementById(id)?.addEventListener('click', (e) => {
        if (e.target === e.currentTarget) {
          e.currentTarget.classList.remove('open');
        }
      });
    });

    // Import modal handlers
    document.getElementById('cancelImportBtn')?.addEventListener('click', () => {
      document.getElementById('importModal')?.classList.remove('open');
    });

    // API Key modal handlers
    document.getElementById('modalCancel')?.addEventListener('click', () => {
      document.getElementById('apiKeyModal')?.classList.remove('open');
    });

    document.getElementById('modalSave')?.addEventListener('click', () => {
      this.saveApiKey();
      document.getElementById('apiKeyModal')?.classList.remove('open');
    });
  }

  async handleExport() {
    const format = document.querySelector('input[name="exportFormat"]:checked')?.value || 'markdown';
    const includeMetadata = document.getElementById('includeMetadata')?.checked ?? true;
    const includeTimestamps = document.getElementById('includeTimestamps')?.checked ?? false;

    const messages = State.get('messages');
    if (messages.length === 0) {
      showToast('No messages to export', 'error');
      return;
    }

    let content = '';
    const metadata = includeMetadata ? `# Conversation Export\nDate: ${new Date().toLocaleString()}\nMode: ${State.get('mode')}\n\n` : '';

    if (format === 'markdown') {
      content = metadata + messages.map(m => {
        const header = m.role === 'user' ? '## User' : '## AI';
        const time = includeTimestamps ? ` (${new Date(m.timestamp).toLocaleTimeString()})` : '';
        return `${header}${time}\n\n${m.text}\n`;
      }).join('\n---\n\n');
    } else if (format === 'json') {
      content = JSON.stringify({
        exportedAt: new Date().toISOString(),
        mode: State.get('mode'),
        messages
      }, null, 2);
    } else {
      content = metadata + messages.map(m => {
        const prefix = m.role === 'user' ? 'User: ' : 'AI: ';
        const time = includeTimestamps ? `[${new Date(m.timestamp).toLocaleTimeString()}] ` : '';
        return `${time}${prefix}${m.text}`;
      }).join('\n\n');
    }

    // Download file
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `conversation-${Date.now()}.${format === 'json' ? 'json' : format === 'markdown' ? 'md' : 'txt'}`;
    a.click();
    URL.revokeObjectURL(url);

    showToast('Conversation exported', 'success');
  }

  saveApiKey() {
    const provider = document.getElementById('modalProviderName')?.dataset.provider;
    const key = document.getElementById('apiKeyInput')?.value;
    if (provider && key) {
      // Store in main process via IPC
      window.api?.setProviderKey?.(provider, key);
      showToast(`API key saved for ${provider}`, 'success');
    }
  }

  escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
}
