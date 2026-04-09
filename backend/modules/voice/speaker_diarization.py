"""
speaker_diarization.py - Speaker Diarization for AI Note Taker

Features:
- Identify different speakers in audio
- Label transcript segments with speaker IDs
- Merge short segments from same speaker
- Support for pyannote.audio (if available) or fallback to energy-based segmentation
"""

import logging
import numpy as np
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import time

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
    Speaker diarization using speaker embeddings.
    Falls back to simple energy-based segmentation if pyannote.audio is not available.
    """

    def __init__(self):
        self.pipeline = None
        self.embedding_model = None
        self.available = False
        self._load_models()

    def _load_models(self):
        """Try to load pyannote models if available."""
        try:
            from pyannote.audio.pipelines.speaker_verification import PretrainedSpeakerEmbedding
            from pyannote.audio import Pipeline
            import torch

            # Load diarization pipeline
            self.pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                use_auth_token=None  # Will use local cache or download
            )

            # Load embedding model for clustering
            self.embedding_model = PretrainedSpeakerEmbedding(
                "speechbrain/ecapa-tdnn",
                device=torch.device("cuda" if torch.cuda.is_available() else "cpu")
            )

            self.available = True
            logger.info("Speaker diarization models loaded successfully")
        except ImportError:
            logger.warning("pyannote.audio not available - using fallback segmentation")
            self.available = False
        except Exception as e:
            logger.warning(f"Failed to load speaker models: {e} - using fallback")
            self.available = False

    def diarize_audio(self, audio_path: str, num_speakers: Optional[int] = None) -> List[SpeakerSegment]:
        """
        Perform speaker diarization on an audio file.

        Args:
            audio_path: Path to audio file
            num_speakers: Expected number of speakers (None for auto)

        Returns:
            List of SpeakerSegment objects
        """
        if not self.available:
            return self._fallback_segmentation(audio_path)

        try:
            # Run diarization
            diarization = self.pipeline(audio_path, num_speakers=num_speakers)

            segments = []
            for turn, _, speaker in diarization.itertracks(yield_label=True):
                segments.append(SpeakerSegment(
                    speaker_id=speaker,
                    start_time=turn.start,
                    end_time=turn.end,
                    text="",  # Text will be filled after transcription
                    confidence=0.9
                ))

            logger.info(f"Diarization complete: {len(segments)} segments, speakers: {len(set(s.speaker_id for s in segments))}")
            return segments

        except Exception as e:
            logger.error(f"Diarization failed: {e}")
            return self._fallback_segmentation(audio_path)

    def _fallback_segmentation(self, audio_path: str) -> List[SpeakerSegment]:
        """
        Fallback: Create single segment (no diarization).
        This is used when pyannote is not available.
        """
        import soundfile as sf

        try:
            info = sf.info(audio_path)
            duration = info.duration
            return [SpeakerSegment(
                speaker_id="Speaker 1",
                start_time=0.0,
                end_time=duration,
                text="",
                confidence=1.0
            )]
        except Exception as e:
            logger.error(f"Fallback segmentation failed: {e}")
            return []

    def diarize_and_transcribe(self, audio_path: str, transcription_segments: List[Dict]) -> List[SpeakerSegment]:
        """
        Combine diarization with existing transcription segments.

        Args:
            audio_path: Path to audio file
            transcription_segments: List of transcription segments from Whisper

        Returns:
            List of SpeakerSegment with text and speaker labels
        """
        # Get speaker segments
        speaker_segments = self.diarize_audio(audio_path)

        if not speaker_segments or len(speaker_segments) == 1:
            # No diarization available, use single speaker
            full_text = " ".join(seg.get("text", "") for seg in transcription_segments)
            return [SpeakerSegment(
                speaker_id="Speaker 1",
                start_time=0.0,
                end_time=transcription_segments[-1].get("end", 0) if transcription_segments else 0,
                text=full_text,
                confidence=1.0
            )]

        # Map transcription segments to speakers based on timing
        combined = []
        for trans_seg in transcription_segments:
            trans_start = trans_seg.get("start", 0)
            trans_end = trans_seg.get("end", trans_start + 1)
            trans_text = trans_seg.get("text", "").strip()

            if not trans_text:
                continue

            # Find overlapping speaker segments
            best_speaker = "Speaker 1"
            best_overlap = 0

            for spk_seg in speaker_segments:
                # Calculate overlap
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
                confidence=0.8
            ))

        # Merge consecutive segments from same speaker
        merged = self._merge_consecutive_segments(combined)

        return merged

    def _merge_consecutive_segments(self, segments: List[SpeakerSegment]) -> List[SpeakerSegment]:
        """Merge consecutive segments from the same speaker."""
        if not segments:
            return []

        merged = []
        current = None

        for seg in segments:
            if current is None:
                current = seg
            elif current.speaker_id == seg.speaker_id:
                # Merge with current
                current.end_time = seg.end_time
                current.text = current.text + " " + seg.text
                current.confidence = min(current.confidence, seg.confidence)
            else:
                merged.append(current)
                current = seg

        if current:
            merged.append(current)

        return merged

    def format_transcript(self, segments: List[SpeakerSegment]) -> str:
        """Format speaker segments as a readable transcript."""
        lines = []
        current_speaker = None

        for seg in segments:
            # Normalize speaker labels (SPEAKER_00 -> Speaker 1)
            speaker_label = seg.speaker_id
            if speaker_label.startswith("SPEAKER_"):
                try:
                    speaker_num = int(speaker_label.split("_")[1]) + 1
                    speaker_label = f"Speaker {speaker_num}"
                except:
                    pass

            if speaker_label != current_speaker:
                lines.append(f"\n[{speaker_label}]")
                current_speaker = speaker_label

            lines.append(seg.text)

        return "\n".join(lines).strip()


class SimpleSpeakerDetector:
    """
    Simple speaker detection based on voice characteristics.
    Used as a lightweight alternative to full diarization.
    """

    def __init__(self):
        self.speaker_profiles = {}
        self.next_speaker_id = 1

    def extract_voice_features(self, audio_chunk: np.ndarray) -> np.ndarray:
        """
        Extract simple voice features from audio.
        Uses MFCC-like features (energy bands).
        """
        # Simple energy-based features
        features = []

        # RMS energy
        rms = np.sqrt(np.mean(audio_chunk ** 2))
        features.append(rms)

        # Zero crossing rate
        zcr = np.mean(np.abs(np.diff(np.sign(audio_chunk))))
        features.append(zcr)

        # Spectral centroid approximation (using FFT)
        fft = np.abs(np.fft.rfft(audio_chunk))
        freqs = np.fft.rfftfreq(len(audio_chunk), 1/16000)
        if np.sum(fft) > 0:
            centroid = np.sum(freqs * fft) / np.sum(fft)
            features.append(centroid)
        else:
            features.append(0)

        # Band energy ratios
        bands = [(0, 500), (500, 2000), (2000, 8000)]
        for low, high in bands:
            band_mask = (freqs >= low) & (freqs < high)
            band_energy = np.sum(fft[band_mask])
            total_energy = np.sum(fft) + 1e-10
            features.append(band_energy / total_energy)

        return np.array(features)

    def identify_speaker(self, audio_chunk: np.ndarray) -> str:
        """Identify speaker based on voice features."""
        features = self.extract_voice_features(audio_chunk)

        # Find best match among known speakers
        best_match = None
        best_score = float('inf')

        for speaker_id, profile in self.speaker_profiles.items():
            distance = np.linalg.norm(features - profile['features'])
            if distance < best_score and distance < 0.5:  # Threshold
                best_score = distance
                best_match = speaker_id

        if best_match:
            # Update profile
            self.speaker_profiles[best_match]['features'] = 0.8 * self.speaker_profiles[best_match]['features'] + 0.2 * features
            return best_match
        else:
            # New speaker
            speaker_id = f"Speaker {self.next_speaker_id}"
            self.speaker_profiles[speaker_id] = {'features': features}
            self.next_speaker_id += 1
            return speaker_id


# Global diarizer instance
diarizer = SpeakerDiarizer()


def get_diarizer() -> SpeakerDiarizer:
    """Get the global diarizer instance."""
    return diarizer


def process_transcription_with_speakers(audio_path: str, whisper_segments: List[Dict]) -> Dict:
    """
    Process transcription with speaker diarization.

    Args:
        audio_path: Path to audio file
        whisper_segments: Segments from Whisper transcription

    Returns:
        Dict with 'segments' (list of SpeakerSegment) and 'formatted' (string)
    """
    diar = get_diarizer()
    segments = diar.diarize_and_transcribe(audio_path, whisper_segments)

    return {
        "segments": [s.to_dict() for s in segments],
        "formatted": diar.format_transcript(segments),
        "speaker_count": len(set(s.speaker_id for s in segments))
    }
