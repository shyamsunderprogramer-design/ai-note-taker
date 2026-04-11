/**
 * Settings Panel Component
 * Manages the settings panel with tabs and lazy-loaded content
 */

import { State } from '../core/state.js';
import { Events, EventNames } from '../core/events.js';
import { API } from '../core/api.js';

export class SettingsPanel {
  constructor() {
    this.panel = document.getElementById('settingsPanel');
    this.closeBtn = document.getElementById('closeSettingsBtn');
    this.currentTab = 'general';

    if (this.panel) {
      this.init();
    }
  }

  init() {
    // Setup close button
    this.closeBtn?.addEventListener('click', () => this.close());

    // Setup tabs
    document.querySelectorAll('.settings-tab').forEach(tab => {
      tab.addEventListener('click', () => this.switchTab(tab.dataset.tab));
    });

    // Setup collapsible cards
    document.querySelectorAll('.settings-card-header[data-collapsible]').forEach(header => {
      header.addEventListener('click', () => {
        const targetId = header.dataset.collapsible;
        const body = document.getElementById(targetId);
        const arrow = header.querySelector('.settings-card-arrow');

        if (body) {
          body.classList.toggle('collapsed');
          header.classList.toggle('collapsed');
          arrow.style.transform = body.classList.contains('collapsed')
            ? 'rotate(-90deg)'
            : 'rotate(0deg)';
        }
      });
    });

    // Listen for state changes
    Events.on(EventNames.SETTINGS_OPEN, () => this.open());
    Events.on(EventNames.SETTINGS_CLOSE, () => this.close());

    console.log('[SettingsPanel] Initialized');
  }

  open() {
    this.panel?.classList.add('open');
    State.set('settingsOpen', true);
    this.switchTab('general');

    // Load providers
    this.loadProviders();
  }

  close() {
    this.panel?.classList.remove('open');
    State.set('settingsOpen', false);
  }

  switchTab(tabName) {
    // Update tab buttons
    document.querySelectorAll('.settings-tab').forEach(tab => {
      tab.classList.toggle('active', tab.dataset.tab === tabName);
    });

    // Update tab content
    document.querySelectorAll('.settings-tab-content').forEach(content => {
      content.classList.toggle('active', content.dataset.content === tabName);
    });

    this.currentTab = tabName;

    // Load tab-specific data
    if (tabName === 'providers') {
      this.loadProviders();
    } else if (tabName === 'models') {
      this.loadOllamaModels();
      // Refresh race toggles when models tab is opened
      if (typeof renderRaceToggles === 'function') {
        renderRaceToggles();
      }
    } else if (tabName === 'data') {
      this.loadDocuments();
    }
  }

  async loadProviders() {
    try {
      const providers = await window.api?.getProviders?.() || {};
      State.set('providers', providers);

      // Update UI indicators
      Object.keys(providers).forEach(provider => {
        const dot = document.getElementById(`dot-${provider}`);
        if (dot) {
          dot.style.background = providers[provider] ? '#22c55e' : 'transparent';
        }
      });
    } catch (e) {
      console.error('[SettingsPanel] Failed to load providers:', e);
    }
  }

  async loadOllamaModels() {
    // Delegate to loadLocalOllamaModels from app.js if available
    if (typeof loadLocalOllamaModels === 'function') {
      await loadLocalOllamaModels()
      return
    }

    // Fallback: fetch from backend proxy
    const list = document.getElementById('ollamaModelsList');
    if (!list) return;

    list.innerHTML = '<div class="ollama-models-loading">Loading...</div>';

    try {
      const response = await fetch('http://127.0.0.1:8000/ollama/models');
      const data = await response.json();
      const models = data.models || [];

      if (models.length === 0) {
        list.innerHTML = '<div class="ollama-models-loading">No models found</div>';
        return;
      }

      list.innerHTML = models.map(m => `
        <div class="ollama-model-item" data-model-name="${m.name}">
          <span class="ollama-model-name">${m.name}</span>
          <span class="ollama-model-size">${this.formatSize(m.size)}</span>
          <button class="ollama-model-delete" data-model-name="${m.name}" title="Delete model">&times;</button>
        </div>
      `).join('');

      // Wire delete buttons
      list.querySelectorAll('.ollama-model-delete').forEach(btn => {
        btn.addEventListener('click', async () => {
          const modelName = btn.dataset.modelName;
          if (!modelName) return;
          if (!confirm(`Delete local model "${modelName}"? This cannot be undone.`)) return;
          try {
            await window.api.deleteOllamaModel(modelName);
            btn.closest('.ollama-model-item').remove();
            // Refresh the list
            await this.loadOllamaModels();
          } catch (e) {
            console.error('[SettingsPanel] Delete failed:', e);
          }
        });
      });
    } catch {
      list.innerHTML = '<div class="ollama-models-loading">Ollama not running</div>';
    }
  }

  async loadDocuments() {
    const list = document.getElementById('documentList');
    if (!list) return;

    try {
      const documents = await API.getDocuments();
      if (documents.length === 0) {
        list.innerHTML = '<div class="document-empty">No documents uploaded</div>';
        return;
      }

      list.innerHTML = documents.map(doc => `
        <div class="document-item">
          <span class="document-name">${doc.name}</span>
          <button class="document-delete" data-id="${doc.id}">×</button>
        </div>
      `).join('');
    } catch {
      list.innerHTML = '<div class="document-empty">Failed to load documents</div>';
    }
  }

  formatSize(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  }
}
