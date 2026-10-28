# Controlled system-audio benchmark

For the live route and reconnect check, run `websocket.py --output /tmp/ant-product-benchmark/live-websocket.json`
with `AINT_Venv/bin/python`. See [validation results and limitations](../LIVE-VALIDATION-2026-09-14.md).

macOS only, using the installed audiotee helper. This plays synthetic speech
audibly and captures only its playback PID. macOS audio permission is required.
It does not record the microphone or constitute a Meet/Zoom call test.

Generate the speech fixtures with `qa/performance/voice/speech.py --generate`
(see that script's required output argument). Prepare playback with a silent
lead-in so afplay is rendering before the process tap attaches:

```sh
AINT_Venv/bin/python - <<'PY'
import numpy as np
import soundfile as sf
audio, rate = sf.read('/tmp/ant-product-benchmark/speech-0.aiff')
sf.write('/tmp/ant-product-benchmark/playback.wav',
         np.concatenate([np.zeros(3 * rate), audio, np.zeros(rate)]), rate)
PY
node qa/performance/live/system-audio.cjs
AINT_Venv/bin/python qa/performance/pipeline/local.py --audio /tmp/ant-product-benchmark/captured-system-audio.wav --output /tmp/ant-product-benchmark/system-audio-pipeline.json
```

The capture script writes a WAV and JSON report under `/tmp/ant-product-benchmark`
(or the directory supplied as its first argument). Processing uses cached Whisper
small, local Ollama Qwen3.5:9b and a temporary database. Its latency excludes capture.
