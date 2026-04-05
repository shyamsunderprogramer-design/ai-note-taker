/**
 * Response Window Component
 * Handles AI response display and message rendering
 */

import { State } from '../core/state.js';
import { Events, EventNames } from '../core/events.js';
import { API } from '../services/api.js';
import { escapeHtml, formatMessage, animateText } from '../utils/helpers.js';

export class ResponseWindow {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
    this.messageList = document.getElementById('messageList');
    this.welcomeState = document.getElementById('welcomeState');
    this.typingIndicator = document.getElementById('typingIndicator');
    this.scrollBottomBtn = document.getElementById('scrollBottomBtn');

    this.currentStreamingMessage = null;
    this.shouldAutoScroll = true;

    this.init();
  }

  init() {
    // Subscribe to state changes
    State.on('messages', () => this.renderMessages());
    State.on('isProcessing', (isProcessing) => {
      this.toggleTypingIndicator(isProcessing);
    });

    // Listen for events
    Events.on(EventNames.MESSAGE_SENT, (data) => this.addUserMessage(data));
    Events.on(EventNames.MESSAGE_STREAM_START, () => this.onStreamStart());
    Events.on(EventNames.MESSAGE_STREAM_CHUNK, (data) => this.onStreamChunk(data));
    Events.on(EventNames.MESSAGE_STREAM_END, () => this.onStreamEnd());
    Events.on(EventNames.SCROLL_TO_BOTTOM, () => this.scrollToBottom());

    // Scroll detection
    this.container.addEventListener('scroll', () => this.handleScroll());

    // Scroll button click
    this.scrollBottomBtn?.addEventListener('click', () => this.scrollToBottom());
  }

  // Show/hide welcome state
  toggleWelcome(show) {
    if (this.welcomeState) {
      this.welcomeState.style.display = show ? 'flex' : 'none';
    }
    if (this.messageList) {
      this.messageList.style.display = show ? 'none' : 'flex';
    }
  }

  // Add user message to display
  addUserMessage({ text, timestamp }) {
    this.hideWelcome();

    const messageEl = document.createElement('div');
    messageEl.className = 'message message-user';
    messageEl.innerHTML = `
      <div class="message-header">
        <span class="message-role">You</span>
        <span class="message-time">${this.formatTime(timestamp)}</span>
      </div>
      <div class="message-bubble">
        <div class="message-content">${escapeHtml(text)}</div>
      </div>
    `;

    this.messageList.appendChild(messageEl);
    this.scrollToBottom();

    // Show typing indicator
    this.toggleTypingIndicator(true);
  }

  // Stream AI message
  async streamResponse(url) {
    this.hideWelcome();
    Events.emit(EventNames.MESSAGE_STREAM_START);

    try {
      const response = await fetch(url);
      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      let buffer = '';

      // Create message element
      const messageEl = document.createElement('div');
      messageEl.className = 'message message-ai';
      messageEl.innerHTML = `
        <div class="message-header">
          <span class="message-role">AI</span>
          <span class="message-time">${this.formatTime(Date.now())}</span>
        </div>
        <div class="message-bubble">
          <div class="message-content"></div>
        </div>
      `;

      this.messageList.appendChild(messageEl);
      const contentEl = messageEl.querySelector('.message-content');
      this.currentStreamingMessage = contentEl;

      while (true) {
        const { done, value } = await reader.read();

        if (done) {
          break;
        }

        buffer += decoder.decode(value, { stream: true });

        // Process lines
        const lines = buffer.split('\n');
        buffer = lines.pop(); // Keep incomplete line in buffer

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6);

            if (data === '[DONE]') {
              break;
            }

            try {
              const parsed = JSON.parse(data);
              if (parsed.chunk) {
                contentEl.innerHTML += escapeHtml(parsed.chunk);
                this.scrollToBottom();
                Events.emit(EventNames.MESSAGE_STREAM_CHUNK, { chunk: parsed.chunk });
              }
            } catch {
              // Not JSON, treat as plain text
              contentEl.innerHTML += escapeHtml(data);
              this.scrollToBottom();
            }
          }
        }
      }

      // Process remaining buffer
      if (buffer) {
        contentEl.innerHTML += escapeHtml(buffer);
      }

      // Format the final message (code blocks, lists, etc)
      contentEl.innerHTML = formatMessage(contentEl.innerHTML);

      // Save to state
      const messages = State.get('messages');
      messages.push({
        role: 'assistant',
        text: contentEl.textContent,
        timestamp: Date.now()
      });
      State.set('messages', messages);

      Events.emit(EventNames.MESSAGE_STREAM_END);

    } catch (error) {
      console.error('Stream error:', error);
      Events.emit(EventNames.TOAST_SHOW, { message: 'Failed to get AI response', type: 'error' });
      this.toggleTypingIndicator(false);
    }
  }

  onStreamStart() {
    State.set('isProcessing', true);
    this.toggleTypingIndicator(true);
  }

  onStreamChunk(data) {
    // Update UI if needed
  }

  onStreamEnd() {
    State.set('isProcessing', false);
    this.toggleTypingIndicator(false);
    this.currentStreamingMessage = null;

    // Save conversation
    Events.emit(EventNames.CONVERSATION_SAVED);
  }

  toggleTypingIndicator(show) {
    if (this.typingIndicator) {
      this.typingIndicator.style.display = show ? 'flex' : 'none';
    }
  }

  hideWelcome() {
    this.toggleWelcome(false);
  }

  scrollToBottom() {
    if (this.shouldAutoScroll) {
      this.container.scrollTop = this.container.scrollHeight;
    }
  }

  handleScroll() {
    const { scrollTop, scrollHeight, clientHeight } = this.container;
    const isAtBottom = scrollHeight - scrollTop - clientHeight < 50;

    this.shouldAutoScroll = isAtBottom;

    // Show/hide scroll button
    if (this.scrollBottomBtn) {
      if (!isAtBottom && State.get('messages').length > 0) {
        this.scrollBottomBtn.classList.add('visible');
      } else {
        this.scrollBottomBtn.classList.remove('visible');
      }
    }
  }

  formatTime(timestamp) {
    const date = new Date(timestamp);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }

  // Clear all messages
  clear() {
    if (this.messageList) {
      this.messageList.innerHTML = '';
    }
    this.toggleWelcome(true);
  }

  // Render existing messages from state
  renderMessages() {
    const messages = State.get('messages');

    if (messages.length === 0) {
      this.toggleWelcome(true);
      return;
    }

    this.toggleWelcome(false);
    this.messageList.innerHTML = '';

    messages.forEach(msg => {
      const messageEl = document.createElement('div');
      messageEl.className = `message message-${msg.role}`;
      messageEl.innerHTML = `
        <div class="message-header">
          <span class="message-role">${msg.role === 'user' ? 'You' : 'AI'}</span>
          <span class="message-time">${this.formatTime(msg.timestamp)}</span>
        </div>
        <div class="message-bubble">
          <div class="message-content">${formatMessage(escapeHtml(msg.text))}</div>
        </div>
      `;
      this.messageList.appendChild(messageEl);
    });

    this.scrollToBottom();
  }
}
