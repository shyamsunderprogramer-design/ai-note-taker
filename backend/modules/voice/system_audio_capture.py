"""
system_audio_capture.py - Native system audio capture
Optimized low-latency audio capture for Windows/macOS/Linux
"""

import asyncio
import numpy as np
import platform
import subprocess
import tempfile
import os
from pathlib import Path
from typing import Optional, Callable, BinaryIO
from dataclasses import dataclass
import threading
import queue
import wave
import io


@dataclass
class AudioConfig:
    """Audio capture configuration"""
    sample_rate: int = 16000  # Whisper-optimized
    channels: int = 1  # Mono for speech
    dtype: str = "int16"
    chunk_duration: float = 0.5  # seconds

    @property
    def chunk_samples(self) -> int:
        return int(self.sample_rate * self.chunk_duration)


class SystemAudioCapture:
    """
    Cross-platform system audio capture with minimal latency.
    Low-latency native audio implementation.
    """

    def __init__(self, config: Optional[AudioConfig] = None):
        self.config = config or AudioConfig()
        self.is_recording = False
        self._capture_thread: Optional[threading.Thread] = None
        self._audio_queue: queue.Queue = queue.Queue()
        self._callbacks: list[Callable[[bytes], None]] = []
        self._system = platform.system()
        self._temp_files: list[str] = []

    def _get_capture_command(self) -> list[str]:
        """Get OS-specific audio capture command"""
        system = self._system

        if system == "Windows":
            # Use ffmpeg with dshow (DirectShow) for Windows
            # Requires: choco install ffmpeg or manual install
            return [
                "ffmpeg",
                "-f", "dshow",
                "-i", "audio=Stereo Mix",  # System audio
                "-ar", str(self.config.sample_rate),
                "-ac", str(self.config.channels),
                "-sample_fmt", "s16",
                "-f", "wav",
                "-"
            ]
        elif system == "Darwin":  # macOS
            # Use ffmpeg with avfoundation for macOS
            return [
                "ffmpeg",
                "-f", "avfoundation",
                "-i", ":0",  # System audio (may need BlackHole for virtual audio)
                "-ar", str(self.config.sample_rate),
                "-ac", str(self.config.channels),
                "-sample_fmt", "s16",
                "-f", "wav",
                "-"
            ]
        else:  # Linux
            # Use ffmpeg with alsa/pulse for Linux
            return [
                "ffmpeg",
                "-f", "pulse",  # or "alsa"
                "-i", "default",
                "-ar", str(self.config.sample_rate),
                "-ac", str(self.config.channels),
                "-sample_fmt", "s16",
                "-f", "wav",
                "-"
            ]

    def _capture_loop(self):
        """Main capture loop running in separate thread"""
        try:
            cmd = self._get_capture_command()

            # Start ffmpeg subprocess
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0
            )

            # Skip WAV header
            header = process.stdout.read(44)
            if len(header) < 44:
                return

            chunk_size = self.config.chunk_samples * 2  # 16-bit = 2 bytes

            while self.is_recording:
                try:
                    # Read audio chunk
                    data = process.stdout.read(chunk_size)
                    if not data:
                        break

                    # Add to queue for processing
                    self._audio_queue.put(data)

                    # Notify callbacks
                    for callback in self._callbacks:
                        try:
                            callback(data)
                        except Exception as e:
                            print(f"[AudioCapture] Callback error: {e}")

                except Exception as e:
                    if self.is_recording:
                        print(f"[AudioCapture] Read error: {e}")
                    break

            # Cleanup
            process.terminate()
            process.wait(timeout=1)

        except Exception as e:
            print(f"[AudioCapture] Capture error: {e}")

    def start(self) -> bool:
        """Start system audio capture"""
        if self.is_recording:
            return True

        try:
            self.is_recording = True
            self._capture_thread = threading.Thread(target=self._capture_loop)
            self._capture_thread.daemon = True
            self._capture_thread.start()
            return True
        except Exception as e:
            print(f"[AudioCapture] Failed to start: {e}")
            self.is_recording = False
            return False

    def stop(self) -> None:
        """Stop system audio capture"""
        self.is_recording = False

        if self._capture_thread:
            self._capture_thread.join(timeout=2.0)
            self._capture_thread = None

        # Clear queue
        while not self._audio_queue.empty():
            try:
                self._audio_queue.get_nowait()
            except queue.Empty:
                break

    def get_audio_chunk(self, timeout: float = 1.0) -> Optional[bytes]:
        """Get a single audio chunk from queue"""
        try:
            return self._audio_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def on_audio(self, callback: Callable[[bytes], None]) -> None:
        """Register audio data callback"""
        self._callbacks.append(callback)

    def off_audio(self, callback: Callable[[bytes], None]) -> None:
        """Unregister audio data callback"""
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def capture_to_file(self, duration: float, output_path: Optional[str] = None) -> Optional[str]:
        """
        Capture system audio to file for specified duration.
        Optimized for interview transcription.
        """
        if output_path is None:
            fd, output_path = tempfile.mkstemp(suffix=".wav")
            os.close(fd)
            self._temp_files.append(output_path)

        try:
            cmd = self._get_capture_command()

            # Add duration limit
            cmd.extend(["-t", str(duration)])
            cmd[-1] = output_path  # Replace "-" with output path

            # Run capture
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=duration + 5
            )

            if result.returncode == 0 and os.path.exists(output_path):
                return output_path
            else:
                print(f"[AudioCapture] ffmpeg error: {result.stderr}")
                return None

        except Exception as e:
            print(f"[AudioCapture] Capture to file error: {e}")
            return None

    def cleanup(self):
        """Cleanup temporary files"""
        self.stop()

        for temp_file in self._temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except Exception as e:
                print(f"[AudioCapture] Cleanup error: {e}")

        self._temp_files.clear()


class PushToTalkCapture:
    """
    Push-to-talk audio capture implementation.
    Records only while hotkey is held.
    """

    def __init__(self, config: Optional[AudioConfig] = None):
        self.config = config or AudioConfig()
        self.capture = SystemAudioCapture(config)
        self.is_pressed = False
        self.audio_buffer: list[bytes] = []
        self._max_buffer_seconds = 30  # Max recording duration

    def press(self):
        """Start recording (hotkey pressed)"""
        if not self.is_pressed:
            self.is_pressed = True
            self.audio_buffer.clear()
            self.capture.start()

            # Register callback to collect audio
            self.capture.on_audio(self._on_audio)

    def release(self) -> Optional[bytes]:
        """
        Stop recording (hotkey released).
        Returns complete audio data as WAV bytes.
        """
        if self.is_pressed:
            self.is_pressed = False
            self.capture.off_audio(self._on_audio)
            self.capture.stop()

            # Combine buffer into WAV file
            if self.audio_buffer:
                return self._create_wav(self.audio_buffer)

        return None

    def _on_audio(self, data: bytes):
        """Callback for audio data"""
        if self.is_pressed:
            self.audio_buffer.append(data)

            # Limit buffer size
            max_chunks = int(self._max_buffer_seconds / self.config.chunk_duration)
            if len(self.audio_buffer) > max_chunks:
                self.audio_buffer.pop(0)

    def _create_wav(self, audio_chunks: list[bytes]) -> bytes:
        """Create WAV file from audio chunks"""
        # Combine all chunks
        audio_data = b"".join(audio_chunks)

        # Create WAV in memory
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav:
            wav.setnchannels(self.config.channels)
            wav.setsampwidth(2)  # 16-bit
            wav.setframerate(self.config.sample_rate)
            wav.writeframes(audio_data)

        return buffer.getvalue()


# Global instance
capture = SystemAudioCapture()


def get_capture() -> SystemAudioCapture:
    """Get the global audio capture instance"""
    return capture


__all__ = [
    "SystemAudioCapture",
    "PushToTalkCapture",
    "AudioConfig",
    "capture",
    "get_capture"
]
