# Embedded voice cloning

The Clone tab uses an app-owned Qwen3-TTS 0.6B Base runtime. No VoiceStudio
process, remote speech API, or separate desktop application is needed.

1. Install the local voice engine from the Clone tab. This downloads Python
   dependencies and model weights once and requires several GB of free disk.
2. Record or upload one clean sample, preferably 3–10 seconds, at most 20 seconds.
3. Give the voice a name and type the exact words spoken in the recording.
4. Save the reference voice, select it below, and generate new speech.

Reference recordings, transcripts, the isolated runtime, weights, and generated
WAV files live under the voice manager's storage directory. Override this with
`ANT_VOICE_STORAGE_DIR`. Keeping the runtime separate avoids replacing the main
backend's Transformers and PyTorch versions. CUDA, Apple MPS, or CPU are selected
by the inference worker. A generation is limited to 2000 characters and five
minutes; failures remain visible rather than substituting a stock voice.

After setup, inference runs with `HF_HUB_OFFLINE=1` and
`TRANSFORMERS_OFFLINE=1`. Setup is the only phase that downloads dependencies and
weights. The worker exits after each generation to release model memory.

VoiceStudio was reviewed as a workflow reference; none of its AGPL source is
included. Its default OmniVoice checkpoint is noncommercial, so the embedded
default uses Apache-2.0 Qwen3-TTS code and weights instead:

- https://github.com/QwenLM/Qwen3-TTS
- https://huggingface.co/Qwen/Qwen3-TTS-12Hz-0.6B-Base
- https://huggingface.co/k2-fsa/OmniVoice (model license)

Existing Edge TTS and RVC voices remain available. Newly saved voices from the
Clone form use the local engine. The gallery continues to show its existing
providers and their source labels.
