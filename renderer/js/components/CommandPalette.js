/**
 * Command Palette Component
 * ⌘K interface for quick feature access
 */

import { State } from '../core/state.js';
import { Events, EventNames } from '../core/events.js';

export class CommandPalette {
  constructor() {
    this.overlay = document.getElementById('commandOverlay');
    this.palette = document.getElementById('commandPalette');
    this.input = document.getElementById('commandInput');
    this.results = document.getElementById('commandResults');
    this.count = document.getElementById('commandCount');

    this.selectedIndex = 0;
    this.filteredCommands = [];

    // Define all available commands
    this.commands = [
      // AI Modes
      { id: 'mode-adaptive', title: 'Adaptive Mode', description: 'Auto-select based on query', group: 'AI Mode', shortcut: '', action: () => this.setMode('adaptive') },
      { id: 'mode-instant', title: 'Instant Mode', description: 'Fastest response', group: 'AI Mode', shortcut: '', action: () => this.setMode('instant') },
      { id: 'mode-reasoning', title: 'Reasoning Mode', description: 'Complex analysis', group: 'AI Mode', shortcut: '', action: () => this.setMode('reasoning') },
      { id: 'mode-interview', title: 'Interview Mode', description: 'Technical interview prep', group: 'AI Mode', shortcut: '', action: () => this.setMode('interview') },
      { id: 'mode-code', title: 'Code Mode', description: 'Programming assistance', group: 'AI Mode', shortcut: '', action: () => this.setMode('code') },

      // Response Styles
      { id: 'style-concise', title: 'Concise', description: 'Short answers (2 sentences)', group: 'Response Style', action: () => this.setStyle('concise') },
      { id: 'style-detailed', title: 'Detailed', description: 'In-depth explanations', group: 'Response Style', action: () => this.setStyle('detailed') },
      { id: 'style-bullet', title: 'Bullet Points', description: 'Structured lists', group: 'Response Style', action: () => this.setStyle('bulletpoint') },

      // Context
      { id: 'context-0', title: 'No Context', description: 'Ignore conversation history', group: 'Context', action: () => this.setContext(0) },
      { id: 'context-3', title: '3 Messages', description: 'Last 3 messages', group: 'Context', action: () => this.setContext(3) },
      { id: 'context-5', title: '5 Messages', description: 'Last 5 messages', group: 'Context', action: () => this.setContext(5) },
      { id: 'context-10', title: '10 Messages', description: 'Last 10 messages', group: 'Context', action: () => this.setContext(10) },

      // Features
      { id: 'toggle-smart', title: 'Toggle Smart Mode', description: 'Enhanced code assistance', group: 'Features', shortcut: '', action: () => this.toggleFeature('smartMode') },
      { id: 'toggle-screenshot', title: 'Toggle Auto Screenshot', description: 'Capture screen every 5s', group: 'Features', action: () => this.toggleFeature('autoScreenshot') },
      { id: 'toggle-mic', title: 'Toggle Always-On Mic', description: 'Continuous listening', group: 'Features', action: () => this.toggleFeature('alwaysOnMic') },

      // Navigation
      { id: 'nav-history', title: 'Open History', description: 'View past conversations', group: 'Navigation', shortcut: '⌘⇧H', action: () => this.openHistory() },
      { id: 'nav-settings', title: 'Open Settings', description: 'Configure AI providers', group: 'Navigation', action: () => this.openSettings() },
      { id: 'nav-new', title: 'New Conversation', description: 'Start fresh chat', group: 'Navigation', shortcut: '⌘N', action: () => this.newConversation() },

      // Actions
      { id: 'action-clear', title: 'Clear Conversation', description: 'Remove all messages', group: 'Actions', action: () => this.clearConversation() },
      { id: 'action-export', title: 'Export Conversation', description: 'Save as text/JSON', group: 'Actions', action: () => this.exportConversation() },
      { id: 'action-stealth', title: 'Toggle Stealth Mode', description: 'Hide from screen capture', group: 'Actions', shortcut: '⌥D', action: () => this.toggleStealth() },
    ];

    this.init();
  }

  init() {
    // Subscribe to state
    State.on('commandPaletteOpen', (isOpen) => {
      if (isOpen) this.open();
      else this.close();
    });

    // Event listeners
    this.overlay?.addEventListener('click', () => this.close());
    this.input?.addEventListener('input', (e) => this.handleInput(e.target.value));
    this.input?.addEventListener('keydown', (e) => this.handleKeydown(e));

    // Global shortcut
    document.addEventListener('keydown', (e) => {
      // ⌘K or Ctrl+K
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        this.toggle();
      }
    });
  }

  toggle() {
    const isOpen = State.get('commandPaletteOpen');
    State.set('commandPaletteOpen', !isOpen);
  }

  open() {
    this.overlay?.classList.add('open');
    this.palette?.classList.add('open');
    this.input?.focus();
    this.input.value = '';
    this.filterCommands('');
  }

  close() {
    this.overlay?.classList.remove('open');
    this.palette?.classList.remove('open');
    State.set('commandPaletteOpen', false);
    this.input?.blur();
  }

  handleInput(value) {
    this.filterCommands(value);
  }

  handleKeydown(e) {
    switch (e.key) {
      case 'Escape':
        e.preventDefault();
        this.close();
        break;

      case 'ArrowDown':
        e.preventDefault();
        this.selectedIndex = Math.min(this.selectedIndex + 1, this.filteredCommands.length - 1);
        this.updateSelection();
        break;

      case 'ArrowUp':
        e.preventDefault();
        this.selectedIndex = Math.max(this.selectedIndex - 1, 0);
        this.updateSelection();
        break;

      case 'Enter':
        e.preventDefault();
        this.executeSelected();
        break;

      case 'Tab':
        e.preventDefault();
        this.selectedIndex = (this.selectedIndex + 1) % this.filteredCommands.length;
        this.updateSelection();
        break;
    }
  }

  filterCommands(query) {
    const lowerQuery = query.toLowerCase();

    this.filteredCommands = this.commands.filter(cmd =>
      cmd.title.toLowerCase().includes(lowerQuery) ||
      cmd.description.toLowerCase().includes(lowerQuery) ||
      cmd.group.toLowerCase().includes(lowerQuery)
    );

    this.selectedIndex = 0;
    this.render();
  }

  render() {
    if (!this.results) return;

    // Group commands
    const groups = {};
    this.filteredCommands.forEach(cmd => {
      if (!groups[cmd.group]) groups[cmd.group] = [];
      groups[cmd.group].push(cmd);
    });

    // Build HTML
    let html = '';
    let globalIndex = 0;

    for (const [groupName, commands] of Object.entries(groups)) {
      html += `<div class="command-group">
        <div class="command-group-label">${groupName}</div>
      `;

      commands.forEach(cmd => {
        const isSelected = globalIndex === this.selectedIndex;
        html += `
          <div class="command-item ${isSelected ? 'selected' : ''}" data-index="${globalIndex}" data-id="${cmd.id}">
            <div class="command-item-icon">${this.getIcon(cmd.group)}</div>
            <div class="command-item-content">
              <div class="command-item-title">${this.highlightMatch(cmd.title)}</div>
              <div class="command-item-description">${cmd.description}</div>
            </div>
            ${cmd.shortcut ? `<span class="command-item-key">${cmd.shortcut}</span>` : ''}
          </div>
        `;
        globalIndex++;
      });

      html += '</div>';
    }

    if (this.filteredCommands.length === 0) {
      html = `
        <div class="command-palette-empty">
          <div class="command-palette-empty-icon">🔍</div>
          <div class="command-palette-empty-text">No commands found</div>
        </div>
      `;
    }

    this.results.innerHTML = html;

    // Update count
    if (this.count) {
      this.count.textContent = `${this.filteredCommands.length} command${this.filteredCommands.length !== 1 ? 's' : ''}`;
    }

    // Add click handlers
    this.results.querySelectorAll('.command-item').forEach(item => {
      item.addEventListener('click', () => {
        const index = parseInt(item.dataset.index);
        this.selectedIndex = index;
        this.executeSelected();
      });

      item.addEventListener('mouseenter', () => {
        const index = parseInt(item.dataset.index);
        this.selectedIndex = index;
        this.updateSelection();
      });
    });
  }

  updateSelection() {
    const items = this.results?.querySelectorAll('.command-item');
    if (!items) return;

    items.forEach((item, index) => {
      if (index === this.selectedIndex) {
        item.classList.add('selected');
        item.scrollIntoView({ block: 'nearest' });
      } else {
        item.classList.remove('selected');
      }
    });
  }

  executeSelected() {
    const command = this.filteredCommands[this.selectedIndex];
    if (command) {
      command.action();
      this.close();
    }
  }

  getIcon(group) {
    const icons = {
      'AI Mode': '⚙️',
      'Response Style': '📝',
      'Context': '💬',
      'Features': '⚡',
      'Navigation': '🧭',
      'Actions': '🔧'
    };
    return icons[group] || '•';
  }

  highlightMatch(text) {
    const query = this.input?.value?.toLowerCase() || '';
    if (!query) return text;

    const regex = new RegExp(`(${query})`, 'gi');
    return text.replace(regex, '<mark style="background: rgba(59,130,246,0.3); color: inherit; border-radius: 2px;">$1</mark>');
  }

  // Command actions
  setMode(mode) {
    State.set('mode', mode);
    Events.emit(EventNames.TOAST_SHOW, { message: `Mode: ${mode}`, type: 'success' });
  }

  setStyle(style) {
    State.set('responseStyle', style);
    Events.emit(EventNames.TOAST_SHOW, { message: `Style: ${style}`, type: 'success' });
  }

  setContext(length) {
    State.set('contextLength', length);
    Events.emit(EventNames.TOAST_SHOW, { message: `Context: ${length} messages`, type: 'success' });
  }

  toggleFeature(feature) {
    const current = State.get(feature);
    State.set(feature, !current);
    Events.emit(EventNames.TOAST_SHOW, { message: `${feature} ${!current ? 'enabled' : 'disabled'}`, type: 'success' });
  }

  openHistory() {
    State.set('historyPanelOpen', true);
  }

  openSettings() {
    State.set('settingsPanelOpen', true);
  }

  newConversation() {
    Events.emit(EventNames.CONVERSATION_NEW);
  }

  clearConversation() {
    if (confirm('Clear current conversation?')) {
      State.set('messages', []);
      State.set('currentConversationId', null);
    }
  }

  exportConversation() {
    Events.emit('conversation:export');
  }

  toggleStealth() {
    Events.emit(EventNames.SHORTCUT_TOGGLE_STEALTH);
  }
}
