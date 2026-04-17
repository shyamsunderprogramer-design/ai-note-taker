"""
speaker_diarization.py - Speaker Diarization for AI Note Taker

Features:
- Identify different speakers in audio
- Label transcript segments with speaker IDs
- Merge short segments from same speaker
- Support for pyannote.audio (if available) or fallback to
  Whisper-word-timestamp-based clustering
"""

import logging
import os
import numpy as np
from typing import List, Dict, Optional
from dataclasses import dataclass

logger = logging.getLogger("speaker_diarization")


@dataclass
class SpeakerSegment:
    """Represents a segment of audio attributed to a speaker."""
    speaker_id: str
    start_time: float
    end_time: float
    text: str
    confidence: float = 1.0

    def to_dict(self) -> Dict:
        return {
            "speaker": self.speaker_id,
            "start": self.start_time,
            "end": self.end_time,
            "text": self.text,
            "confidence": self.confidence
        }


class SpeakerDiarizer:
    """
    Speaker diarization using pyannote.audio if available,
    falling back to Whisper word-timestamp clustering.
    """

    def __init__(self):
        self.pipeline = None
        self.available = False
        self._load_attempted = False
        self._load_error = None

    def _try_load_pyannote(self):
        """Lazy-load pyannote models. Only attempts once."""
        if self._load_attempted:
            return
        self._load_attempted = True

        try:
            from pyannote.audio import Pipeline
            import torch

            # HuggingFace access token for gated models
            # The pyannote/speaker-diarization-3.1 model requires accepting
            # the user agreement on huggingface.co and providing a token.
            hf_token = os.getenv("HUGGINGFACE_TOKEN", "").strip()
            if not hf_token:
                hf_token = os.getenv("HF_TOKEN", "").strip()

            if not hf_token:
                logger.info(
                    "[Diarization] No HUGGINGFACE_TOKEN set. "
                    "pyannote diarization requires a HuggingFace token. "
                    "Set HUGGINGFACE_TOKEN env var to enable. "
                    "Falling back to Whisper-based segmentation."
                )
                self.available = False
                return

            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            logger.info(f"[Diarization] Loading pyannote pipeline on {device}...")

            self.pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-community-1",
                token=hf_token,
            )
            self.pipeline = self.pipeline.to(device)

            self.available = True
            logger.info("[Diarization] pyannote pipeline loaded successfully")

        except ImportError:
            logger.info(
                "[Diarization] pyannote.audio not installed. "
                "Install with: pip install pyannote.audio"
            )
            self._load_error = "pyannote not installed"
        except Exception as e:
            logger.warning(f"[Diarization] Failed to load pyannote: {e}")
            self._load_error = str(e)

    def diarize_audio(self, audio_path: str, num_speakers: Optional[int] = None) -> List[SpeakerSegment]:
        """
        Perform speaker diarization on an audio file.

        Args:
            audio_path: Path to audio file (WAV 16kHz mono preferred)
            num_speakers: Expected number of speakers (None for auto)

        Returns:
            List of SpeakerSegment objects
        """
        self._try_load_pyannote()

        if self.available and self.pipeline is not None:
            try:
                # Preload audio with soundfile to avoid torchcodec dependency
                # (torchcodec often fails on Windows due to FFmpeg DLL issues)
                audio_data = self._preload_audio(audio_path)
                if audio_data is not None:
                    diarization = self.pipeline(audio_data, num_speakers=num_speakers)
                else:
                    # Fallback: try passing path directly (may work on Linux/Mac)
                    diarization = self.pipeline(audio_path, num_speakers=num_speakers)

                segments = []
                # pyannote v4+ returns DiarizeOutput with serialize()
                # pyannote v3 returns Annotation with itertracks()
                if hasattr(diarization, 'serialize'):
                    result = diarization.serialize()
                    for seg in result.get('diarization', result.get('exclusive_diarization', [])):
                        label = seg.get('speaker', 'Speaker 1')
                        if label.startswith("SPEAKER_"):
                            try:
                                num = int(label.split("_")[1]) + 1
                                label = f"Speaker {num}"
                            except (ValueError, IndexError):
                                pass
                        segments.append(SpeakerSegment(
                            speaker_id=label,
                            start_time=round(seg.get('start', 0), 3),
                            end_time=round(seg.get('end', 0), 3),
                            text="",
                            confidence=0.9
                        ))
                elif hasattr(diarization, 'itertracks'):
                    for turn, _, speaker in diarization.itertracks(yield_label=True):
                        label = speaker
                        if label.startswith("SPEAKER_"):
                            try:
                                num = int(label.split("_")[1]) + 1
                                label = f"Speaker {num}"
                            except (ValueError, IndexError):
                                pass
                        segments.append(SpeakerSegment(
                            speaker_id=label,
                            start_time=round(turn.start, 3),
                            end_time=round(turn.end, 3),
                            text="",
                            confidence=0.9
                        ))
                else:
                    # Unknown format — try iterating as annotation
                    logger.warning(f"[Diarization] Unknown diarization output type: {type(diarization)}")
                    return []
                logger.info(f"[Diarization] pyannote: {len(segments)} segments, "
                            f"{len(set(s.speaker_id for s in segments))} speakers")
                return segments
            except Exception as e:
                logger.warning(f"[Diarization] pyannote failed: {e}, using fallback")

        # Fallback: return empty — the caller should use Whisper word timestamps
        # for better segmentation than a single-segment guess
        return []

    def _preload_audio(self, audio_path: str) -> Optional[Dict]:
        """Preload audio file as in-memory dict for pyannote (avoids torchcodec)."""
        try:
            import soundfile as sf
            import torch
            waveform, sample_rate = sf.read(audio_path)
            # Convert to float32 mono
            if waveform.ndim > 1:
                waveform = waveform.mean(axis=1)
            waveform = waveform.astype(np.float32)
            # pyannote expects: {"waveform": tensor(1, N), "sample_rate": int}
            waveform_tensor = torch.from_numpy(waveform).unsqueeze(0)
            return {"waveform": waveform_tensor, "sample_rate": sample_rate}
        except ImportError:
            logger.debug("[Diarization] soundfile not available for audio preload")
            return None
        except Exception as e:
            logger.debug(f"[Diarization] Audio preload failed: {e}")
            return None

    def diarize_and_transcribe(self, audio_path: str, transcription_segments: List[Dict]) -> List[SpeakerSegment]:
        """
        Combine diarization with existing Whisper transcription segments.

        Strategy:
          1. If pyannote is available → use its speaker timeline to label segments
          2. If not → cluster Whisper segments by voice similarity using
             energy + spectral features
        """
        # Try pyannote diarization first
        speaker_segments = self.diarize_audio(audio_path)

        if speaker_segments and len(speaker_segments) > 1:
            # Map Whisper transcription segments to speaker timeline
            return self._map_transcription_to_speakers(
                transcription_segments, speaker_segments
            )

        # Fallback: cluster Whisper segments by voice features
        return self._cluster_whisper_segments(audio_path, transcription_segments)

    def _map_transcription_to_speakers(
        self,
        transcription_segments: List[Dict],
        speaker_segments: List[SpeakerSegment],
    ) -> List[SpeakerSegment]:
        """Map Whisper word segments onto pyannote speaker timeline."""
        combined = []
        for trans_seg in transcription_segments:
            trans_start = trans_seg.get("start", 0)
            trans_end = trans_seg.get("end", trans_start + 1)
            trans_text = trans_seg.get("text", "").strip()
            if not trans_text:
                continue

            # Find the speaker segment with maximum overlap
            best_speaker = "Speaker 1"
            best_overlap = 0
            for spk_seg in speaker_segments:
                overlap_start = max(trans_start, spk_seg.start_time)
                overlap_end = min(trans_end, spk_seg.end_time)
                overlap = max(0, overlap_end - overlap_start)
                if overlap > best_overlap:
                    best_overlap = overlap
                    best_speaker = spk_seg.speaker_id

            combined.append(SpeakerSegment(
                speaker_id=best_speaker,
                start_time=trans_start,
                end_time=trans_end,
                text=trans_text,
                confidence=0.85
            ))

        return self._merge_consecutive_segments(combined)

    def _cluster_whisper_segments(
        self,
        audio_path: str,
        transcription_segments: List[Dict],
    ) -> List[SpeakerSegment]:
        """
        Cluster Whisper segments into speakers using audio features.

        This is the fallback when pyannote is not available.
        Uses energy + spectral features from the audio at each segment's
        time range to cluster segments by speaker similarity.
        """
        if not transcription_segments:
            return []

        try:
            import soundfile as sf
            audio, sr = sf.read(audio_path)
            # Convert to mono float32
            if audio.ndim > 1:
                audio = audio.mean(axis=1)
            audio = audio.astype(np.float32)
        except Exception as e:
            logger.warning(f"[Diarization] Could not read audio for clustering: {e}")
            # Last resort: label everything as Speaker 1
            full_text = " ".join(seg.get("text", "") for seg in transcription_segments)
            return [SpeakerSegment(
                speaker_id="Speaker 1",
                start_time=0.0,
                end_time=transcription_segments[-1].get("end", 0) if transcription_segments else 0,
                text=full_text,
                confidence=0.5,
            )]

        # Extract voice features for each segment
        detector = SimpleSpeakerDetector()
        segments = []
        for seg in transcription_segments:
            text = seg.get("text", "").strip()
            if not text:
                continue
            start_time = seg.get("start", 0)
            end_time = seg.get("end", start_time + 0.5)

            # Extract audio chunk for this segment
            start_sample = int(start_time * sr)
            end_sample = int(end_time * sr)
            # Clamp to audio bounds
            start_sample = max(0, min(start_sample, len(audio) - 1))
            end_sample = max(start_sample + 1600, min(end_sample, len(audio)))

            chunk = audio[start_sample:end_sample]

            if len(chunk) < 800:  # Skip very short segments
                speaker = detector.last_speaker or "Speaker 1"
            else:
                speaker = detector.identify_speaker(chunk)

            segments.append(SpeakerSegment(
                speaker_id=speaker,
                start_time=start_time,
                end_time=end_time,
                text=text,
                confidence=0.6,
            ))

        # Merge consecutive segments from same speaker
        merged = self._merge_consecutive_segments(segments)

        logger.info(f"[Diarization] Whisper clustering: {len(merged)} segments, "
                     f"{len(set(s.speaker_id for s in merged))} speakers")
        return merged

    def _merge_consecutive_segments(self, segments: List[SpeakerSegment]) -> List[SpeakerSegment]:
        """Merge consecutive segments from the same speaker."""
        if not segments:
            return []
        merged = []
        current = segments[0]
        for seg in segments[1:]:
            if current.speaker_id == seg.speaker_id:
                current.end_time = seg.end_time
                current.text = (current.text + " " + seg.text).strip()
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
            # Normalize speaker labels
            label = seg.speaker_id
            if label.startswith("SPEAKER_"):
                try:
                    num = int(label.split("_")[1]) + 1
                    label = f"Speaker {num}"
                except (ValueError, IndexError):
                    pass

            if label != current_speaker:
                lines.append(f"\n[{label}]")
                current_speaker = label
            lines.append(seg.text)
        return "\n".join(lines).strip()


class SimpleSpeakerDetector:
    """
    Lightweight speaker detector using voice feature clustering.
    Uses MFCC-like features (energy, ZCR, spectral centroid, band ratios)
    to cluster audio segments by speaker similarity.
    """

    def __init__(self):
        self.speaker_profiles: Dict[str, np.ndarray] = {}
        self.next_speaker_id = 1
        self.last_speaker = "Speaker 1"

    def extract_voice_features(self, audio_chunk: np.ndarray) -> np.ndarray:
        """Extract voice features: energy, spectral shape, pitch proxy."""
        if len(audio_chunk) < 400:
            return np.zeros(7)

        # RMS energy
        rms = np.sqrt(np.mean(audio_chunk ** 2)) + 1e-10

        # Zero crossing rate
        zcr = np.mean(np.abs(np.diff(np.sign(audio_chunk))))

        # Spectral features
        fft = np.abs(np.fft.rfft(audio_chunk))
        freqs = np.fft.rfftfreq(len(audio_chunk), 1 / 16000)
        total_energy = np.sum(fft) + 1e-10

        # Spectral centroid
        centroid = np.sum(freqs * fft) / total_energy

        # Band energy ratios (low, mid, high)
        bands = [(0, 500), (500, 2000), (2000, 8000)]
        band_ratios = []
        for low, high in bands:
            mask = (freqs >= low) & (freqs < high)
            band_energy = np.sum(fft[mask])
            band_ratios.append(band_energy / total_energy)

        # Normalize energy relative to a reference to stabilize clustering
        features = np.array([
            rms,
            zcr,
            centroid / 1000.0,  # Scale down to be comparable to other features
            *band_ratios,
        ])
        return features

    def identify_speaker(self, audio_chunk: np.ndarray) -> str:
        """Identify speaker based on voice features."""
        features = self.extract_voice_features(audio_chunk)

        # Find best match among known speakers
        best_match = None
        best_distance = float('inf')

        for speaker_id, profile in self.speaker_profiles.items():
            distance = np.linalg.norm(features - profile)
            if distance < best_distance:
                best_distance = distance
                best_match = speaker_id

        # Threshold for "same speaker" — tuned for the feature scale
        # Features are [rms, zcr, centroid_kHz, band1, band2, band3]
        # After normalization, 0.6 gives good separation for typical voices
        threshold = 0.6

        if best_match and best_distance < threshold:
            # Update profile with exponential moving average
            self.speaker_profiles[best_match] = (
                0.75 * self.speaker_profiles[best_match] + 0.25 * features
            )
            self.last_speaker = best_match
            return best_match

        # New speaker
        speaker_id = f"Speaker {self.next_speaker_id}"
        self.speaker_profiles[speaker_id] = features
        self.next_speaker_id += 1
        self.last_speaker = speaker_id
        return speaker_id


# Global diarizer instance (lazy-loaded)
_diarizer: Optional[SpeakerDiarizer] = None


def get_diarizer() -> SpeakerDiarizer:
    """Get the global diarizer instance."""
    global _diarizer
    if _diarizer is None:
        _diarizer = SpeakerDiarizer()
    return _diarizer


def process_transcription_with_speakers(audio_path: str, whisper_segments: List[Dict]) -> Dict:
    """
    Process transcription with speaker diarization.

    Args:
        audio_path: Path to audio file
        whisper_segments: Segments from Whisper transcription with start/end/text

    Returns:
        Dict with 'segments', 'formatted', 'speaker_count', 'method'
    """
    diar = get_diarizer()
    segments = diar.diarize_and_transcribe(audio_path, whisper_segments)

    method = "pyannote" if diar.available else "whisper_clustering"

    return {
        "segments": [s.to_dict() for s in segments],
        "formatted": diar.format_transcript(segments),
        "speaker_count": len(set(s.speaker_id for s in segments)),
        "method": method,
    }