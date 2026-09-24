"""
vad_segmenter.py — utterance segmentation for the live interview assist.

Why this exists (2026-09-11): the live path used to transcribe fixed 1.5s
slices and then guess, from the resulting text, where a question began and
ended. That guessing is what produced the garbling ("greatest strength" ->
"greatest spread": words cut mid-boundary), hints fired on half-questions
(the transcript lags the audio by at least a slice), and the pile of repair
heuristics layered on top — question-starter scans, word-count floors,
refinement exceptions, stale-generation drops.

Silence is measurable directly on the audio within ~100ms, so we take the
boundary from the sound itself and hand Whisper a COMPLETE utterance exactly
once. This is the approach the open-source Cluely-class assistants use
(cheating-daddy's energy VAD; Glass delegates to server-side VAD).
"""

from collections import deque

import numpy as np

DEFAULT_SAMPLE_RATE = 16000


class VadSegmenter:
    """Splits a live PCM stream into complete spoken utterances.

    Feed it float32 PCM with `add_chunk()`; it returns a list of finished
    utterances (usually empty). Chunk sizes are arbitrary — audio is
    re-framed internally, so callers don't have to align to frame
    boundaries.

    Defaults are tuned for a 16kHz mono interview stream:
      - 100ms frames, matching the granularity competitors run at;
      - speech starts after 2 voiced frames (~200ms), which rejects clicks
        without clipping a real word;
      - speech ends after 10 silent frames (~1.0s), honouring the project's
        "settle window is never padded" speed rule while still tolerating
        the mid-sentence pauses interviewers actually take.
    """

    def __init__(
        self,
        sample_rate: int = DEFAULT_SAMPLE_RATE,
        frame_ms: int = 100,
        energy_threshold: float = 0.01,
        noise_ratio: float = 3.0,
        noise_window_frames: int = 150,
        max_noise_threshold: float = 0.06,
        speech_frames_required: int = 2,
        silence_frames_required: int = 10,
        preroll_frames: int = 3,
        min_utterance_ms: int = 400,
        max_utterance_ms: int = 30000,
    ):
        self.sample_rate = sample_rate
        self.frame_ms = frame_ms
        self.frame_samples = max(1, int(sample_rate * frame_ms / 1000))
        self.energy_threshold = energy_threshold
        self.noise_ratio = noise_ratio
        self.max_noise_threshold = max(energy_threshold, max_noise_threshold)
        self.speech_frames_required = speech_frames_required
        self.silence_frames_required = silence_frames_required
        self.min_utterance_frames = max(1, int(min_utterance_ms / frame_ms))
        self.max_utterance_frames = max(1, int(max_utterance_ms / frame_ms))

        # Rolling RMS history for the adaptive floor. A FIXED threshold dies
        # in a real room: measured 2026-09-11, once ambient noise passed 0.015
        # the end-of-speech condition could never be met, so no hint fired for
        # the whole call and nothing reported an error. The threshold has to
        # follow the room.
        self._recent_rms = deque(maxlen=max(10, noise_window_frames))
        self._threshold = energy_threshold

        self._residual = np.zeros(0, dtype=np.float32)
        # Frames held back from before speech was confirmed. Without this the
        # utterance would start mid-word, because the frames that PROVED
        # speech began are already in the past by the time we know it.
        self._preroll = deque(maxlen=max(0, preroll_frames))
        self._utterance = []
        self._speech_run = 0
        self._silence_run = 0
        self._voiced_in_utterance = 0
        self.is_speaking = False

    @staticmethod
    def _rms(frame: np.ndarray) -> float:
        if frame.size == 0:
            return 0.0
        wide = frame.astype(np.float64, copy=False)
        return float(np.sqrt(np.mean(wide * wide)))

    def add_chunk(self, chunk) -> list:
        """Feed PCM. Returns any utterances that completed on this chunk."""
        if chunk is None or len(chunk) == 0:
            return []
        chunk = np.asarray(chunk, dtype=np.float32).reshape(-1)
        self._residual = (
            np.concatenate([self._residual, chunk])
            if self._residual.size
            else chunk
        )

        finished = []
        while self._residual.size >= self.frame_samples:
            frame = self._residual[: self.frame_samples]
            self._residual = self._residual[self.frame_samples :]
            done = self._process_frame(frame)
            if done is not None:
                finished.append(done)
        return finished

    def _update_threshold(self, rms: float) -> float:
        """Track the room's noise floor and keep the bar above it.

        A low percentile of recent frames is the ambient level: speech is the
        loud minority, so the quiet fifth is the room itself. Estimating it
        this way adapts in BOTH directions, unlike a floor that only updates
        while silent — which gets stuck the moment noise rises enough to read
        as continuous speech. `energy_threshold` remains an absolute minimum
        so a perfectly quiet room doesn't drive the bar toward zero.
        """
        self._recent_rms.append(rms)
        # 10th percentile, not 20th: during a long question speech can occupy
        # most of the window, and too high a percentile then reads the SPEECH
        # as the floor and raises the bar above the voice it is meant to hear.
        # A percentile rather than the raw minimum keeps one dropout frame
        # from collapsing the estimate. 2s of history before adapting, so the
        # first question of a session isn't judged on three frames.
        if len(self._recent_rms) >= 20:
            floor = float(np.percentile(np.fromiter(self._recent_rms, dtype=np.float64), 10))
            # A session can begin with speech and no ambient-only lead-in.
            # Do not let that speech become an arbitrarily high noise floor:
            # it previously cut a continuous question after only 1.3 seconds.
            self._threshold = max(self.energy_threshold, min(self.max_noise_threshold, floor * self.noise_ratio))
        return self._threshold

    @property
    def current_threshold(self) -> float:
        """Live speech threshold — useful when diagnosing a silent session."""
        return self._threshold

    def _process_frame(self, frame: np.ndarray):
        rms = self._rms(frame)
        voiced = rms > self._update_threshold(rms)

        if voiced:
            self._speech_run += 1
            self._silence_run = 0
            if not self.is_speaking and self._speech_run >= self.speech_frames_required:
                self.is_speaking = True
                self._utterance = list(self._preroll)
                self._voiced_in_utterance = 0
                self._preroll.clear()
        else:
            self._silence_run += 1
            self._speech_run = 0
            if self.is_speaking and self._silence_run >= self.silence_frames_required:
                return self._finish()

        if self.is_speaking:
            self._utterance.append(frame)
            if voiced:
                self._voiced_in_utterance += 1
            if len(self._utterance) >= self.max_utterance_frames:
                # Runaway speaker: cut here so the assist still answers
                # instead of buffering without bound.
                return self._finish(force=True)
        else:
            self._preroll.append(frame)
        return None

    def _finish(self, force: bool = False):
        frames = self._utterance
        voiced_frames = self._voiced_in_utterance
        self._utterance = []
        self._voiced_in_utterance = 0
        self._preroll.clear()

        if force:
            # Mid-sentence cut — stay in speaking state so the rest of the
            # sentence keeps accumulating as the next utterance.
            self._silence_run = 0
        else:
            self.is_speaking = False
            self._speech_run = 0
            self._silence_run = 0

        frames = self._trim_trailing_silence(frames)
        # Gate on ACTUAL speech, not buffer length: preroll and the decay tail
        # would otherwise let a 250ms door-slam through the min-length check.
        if voiced_frames < self.min_utterance_frames:
            return None  # click, cough, or a door — too short to be speech
        return np.concatenate(frames).astype(np.float32)

    def _trim_trailing_silence(self, frames, keep: int = 2):
        """Drop the silence the speaker left at the end.

        A finished utterance always carries the silence that proved it ended
        (~0.9s by default). Handing that to Whisper costs decode time for no
        information, and every millisecond here lands directly on the
        question-end -> first-hint latency the project is gated on. A couple
        of frames stay so soft word endings aren't clipped.
        """
        end = len(frames)
        while end > 0 and self._rms(frames[end - 1]) <= self._threshold:
            end -= 1
        return frames[: min(len(frames), end + keep)]

    def peek(self):
        """Copy the in-progress utterance WITHOUT consuming it.

        Used for rolling previews while the interviewer is still speaking: the
        question so far can be transcribed and answered provisionally, and the
        real boundary still arrives later untouched. Returns None when nobody
        is mid-sentence.
        """
        if not self.is_speaking or not self._utterance:
            return None
        return np.concatenate(list(self._utterance)).astype(np.float32)

    def flush(self, force: bool = False):
        """Hand back the utterance still in progress, if any.

        `force` is the manual cut (the user pressing Enter to say "the question
        ends here, answer it"). It takes whatever audio is buffered without
        waiting for silence and without applying the minimum-length gate: an
        explicit request is not a door slam, and second-guessing it would make
        the key feel broken.
        """
        if force:
            frames = list(self._utterance) + list(self._preroll)
            self._utterance = []
            self._preroll.clear()
            self._voiced_in_utterance = 0
            self.is_speaking = False
            self._speech_run = 0
            self._silence_run = 0
            self._residual = np.zeros(0, dtype=np.float32)
            if not frames:
                return None
            return np.concatenate(frames).astype(np.float32)
        if not self.is_speaking:
            self._utterance = []
            self._preroll.clear()
            return None
        return self._finish()
