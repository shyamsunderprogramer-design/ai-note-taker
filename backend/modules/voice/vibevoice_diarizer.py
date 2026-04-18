"""
vibevoice_diarizer.py — VibeVoice-ASR Speaker Diarization Integration

Provides speaker-identified transcription using VibeVoice-ASR (Microsoft's 7B
parameter speech model with built-in diarization). Falls back to existing
pyannote/energy-based diarization when VibeVoice is unavailable.

Integration points:
  - WebSocket /ws/transcribe: adds "speaker" field to partial/final messages
  - Agent Orchestrator: routes speaker-identified segments to agents
  - Standalone: process_transcription_with_speakers() API endpoint
"""

import logging
import os
import time
import threading
from typing import List, Dict, Optional
from dataclasses import dataclass

import numpy as np

logger = logging.getLogger("voice.vibevoice_diarizer")


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class SpeakerSegment:
    """A transcription segment attributed to a specific speaker."""
    speaker_id: str
    start_time: float
    end_time: float
    text: str
    confidence: float = 1.0
    language: str = ""

    def to_dict(self) -> Dict:
        return {
            "speaker": self.speaker_id,
            "start": self.start_time,
            "end": self.end_time,
            "text": self.text,
            "confidence": self.confidence,
            "language": self.language,
        }


# ---------------------------------------------------------------------------
# Speaker mapping — maps raw speaker labels to semantic roles
# ---------------------------------------------------------------------------

class SpeakerMapper:
    """Maps raw speaker IDs (Speaker 1, Speaker 2) to semantic roles
    (user, interviewer, other) based on configuration and heuristics."""

    def __init__(self, user_speaker: str = "Speaker 1"):
        self.user_speaker = user_speaker
        self.speaker_map: Dict[str, str] = {user_speaker: "user"}
        self._next_other = 1

    def map_speaker(self, raw_speaker: str) -> str:
        """Map a raw speaker label to a semantic role."""
        # Semantic roles pass through directly
        if raw_speaker in ("user", "interviewer", "other"):
            return raw_speaker

        if raw_speaker in self.speaker_map:
            return self.speaker_map[raw_speaker]

        # First unknown speaker seen after user is mapped to interviewer
        # (most common pattern: 2-person interview/call)
        unmapped = [s for s in self.speaker_map if self.speaker_map[s] not in ("user",)]
        if not unmapped:
            self.speaker_map[raw_speaker] = "interviewer"
        else:
            self.speaker_map[raw_speaker] = f"other_{self._next_other}"
            self._next_other += 1

        return self.speaker_map[raw_speaker]

    def reset(self):
        """Reset mapping state."""
        self.speaker_map = {self.user_speaker: "user"}
        self._next_other = 1


# ---------------------------------------------------------------------------
# VibeVoice-ASR diarizer (primary)
# ---------------------------------------------------------------------------

class VibeVoiceDiarizer:
    """Speaker diarization using VibeVoice-ASR.

    VibeVoice-ASR is a 7B parameter model from Microsoft that performs
    speech recognition WITH built-in speaker diarization in a single pass.
    It supports 50+ languages and up to 60 minutes of audio.

    This class provides a synchronous interface that:
      1. Tries VibeVoice-ASR for primary diarization
      2. Falls back to pyannote + Whisper (existing pipeline)
      3. Falls back to energy-based segmentation (SimpleSpeakerDetector)
    """

    def __init__(self, model_size: str = "base"):
        self.model = None
        self.available = False
        self.model_size = model_size
        self._lock = threading.Lock()
        self._load_attempted = False

    def _try_load_vibevoice(self):
        """Attempt to load VibeVoice-ASR model.

        VibeVoice-ASR is loaded from HuggingFace transformers.
        Requires: transformers, torch, accelerate
        """
        if self._load_attempted:
            return
        self._load_attempted = True

        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer
            import torch

            model_name = "microsoft/VibeVoice-ASR"
            logger.info(f"[VibeVoice] Attempting to load {model_name}...")

            self.tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
            self.model = AutoModelForCausalLM.from_pretrained(
                model_name,
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                device_map="auto" if torch.cuda.is_available() else None,
                trust_remote_code=True,
            )
            self.available = True
            logger.info("[VibeVoice] Model loaded successfully")

        except ImportError:
            logger.info("[VibeVoice] transformers/torch not available — will use fallback diarization")
        except Exception as e:
            logger.warning("[VibeVoice] Failed to load model: %s — will use fallback diarization", str(e))

    def transcribe_with_diarization(
        self,
        audio: np.ndarray,
        sample_rate: int = 16000,
        language: Optional[str] = None,
        num_speakers: Optional[int] = None,
    ) -> List[SpeakerSegment]:
        """Transcribe audio with speaker diarization.

        Args:
            audio: PCM float32 audio array
            sample_rate: Sample rate of the audio
            language: Language code (None for auto-detect)
            num_speakers: Expected number of speakers (None for auto)

        Returns:
            List of SpeakerSegment with text and speaker labels
        """
        # Try VibeVoice-ASR first
        segments = self._transcribe_vibevoice(audio, sample_rate, language, num_speakers)
        if segments is not None:
            return segments

        # Fallback 1: pyannote + existing Whisper
        segments = self._transcribe_pyannote_fallback(audio, sample_rate)
        if segments is not None:
            return segments

        # Fallback 2: Simple energy-based diarization
        return self._transcribe_simple_fallback(audio, sample_rate)

    def _transcribe_vibevoice(
        self,
        audio: np.ndarray,
        sample_rate: int,
        language: Optional[str],
        num_speakers: Optional[int],
    ) -> Optional[List[SpeakerSegment]]:
        """Primary path: VibeVoice-ASR for combined transcription + diarization."""
        with self._lock:
            if not self.available and not self._load_attempted:
                self._try_load_vibevoice()
            if not self.available:
                return None

        try:
            import torch

            # Prepare audio input
            if sample_rate != 16000:
                # Resample to 16kHz
                audio = self._resample(audio, sample_rate, 16000)
                sample_rate = 16000

            # VibeVoice-ASR uses a prompt-based interface
            prompt = "<|transcribe|>"
            if language:
                prompt = f"<|transcribe|><|lang|>{language}>"
            if num_speakers:
                prompt += f"<|speakers|{num_speakers}|>"

            # Tokenize and run inference
            inputs = self.tokenizer(
                prompt,
                return_tensors="pt",
                sampling_rate=sample_rate,
                audio=audio,
            )

            device = next(self.model.parameters()).device
            inputs = {k: v.to(device) for k, v in inputs.items()}

            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=4096,
                    temperature=0.0,
                    do_sample=False,
                )

            # Parse VibeVoice output format
            result_text = self.tokenizer.decode(outputs[0], skip_special_tokens=False)
            segments = self._parse_vibevoice_output(result_text, audio, sample_rate)

            if segments:
                logger.info(f"[VibeVoice] Transcribed {len(segments)} segments with diarization")
                return segments

            return None

        except Exception as e:
            logger.warning("[VibeVoice] Inference failed: %s", str(e))
            return None

    def _parse_vibevoice_output(
        self,
        output: str,
        audio: np.ndarray,
        sample_rate: int,
    ) -> List[SpeakerSegment]:
        """Parse VibeVoice-ASR output into SpeakerSegments.

        VibeVoice output format:
        <|speaker:1|> Hello, how are you doing today?
        <|speaker:2|> I'm doing great, thanks for asking.

        Also supports:
        <|speaker:SPEAKER_00|> text...
        [Speaker 1] text...
        """
        segments = []
        duration = len(audio) / sample_rate if len(audio) > 0 else 0
        current_speaker = "Speaker 1"
        current_text = ""
        current_start = 0.0

        # VibeVoice uses special tokens for speaker turns
        import re
        # Pattern 1: <|speaker:N|> format (VibeVoice native)
        # Pattern 2: <|speaker:SPEAKER_XX|> format
        # Pattern 3: [Speaker N] format (fallback)
        speaker_pattern = re.compile(
            r'(?:<\|speaker:(\d+)\|>|<\|speaker:SPEAKER_(\d+)\|>|\[Speaker\s+(\d+)\])'
        )

        lines = output.split('\n')
        position = 0.0  # approximate time position

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check for speaker turn
            match = speaker_pattern.search(line)
            if match:
                # Save previous segment
                if current_text.strip():
                    segments.append(SpeakerSegment(
                        speaker_id=current_speaker,
                        start_time=current_start,
                        end_time=position,
                        text=current_text.strip(),
                        confidence=0.9,
                    ))

                # Extract speaker number
                speaker_num = match.group(1) or match.group(2) or match.group(3)
                current_speaker = f"Speaker {int(speaker_num)}"
                current_start = position
                # Remove speaker tag from text
                current_text = speaker_pattern.sub('', line).strip()
            else:
                current_text += " " + line

            # Estimate time position (~5 words per second)
            position += len(line.split()) * 0.2

        # Final segment
        if current_text.strip():
            segments.append(SpeakerSegment(
                speaker_id=current_speaker,
                start_time=current_start,
                end_time=duration,
                text=current_text.strip(),
                confidence=0.9,
            ))

        return segments

    def _transcribe_pyannote_fallback(
        self,
        audio: np.ndarray,
        sample_rate: int,
    ) -> Optional[List[SpeakerSegment]]:
        """Fallback 1: Use pyannote diarization + Whisper transcription."""
        try:
            from modules.voice.speaker_diarization import get_diarizer, SimpleSpeakerDetector

            diarizer = get_diarizer()

            # Transcribe with Whisper first
            try:
                from modules.voice.whisper_handler import transcribe
            except ImportError:
                from whisper_handler import transcribe

            text = transcribe(audio, mode="adaptive")
            if not text or not text.strip():
                return None

            duration = len(audio) / sample_rate if len(audio) > 0 else 0

            # If pyannote is available, save audio to temp file and run full diarization
            if diarizer.available:
                import tempfile
                import soundfile as sf
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                    sf.write(tmp.name, audio, sample_rate)
                    tmp_path = tmp.name
                try:
                    segments = diarizer.diarize_audio(tmp_path)
                    if segments and len(segments) > 1:
                        # Map Whisper text onto pyannote segments
                        full_segment = SpeakerSegment(
                            speaker_id="Speaker 1",
                            start_time=0.0,
                            end_time=duration,
                            text=text.strip(),
                            confidence=0.85,
                        )
                        return [full_segment]
                finally:
                    try:
                        os.unlink(tmp_path)
                    except OSError:
                        pass  # nosec B110

            # Fallback: use SimpleSpeakerDetector for basic clustering
            detector = SimpleSpeakerDetector()
            chunk_duration = 3.0  # seconds per chunk
            chunk_samples = int(chunk_duration * sample_rate)
            segments = []
            current_text = ""
            current_start = 0.0

            for i in range(0, len(audio), chunk_samples):
                chunk = audio[i:i + chunk_samples]
                if len(chunk) < sample_rate // 2:  # Skip very short chunks
                    continue
                speaker = detector.identify_speaker(chunk)
                chunk_end = min((i + len(chunk)) / sample_rate, duration)

                if speaker != (segments[-1].speaker_id if segments else None):
                    if current_text.strip():
                        segments.append(SpeakerSegment(
                            speaker_id=segments[-1].speaker_id if segments else speaker,
                            start_time=current_start,
                            end_time=i / sample_rate,
                            text=current_text.strip(),
                            confidence=0.6,
                        ))
                    current_start = i / sample_rate
                    current_text = ""
                current_text += " "

            if current_text.strip() or text.strip():
                segments.append(SpeakerSegment(
                    speaker_id=segments[-1].speaker_id if segments else "Speaker 1",
                    start_time=current_start,
                    end_time=duration,
                    text=text.strip(),
                    confidence=0.6,
                ))

            return segments if segments else None

        except Exception as e:
            logger.debug("[VibeVoice] Pyannote fallback unavailable: %s", str(e))
            return None

    def _transcribe_simple_fallback(
        self,
        audio: np.ndarray,
        sample_rate: int,
    ) -> List[SpeakerSegment]:
        """Fallback 2: Simple energy-based segmentation + Whisper transcription."""
        try:
            try:
                from .speaker_diarization import SimpleSpeakerDetector
            except ImportError:
                from voice.speaker_diarization import SimpleSpeakerDetector
            try:
                from .whisper_handler import transcribe
            except ImportError:
                from voice.whisper_handler import transcribe
        except ImportError:
            # Absolute minimal fallback — single speaker
            duration = len(audio) / sample_rate if len(audio) > 0 else 0
            try:
                text = transcribe(audio, mode="adaptive")
            except Exception:
                text = ""
            return [SpeakerSegment(
                speaker_id="Speaker 1",
                start_time=0.0,
                end_time=duration,
                text=text.strip() if text else "",
                confidence=0.5,
            )]

        try:
            detector = SimpleSpeakerDetector()
            text = transcribe(audio, mode="adaptive")

            if not text or not text.strip():
                duration = len(audio) / sample_rate if len(audio) > 0 else 0
                return [SpeakerSegment(
                    speaker_id="Speaker 1",
                    start_time=0.0,
                    end_time=duration,
                    text="",
                    confidence=0.5,
                )]

            duration = len(audio) / sample_rate if len(audio) > 0 else 0

            # Simple approach: try to detect speaker changes via energy patterns
            chunk_size = int(sample_rate * 2)  # 2-second chunks
            segments = []
            pos = 0

            while pos < len(audio):
                end = min(pos + chunk_size, len(audio))
                chunk = audio[pos:end]

                # Detect speaker
                speaker_id = detector.identify_speaker(chunk)
                chunk_duration = (end - pos) / sample_rate
                start_time = pos / sample_rate

                segments.append(SpeakerSegment(
                    speaker_id=speaker_id,
                    start_time=start_time,
                    end_time=start_time + chunk_duration,
                    text="",  # Text assigned proportionally below
                    confidence=0.6,
                ))
                pos = end

            # Distribute transcribed text across segments proportionally
            words = text.strip().split()
            total_duration = duration if duration > 0 else 1
            words_per_second = len(words) / total_duration

            for seg in segments:
                seg_duration = seg.end_time - seg.start_time
                word_count = max(1, int(seg_duration * words_per_second))
                start_idx = int(seg.start_time * words_per_second)
                end_idx = min(start_idx + word_count, len(words))
                if start_idx < len(words):
                    seg.text = " ".join(words[start_idx:end_idx])

            # Merge consecutive same-speaker segments
            merged = self._merge_consecutive(segments)
            return merged

        except Exception as e:
            logger.warning("[VibeVoice] Simple fallback error: %s", str(e))
            duration = len(audio) / sample_rate if len(audio) > 0 else 0
            fallback_text = text.strip() if 'text' in dir() and text else ""
            return [SpeakerSegment(
                speaker_id="Speaker 1",
                start_time=0.0,
                end_time=duration,
                text=fallback_text,
                confidence=0.3,
            )]

    @staticmethod
    def _resample(audio: np.ndarray, orig_rate: int, target_rate: int) -> np.ndarray:
        """Simple resampling by linear interpolation."""
        if orig_rate == target_rate:
            return audio
        duration = len(audio) / orig_rate
        target_len = int(duration * target_rate)
        indices = np.linspace(0, len(audio) - 1, target_len)
        return np.interp(indices, np.arange(len(audio)), audio).astype(np.float32)

    @staticmethod
    def _merge_consecutive(segments: List[SpeakerSegment]) -> List[SpeakerSegment]:
        """Merge consecutive segments from the same speaker."""
        if not segments:
            return []

        merged = []
        current = segments[0]

        for seg in segments[1:]:
            if current.speaker_id == seg.speaker_id:
                current.end_time = seg.end_time
                if seg.text:
                    if current.text:
                        current.text += " " + seg.text
                    else:
                        current.text = seg.text
                current.confidence = min(current.confidence, seg.confidence)
            else:
                merged.append(current)
                current = seg

        merged.append(current)
        return merged

    def format_transcript(self, segments: List[SpeakerSegment]) -> str:
        """Format speaker segments as a readable transcript."""
        lines = []
        current_speaker = None

        for seg in segments:
            speaker_label = seg.speaker_id
            # Normalize SPEAKER_XX format
            if speaker_label.startswith("SPEAKER_"):
                try:
                    speaker_num = int(speaker_label.split("_")[1]) + 1
                    speaker_label = f"Speaker {speaker_num}"
                except (ValueError, IndexError):
                    pass  # nosec B110

            if speaker_label != current_speaker:
                lines.append(f"\n[{speaker_label}]")
                current_speaker = speaker_label

            lines.append(seg.text)

        return "\n".join(lines).strip()


# ---------------------------------------------------------------------------
# Streaming diarizer — attaches speaker labels to real-time transcription
# ---------------------------------------------------------------------------

class StreamingDiarizer:
    """Real-time speaker diarization for streaming audio.

    Works with BrowserTranscriber to add speaker labels to partial
    transcriptions as they arrive over the WebSocket connection.

    Strategy:
      1. Buffer audio chunks to build longer segments (2-3 seconds)
      2. Run voice feature extraction on each chunk
      3. Assign speaker labels based on voice similarity
      4. Map speaker labels to semantic roles (user/interviewer/other)
    """

    def __init__(self, sample_rate: int = 16000, buffer_seconds: float = 3.0):
        self.sample_rate = sample_rate
        self.buffer_seconds = buffer_seconds
        self.buffer = np.array([], dtype=np.float32)
        self.buffer_lock = threading.Lock()
        self.speaker_detector = None  # Lazy-loaded SimpleSpeakerDetector
        self.speaker_mapper = SpeakerMapper()
        self._speaker_history: List[Dict] = []
        self._last_speaker: str = "Speaker 1"

        # Try to load VibeVoice for high-quality diarization (lazy)
        self.vibevoice = None  # Lazy-loaded to avoid startup delay
        self._vibevoice_available = False

    def _ensure_speaker_detector(self):
        """Lazy-load the SimpleSpeakerDetector."""
        if self.speaker_detector is None:
            try:
                try:
                    from .speaker_diarization import SimpleSpeakerDetector
                except ImportError:
                    from voice.speaker_diarization import SimpleSpeakerDetector
                self.speaker_detector = SimpleSpeakerDetector()
            except ImportError:
                # Create a minimal inline detector
                self.speaker_detector = _MinimalSpeakerDetector()

    def add_chunk(self, chunk: np.ndarray) -> Optional[str]:
        """Add an audio chunk and return the current speaker label.

        Returns the detected speaker ID (e.g., "Speaker 1") or None
        if the buffer hasn't accumulated enough audio yet.
        """
        self._ensure_speaker_detector()

        with self.buffer_lock:
            self.buffer = np.concatenate([self.buffer, chunk])

        # Process when we have enough audio
        min_samples = int(self.buffer_seconds * self.sample_rate)
        if len(self.buffer) >= min_samples:
            with self.buffer_lock:
                segment = self.buffer.copy()
                self.buffer = np.array([], dtype=np.float32)

            # Detect speaker
            try:
                speaker = self.speaker_detector.identify_speaker(segment)
            except Exception:
                speaker = self._last_speaker

            self._last_speaker = speaker
            return speaker

        return None

    def map_speaker(self, raw_speaker: str) -> str:
        """Map a raw speaker ID to a semantic role."""
        return self.speaker_mapper.map_speaker(raw_speaker)

    def get_transcript_with_speakers(
        self,
        text: str,
        speaker: str,
    ) -> Dict:
        """Create a transcript entry with speaker information.

        Args:
            text: Transcribed text
            speaker: Raw speaker ID (e.g., "Speaker 1")

        Returns:
            Dict with speaker, text, semantic_role, and timestamp
        """
        semantic_role = self.map_speaker(speaker)
        entry = {
            "speaker": speaker,
            "semantic_role": semantic_role,
            "text": text,
            "timestamp": time.time(),
        }
        self._speaker_history.append(entry)
        return entry

    def process_audio_segment(
        self,
        audio: np.ndarray,
        text: str,
        sample_rate: int = 16000,
    ) -> Dict:
        """Process a complete audio+text segment with speaker identification.

        This is the primary integration point for the WebSocket pipeline.
        When a BrowserTranscriber produces a text result, this method
        determines the speaker and returns enriched data.

        Args:
            audio: The audio that produced this text
            text: The transcribed text
            sample_rate: Audio sample rate

        Returns:
            Dict with speaker, semantic_role, text, confidence
        """
        if not text or not text.strip():
            return {
                "speaker": "Speaker 1",
                "semantic_role": "user",
                "text": text,
                "confidence": 0.0,
            }

        # Try to detect speaker from audio
        self._ensure_speaker_detector()
        min_chunk = int(0.5 * self.sample_rate)  # 500ms minimum for detection

        if len(audio) >= min_chunk:
            try:
                raw_speaker = self.speaker_detector.identify_speaker(audio)
            except Exception:
                raw_speaker = self._last_speaker
        else:
            raw_speaker = self._last_speaker

        self._last_speaker = raw_speaker
        semantic_role = self.map_speaker(raw_speaker)

        return {
            "speaker": raw_speaker,
            "semantic_role": semantic_role,
            "text": text,
            "confidence": 0.7 if len(audio) >= min_chunk else 0.5,
        }

    def reset(self):
        """Reset the streaming diarizer state (e.g., for a new session)."""
        self.buffer = np.array([], dtype=np.float32)
        self.speaker_mapper.reset()
        self._speaker_history = []
        self._last_speaker = "Speaker 1"


class _MinimalSpeakerDetector:
    """Fallback speaker detector when SimpleSpeakerDetector is unavailable.

    Uses simple energy-based heuristics to distinguish speakers.
    """

    def __init__(self):
        self.profiles = {}  # speaker_id -> mean_energy
        self.next_id = 1

    def identify_speaker(self, audio_chunk: np.ndarray) -> str:
        """Identify speaker based on energy characteristics."""
        if len(audio_chunk) == 0:
            return "Speaker 1"

        # Calculate energy features
        mean_energy = float(np.mean(np.abs(audio_chunk)))
        std_energy = float(np.std(np.abs(audio_chunk)))
        zcr = float(np.mean(np.abs(np.diff(np.sign(audio_chunk)))))

        feature_vector = np.array([mean_energy, std_energy, zcr])

        # Match against known speakers
        best_match = None
        best_distance = float('inf')

        for speaker_id, profile in self.profiles.items():
            distance = float(np.linalg.norm(feature_vector - profile))
            if distance < best_distance:
                best_distance = distance
                best_match = speaker_id

        # Threshold for matching — use fixed threshold to avoid
        # matching very different speakers just because one is loud
        # The features are [mean_energy, std_energy, zcr] so distances
        # between different speakers are typically > 0.05
        threshold = 0.1

        if best_match and best_distance < threshold:
            # Update profile with exponential moving average
            self.profiles[best_match] = 0.8 * self.profiles[best_match] + 0.2 * feature_vector
            return best_match

        # New speaker
        speaker_id = f"Speaker {self.next_id}"
        self.profiles[speaker_id] = feature_vector
        self.next_id += 1
        return speaker_id


# ---------------------------------------------------------------------------
# Global singleton
# ---------------------------------------------------------------------------

_diarizer = None
_diarizer_lock = threading.Lock()


def get_diarizer() -> VibeVoiceDiarizer:
    """Get the global VibeVoiceDiarizer singleton."""
    global _diarizer
    if _diarizer is None:
        with _diarizer_lock:
            if _diarizer is None:
                _diarizer = VibeVoiceDiarizer()
    return _diarizer


def get_streaming_diarizer() -> StreamingDiarizer:
    """Create a new StreamingDiarizer (per-session, not singleton)."""
    return StreamingDiarizer()


def process_transcription_with_speakers(
    audio: np.ndarray,
    sample_rate: int = 16000,
    language: Optional[str] = None,
    num_speakers: Optional[int] = None,
) -> Dict:
    """Process audio with speaker diarization.

    Primary entry point for the API endpoint.
    Uses VibeVoice-ASR if available, falls back to pyannote, then energy-based.

    Args:
        audio: PCM float32 audio array
        sample_rate: Audio sample rate
        language: Language code for transcription (None for auto)
        num_speakers: Expected number of speakers (None for auto)

    Returns:
        Dict with 'segments', 'formatted', 'speaker_count', 'method'
    """
    diarizer = get_diarizer()
    segments = diarizer.transcribe_with_diarization(
        audio, sample_rate, language, num_speakers
    )

    # Determine which method was used
    if diarizer.available:
        method = "vibevoice"
    else:
        method = "fallback"

    return {
        "segments": [s.to_dict() for s in segments],
        "formatted": diarizer.format_transcript(segments),
        "speaker_count": len(set(s.speaker_id for s in segments)) if segments else 0,
        "method": method,
    }