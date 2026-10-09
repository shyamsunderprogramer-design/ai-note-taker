"""App-owned local inference process; no server or cloud speech API."""
import json
import sys


def main():
    job = json.load(sys.stdin)
    import torch
    import soundfile as sf
    from qwen_tts import Qwen3TTSModel

    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    if device == "cpu" and torch.backends.mps.is_available():
        device = "mps"
    # Float32 on CPU/MPS; CUDA supports the faster bfloat16 path.
    dtype = torch.bfloat16 if device.startswith("cuda") else torch.float32
    model = Qwen3TTSModel.from_pretrained(
        job["model_dir"], device_map=device, dtype=dtype,
        attn_implementation="sdpa", local_files_only=True,
    )
    wavs, sample_rate = model.generate_voice_clone(
        text=job["text"], language="Auto", ref_audio=job["reference_audio"],
        ref_text=job["reference_text"], max_new_tokens=2048,
    )
    if not wavs or len(wavs[0]) == 0:
        raise RuntimeError("The local engine generated no audio")
    sf.write(job["output_file"], wavs[0], sample_rate)
    print(json.dumps({"device": device, "sample_rate": sample_rate}))


if __name__ == "__main__":
    main()
