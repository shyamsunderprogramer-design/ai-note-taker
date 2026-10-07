"""Own the embedded voice runtime, downloads, and bounded inference jobs."""
import asyncio
import json
import os
from pathlib import Path
import sys
import uuid

MODEL_ID = "Qwen/Qwen3-TTS-12Hz-0.6B-Base"


class LocalCloneEngine:
    def __init__(self, storage_dir):
        self.root = Path(storage_dir).resolve() / "local_engine"
        self.runtime = self.root / "runtime"
        self.model_dir = self.root / "model"
        self.python = self.runtime / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        self.setup_task = None
        self.phase = "not_installed"
        self.error = ""
        self.lock = asyncio.Lock()

    def status(self):
        ready = self.python.exists() and (self.root / "ready.json").exists() and (self.model_dir / "config.json").exists()
        return {"engine": "qwen_local", "available": ready, "model": MODEL_ID,
                "status": self.phase if self.setup_task and not self.setup_task.done() else ("ready" if ready else self.phase),
                "message": self.error}

    async def _run(self, args, timeout, stdin=None, offline=False):
        env = {**os.environ, "HF_HOME": str(self.root / "cache"),
               "PIP_CACHE_DIR": str(self.root / "pip-cache"),
               "PYTORCH_ENABLE_MPS_FALLBACK": "1", "TOKENIZERS_PARALLELISM": "false"}
        if offline:
            env.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1")
        process = await asyncio.create_subprocess_exec(
            *map(str, args), stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE, env=env,
        )
        # Drain stderr continuously and retain only the tail of dependency/model logs.
        tail = bytearray()
        async def drain():
            while chunk := await process.stderr.read(8192):
                tail.extend(chunk)
                del tail[:-4096]
        reader = asyncio.create_task(drain())
        try:
            if stdin:
                process.stdin.write(stdin)
                await process.stdin.drain()
            process.stdin.close()
            await asyncio.wait_for(process.wait(), timeout)
            await reader
            if process.returncode:
                raise RuntimeError(bytes(tail).decode(errors="replace")[-1500:] or "Local voice process failed")
        except BaseException:
            if process.returncode is None:
                process.kill()
                await process.wait()
            await reader
            raise

    async def setup(self):
        self.error = ""
        self.root.mkdir(parents=True, exist_ok=True)
        try:
            self.phase = "installing"
            await self._run([sys.executable, "-m", "venv", self.runtime], 120)
            await self._run([self.python, "-m", "pip", "install", "--disable-pip-version-check",
                             "qwen-tts==0.1.1"], 1800)
            self.phase = "downloading"
            script = "from huggingface_hub import snapshot_download; import sys; snapshot_download(sys.argv[1], local_dir=sys.argv[2])"
            await self._run([self.python, "-c", script, MODEL_ID, self.model_dir], 3600)
            # Validate imports before marking a partially installed runtime ready.
            await self._run([self.python, "-c", "from qwen_tts import Qwen3TTSModel; import torch, soundfile"], 120)
            (self.root / "ready.json").write_text(json.dumps({"model": MODEL_ID}))
            self.phase = "ready"
        except Exception as exc:
            self.phase = "error"
            self.error = "Local voice setup failed: " + str(exc)[-1000:]

    def start_setup(self):
        if self.status()["available"]:
            return self.status()
        if not self.setup_task or self.setup_task.done():
            self.setup_task = asyncio.create_task(self.setup())
            self.phase = "installing"
        return self.status()

    async def synthesize(self, reference_audio, reference_text, text, output_dir):
        if not self.status()["available"]:
            raise ValueError("Install the local voice engine in the Clone tab first")
        if not isinstance(text, str) or not text.strip() or len(text) > 2000:
            raise ValueError("Enter between 1 and 2000 characters")
        if not reference_text.strip() or not Path(reference_audio).is_file():
            raise ValueError("This voice needs a reference recording and its transcript")
        if self.lock.locked():
            raise ValueError("The local voice engine is busy. Try again after this generation finishes")
        output = Path(output_dir) / f"clone_{uuid.uuid4().hex}.wav"
        output.parent.mkdir(parents=True, exist_ok=True)
        job = {"model_dir": str(self.model_dir), "reference_audio": reference_audio,
               "reference_text": reference_text, "text": text, "output_file": str(output)}
        async with self.lock:
            try:
                await self._run([self.python, Path(__file__).with_name("local_clone_worker.py")],
                                300, json.dumps(job).encode(), offline=True)
                if not output.is_file() or output.stat().st_size <= 44:
                    raise ValueError("The local engine generated no playable audio")
            except BaseException:
                output.unlink(missing_ok=True)
                raise
        return output


_engines = {}


def get_local_clone_engine(storage_dir):
    key = str(Path(storage_dir).resolve())
    if key not in _engines:
        _engines[key] = LocalCloneEngine(key)
    return _engines[key]


async def close_local_clone_engines():
    tasks = [engine.setup_task for engine in _engines.values()
             if engine.setup_task and not engine.setup_task.done()]
    for task in tasks:
        task.cancel()
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)
