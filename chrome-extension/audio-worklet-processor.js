// Audio Worklet Processor — Downsamples native sample rate to 16kHz mono
// Used by the offscreen document to process tab/mic audio before sending via WebSocket

const TARGET_SAMPLE_RATE = 16000;
const CHUNK_SIZE = 1600; // 100ms at 16kHz

class DownsampleProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this._buffer = new Float32Array(CHUNK_SIZE * 2); // double buffer for safety
    this._bufferIndex = 0;
    this._lastSample = 0;
    this._inputSampleRate = sampleRate; // native rate provided by AudioWorklet
    this._ratio = this._inputSampleRate / TARGET_SAMPLE_RATE;
    this._outputIndex = 0; // fractional position in output domain
    this._isRecording = true;
    this._silenceCount = 0;
    this._chunkCount = 0;

    this.port.onmessage = (event) => {
      if (event.data.type === 'stop') {
        this._isRecording = false;
        this._flush();
      } else if (event.data.type === 'pause') {
        this._isRecording = false;
      } else if (event.data.type === 'resume') {
        this._isRecording = true;
      }
    };
  }

  process(inputs, outputs, parameters) {
    if (!this._isRecording) return true;

    const input = inputs[0];
    if (!input || input.length === 0) return true;

    // Convert to mono: average all channels
    let mono;
    if (input.length === 1) {
      mono = input[0];
    } else {
      mono = new Float32Array(input[0].length);
      for (let ch = 0; ch < input.length; ch++) {
        const channelData = input[ch];
        for (let i = 0; i < channelData.length; i++) {
          mono[i] += channelData[i];
        }
      }
      const numChannels = input.length;
      for (let i = 0; i < mono.length; i++) {
        mono[i] /= numChannels;
      }
    }

    // Downsample using linear interpolation
    const inputLength = mono.length;
    // Calculate how many output samples we can produce from this input block
    const startOutputIndex = this._outputIndex;
    const maxOutputIndex = startOutputIndex + (inputLength / this._ratio);

    let oi = startOutputIndex;
    while (oi < maxOutputIndex) {
      // Map output index back to input domain
      const inputPos = oi * this._ratio;
      const inputIndex = Math.floor(inputPos);
      const frac = inputPos - inputIndex;

      if (inputIndex + 1 < inputLength) {
        // Linear interpolation between adjacent samples
        const sample = mono[inputIndex] * (1 - frac) + mono[inputIndex + 1] * frac;
        this._buffer[this._bufferIndex++] = sample;
      } else if (inputIndex < inputLength) {
        this._buffer[this._bufferIndex++] = mono[inputIndex];
      }

      // When we have a full chunk, send it
      if (this._bufferIndex >= CHUNK_SIZE) {
        const chunk = this._buffer.slice(0, CHUNK_SIZE);
        this._bufferIndex = 0;
        // Copy any remainder to start of buffer
        this._buffer.copyWithin(0, CHUNK_SIZE);
        this._chunkCount++;

        // Calculate RMS volume for the recording indicator
        let sumSq = 0;
        for (let i = 0; i < chunk.length; i++) {
          sumSq += chunk[i] * chunk[i];
        }
        const rms = Math.sqrt(sumSq / chunk.length);

        // Detect silence (RMS below threshold for extended period)
        if (rms < 0.001) {
          this._silenceCount++;
        } else {
          this._silenceCount = 0;
        }

        this.port.postMessage({
          type: 'audio-chunk',
          data: chunk.buffer,
          rms: rms,
          silenceSeconds: this._silenceCount * (CHUNK_SIZE / TARGET_SAMPLE_RATE),
          chunkIndex: this._chunkCount
        }, [chunk.buffer]); // Transfer ownership for zero-copy
      }

      oi += 1;
    }

    // Track fractional output position across process() calls
    this._outputIndex = oi - Math.floor(maxOutputIndex);

    return true;
  }

  _flush() {
    // Send any remaining buffered audio
    if (this._bufferIndex > 0) {
      const remaining = this._buffer.slice(0, this._bufferIndex);
      this.port.postMessage({
        type: 'audio-flush',
        data: remaining.buffer,
        samplesRemaining: this._bufferIndex
      }, [remaining.buffer]);
      this._bufferIndex = 0;
    }
  }
}

registerProcessor('downsample-processor', DownsampleProcessor);