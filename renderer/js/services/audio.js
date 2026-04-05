/**
 * ANT Audio Service
 * Voice recording and waveform visualization
 */

import { State } from '../core/state.js';
import { Events, EventNames } from '../core/events.js';

export const AudioService = {
  // Recording state
  mediaRecorder: null,
  mediaStream: null,
  audioChunks: [],
  recordingDuration: 0,
  recordingTimer: null,

  // Waveform
  audioContext: null,
  analyser: null,
  waveformAnimationId: null,

  // Initialize recording
  async startRecording() {
    try {
      this.audioChunks = [];

      // Get microphone access
      this.mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          sampleRate: 16000
        }
      });

      // Create media recorder
      this.mediaRecorder = new MediaRecorder(this.mediaStream, {
        mimeType: 'audio/webm;codecs=opus'
      });

      // Collect audio chunks
      this.mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          this.audioChunks.push(event.data);
          Events.emit(EventNames.RECORDING_CHUNK, event.data);
        }
      };

      // Start recording
      this.mediaRecorder.start(100); // Collect every 100ms

      // Start timer
      this.recordingDuration = 0;
      this.recordingTimer = setInterval(() => {
        this.recordingDuration++;
        State.set('recordingDuration', this.recordingDuration);
      }, 1000);

      // Update state
      State.set('isRecording', true);
      State.set('mediaRecorder', this.mediaRecorder);
      State.set('mediaStream', this.mediaStream);

      // Emit event
      Events.emit(EventNames.RECORDING_STARTED);

      // Initialize waveform
      this.initWaveform();

      return true;
    } catch (error) {
      console.error('Failed to start recording:', error);
      Events.emit(EventNames.TOAST_SHOW, { message: 'Microphone access denied', type: 'error' });
      return false;
    }
  },

  // Stop recording and return audio blob
  async stopRecording() {
    return new Promise((resolve, reject) => {
      if (!this.mediaRecorder || this.mediaRecorder.state === 'inactive') {
        resolve(null);
        return;
      }

      // Set up onstop handler
      this.mediaRecorder.onstop = () => {
        // Stop timer
        if (this.recordingTimer) {
          clearInterval(this.recordingTimer);
          this.recordingTimer = null;
        }

        // Stop waveform
        this.stopWaveform();

        // Stop all tracks
        if (this.mediaStream) {
          this.mediaStream.getTracks().forEach(track => track.stop());
        }

        // Create blob from chunks
        const audioBlob = new Blob(this.audioChunks, { type: 'audio/webm' });

        // Update state
        State.set('isRecording', false);
        State.set('recordingDuration', 0);

        // Emit event
        Events.emit(EventNames.RECORDING_STOPPED, { duration: this.recordingDuration });

        resolve(audioBlob);
      };

      // Stop recording
      this.mediaRecorder.stop();
    });
  },

  // Initialize waveform visualization
  initWaveform() {
    const canvas = document.getElementById('waveformCanvas');
    if (!canvas) return;

    // Set up audio context
    this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
    const source = this.audioContext.createMediaStreamSource(this.mediaStream);
    this.analyser = this.audioContext.createAnalyser();
    this.analyser.fftSize = 256;
    this.analyser.smoothingTimeConstant = 0.8;
    source.connect(this.analyser);

    // Start animation
    this.animateWaveform(canvas);
  },

  // Animate waveform
  animateWaveform(canvas) {
    if (!this.analyser) return;

    const ctx = canvas.getContext('2d');
    const bufferLength = this.analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);

    const draw = () => {
      if (!State.get('isRecording')) return;

      this.waveformAnimationId = requestAnimationFrame(draw);

      this.analyser.getByteFrequencyData(dataArray);

      // Clear canvas
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      // Draw waveform
      const barWidth = (canvas.width / bufferLength) * 2.5;
      let barHeight;
      let x = 0;

      // Use green color
      ctx.fillStyle = '#22c55e';

      for (let i = 0; i < bufferLength; i++) {
        barHeight = (dataArray[i] / 255) * canvas.height * 0.8;

        // Center vertically
        const y = (canvas.height - barHeight) / 2;

        ctx.fillRect(x, y, barWidth, barHeight);

        x += barWidth + 1;
      }
    };

    draw();
  },

  // Stop waveform
  stopWaveform() {
    if (this.waveformAnimationId) {
      cancelAnimationFrame(this.waveformAnimationId);
      this.waveformAnimationId = null;
    }

    if (this.audioContext) {
      this.audioContext.close();
      this.audioContext = null;
    }

    this.analyser = null;

    // Clear canvas
    const canvas = document.getElementById('waveformCanvas');
    if (canvas) {
      const ctx = canvas.getContext('2d');
      ctx.clearRect(0, 0, canvas.width, canvas.height);
    }
  },

  // Get current audio level (for visualization)
  getAudioLevel() {
    if (!this.analyser) return 0;

    const dataArray = new Uint8Array(this.analyser.frequencyBinCount);
    this.analyser.getByteFrequencyData(dataArray);

    // Calculate average
    const average = dataArray.reduce((a, b) => a + b, 0) / dataArray.length;
    return average / 255; // Normalize to 0-1
  },

  // Format duration as MM:SS
  formatDuration(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  }
};
