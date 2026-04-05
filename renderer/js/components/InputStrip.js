/**
 * Input Strip Component
 * Handles text input, voice recording, and quick actions
 */

import { State } from '../core/state.js';
import { Events, EventNames } from '../core/events.js';
import { AudioService } from '../services/audio.js';
import { API } from '../services/api.js';

export class InputStrip {
  constructor() {
    this.voiceBtn = document.getElementById('voiceBtn');
    this.voiceIcon = document.getElementById('voiceIcon');
    this.textInput = document.getElementById('textInput');
    this.submitBtn = document.getElementById('submitBtn');
    this.recordingTimer = document.getElementById('recordingTimer');

    this.quickBtns = {
      smart: document.getElementById('smartModeBtn'),
      screenshot: document.getElementById('screenshotBtn'),
      attach: document.getElementById('attachBtn')
    };

    this.init();
  }

  init() {
    // Subscribe to state
    State.on('isRecording', (isRecording) => this.onRecordingChange(isRecording));
    State.on('recordingDuration', (duration) => this.updateTimer(duration));
    State.on('smartMode', (enabled) => this.toggleSmartMode(enabled));

    // Event listeners
    this.voiceBtn?.addEventListener('click', () => this.toggleRecording());
    this.textInput?.addEventListener('keydown', (e) => this.handleKeydown(e));
    this.textInput?.addEventListener('input', () => this.handleInput());
    this.submitBtn?.addEventListener('click', () => this.submit());

    // Quick buttons
    this.quickBtns.smart?.addEventListener('click', () => this.toggleSmartMode());
    this.quickBtns.screenshot?.addEventListener('click', () => this.captureScreenshot());
    this.quickBtns.attach?.addEventListener('click', () => this.attachFile());

    // Global shortcut
    Events.on(EventNames.SHORTCUT_TRIGGER_AI, () => this.onGlobalTrigger());

    // Auto-resize textarea
    this.setupAutoResize();
  }

  setupAutoResize() {
    if (!this.textInput) return;

    this.textInput.addEventListener('input', () => {
      this.textInput.style.height = 'auto';
      this.textInput.style.height = Math.min(this.textInput.scrollHeight, 120) + 'px';
    });
  }

  async toggleRecording() {
    if (State.get('isRecording')) {
      await this.stopRecording();
    } else {
      await this.startRecording();
    }
  }

  async startRecording() {
    const success = await AudioService.startRecording();
    if (success) {
      this.voiceBtn.classList.add('recording');
      this.voiceIcon.textContent = '⏹';
      this.recordingTimer?.classList.add('visible');
    }
  }

  async stopRecording() {
    const audioBlob = await AudioService.stopRecording();

    this.voiceBtn.classList.remove('recording');
    this.voiceIcon.textContent = '🎤';
    this.recordingTimer?.classList.remove('visible');

    if (audioBlob) {
      // Transcribe
      try {
        Events.emit(EventNames.TOAST_SHOW, { message: 'Transcribing...', type: 'info' });
        const result = await API.transcribeAudio(audioBlob);

        if (result.text) {
          this.textInput.value = result.text;
          this.textInput.style.height = 'auto';
          this.textInput.style.height = Math.min(this.textInput.scrollHeight, 120) + 'px';
          this.submit();
        }
      } catch (error) {
        console.error('Transcription error:', error);
        Events.emit(EventNames.TOAST_SHOW, { message: 'Transcription failed', type: 'error' });
      }
    }
  }

  onRecordingChange(isRecording) {
    if (isRecording) {
      this.voiceBtn?.classList.add('recording');
      this.voiceIcon.textContent = '⏹';
    } else {
      this.voiceBtn?.classList.remove('recording');
      this.voiceIcon.textContent = '🎤';
    }
  }

  updateTimer(duration) {
    if (this.recordingTimer) {
      this.recordingTimer.textContent = AudioService.formatDuration(duration);
    }
  }

  handleKeydown(e) {
    // Submit on Enter (not Shift+Enter)
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      this.submit();
    }

    // Close panels on Escape
    if (e.key === 'Escape') {
      State.set('commandPaletteOpen', false);
      State.set('historyPanelOpen', false);
      State.set('settingsPanelOpen', false);
    }
  }

  handleInput() {
    const hasText = this.textInput.value.trim().length > 0;
    this.submitBtn.disabled = !hasText;

    if (hasText) {
      this.submitBtn.style.opacity = '1';
    } else {
      this.submitBtn.style.opacity = '0.5';
    }
  }

  submit() {
    const text = this.textInput.value.trim();
    if (!text) return;

    // Clear input
    this.textInput.value = '';
    this.textInput.style.height = 'auto';
    this.submitBtn.disabled = true;

    // Emit message sent event
    Events.emit(EventNames.INPUT_SUBMIT, { text });
    Events.emit(EventNames.MESSAGE_SENT, { text, timestamp: Date.now() });

    // Get AI response
    this.getAIResponse(text);
  }

  async getAIResponse(text) {
    State.set('isProcessing', true);

    try {
      const mode = State.get('mode');
      const style = State.get('responseStyle');
      const contextLength = State.get('contextLength');

      // Get context messages
      const messages = State.get('messages');
      const context = contextLength > 0
        ? messages.slice(-contextLength * 2)
        : null;

      // Determine provider
      const provider = State.get('smartMode') ? 'auto' : 'ollama';

      // Build stream URL
      const streamUrl = API.getStreamUrl(text, {
        mode,
        style,
        provider,
        context
      });

      // Stream response
      const responseWindow = window.appComponents?.responseWindow;
      if (responseWindow) {
        await responseWindow.streamResponse(streamUrl);
      }

    } catch (error) {
      console.error('AI response error:', error);
      Events.emit(EventNames.TOAST_SHOW, { message: 'Failed to get AI response', type: 'error' });
    } finally {
      State.set('isProcessing', false);
    }
  }

  onGlobalTrigger() {
    // If already recording, stop and submit
    if (State.get('isRecording')) {
      this.stopRecording();
      return;
    }

    // Focus input
    this.textInput?.focus();

    // If there's text in input, submit it
    if (this.textInput?.value.trim()) {
      this.submit();
    } else {
      // Otherwise start recording
      this.startRecording();
    }
  }

  toggleSmartMode(forceState) {
    const current = State.get('smartMode');
    const newState = forceState !== undefined ? forceState : !current;
    State.set('smartMode', newState);

    if (this.quickBtns.smart) {
      if (newState) {
        this.quickBtns.smart.classList.add('active');
      } else {
        this.quickBtns.smart.classList.remove('active');
      }
    }
  }

  async captureScreenshot() {
    try {
      if (window.api?.captureScreenshot) {
        const screenshot = await window.api.captureScreenshot();
        if (screenshot) {
          Events.emit(EventNames.TOAST_SHOW, { message: 'Screenshot captured', type: 'success' });
          // Store screenshot for next message
          State.set('pendingScreenshot', screenshot);
        }
      }
    } catch (error) {
      console.error('Screenshot error:', error);
      Events.emit(EventNames.TOAST_SHOW, { message: 'Screenshot failed', type: 'error' });
    }
  }

  attachFile() {
    // Create file input
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.pdf,.txt,.md,.docx';
    input.onchange = async (e) => {
      const file = e.target.files[0];
      if (file) {
        try {
          Events.emit(EventNames.TOAST_SHOW, { message: `Uploading ${file.name}...`, type: 'info' });
          await API.uploadDocument(file);
          Events.emit(EventNames.TOAST_SHOW, { message: 'Document uploaded', type: 'success' });
        } catch (error) {
          Events.emit(EventNames.TOAST_SHOW, { message: 'Upload failed', type: 'error' });
        }
      }
    };
    input.click();
  }

  focus() {
    this.textInput?.focus();
  }
}
