"""
voice_agent.py - AI Voice Agent for Real-Time Interview Assistance
T20: Biggest competitive gap - MeetGeek has this

Features:
- Voice Activity Detection (VAD) - detect when interviewer speaks
- Real-time speech-to-text using faster-whisper (not simulated)
- AI response generation using existing AI router
- Text-to-speech with Edge TTS integration
- Interruption handling (stop speaking when interrupted)
- Natural conversation flow with state machine
"""

import os
import json
import asyncio
import logging
import base64
import tempfile
import wave
from typing import Optional, Dict, Any, Callable, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

import numpy as np

logger = logging.getLogger("voice_agent")

# Try importing required libraries
try:
    import edge_tts
    HAS_EDGE_TTS = True
except ImportError:
    HAS_EDGE_TTS = False

# Import whisper transcription (same pipeline used by /ws/transcribe)
try:
    from modules.voice.whisper_handler import transcribe, clean_text, is_meaningful, is_question
    HAS_WHISPER = True
except ImportError:
    try:
        from whisper_handler import transcribe, clean_text, is_meaningful, is_question
        HAS_WHISPER = True
    except ImportError:
        HAS_WHISPER = False
        logger.warning("[VoiceAgent] Whisper handler not available — transcription disabled")

# Import AI router for response generation
try:
    from ai_router import route_ai
    HAS_AI_ROUTER = True
except ImportError:
    try:
        from modules.ai.ai_router import route_ai
        HAS_AI_ROUTER = True
    except ImportError:
        HAS_AI_ROUTER = False
        logger.warning("[VoiceAgent] AI router not available — responses disabled")


class VoiceAgentState(Enum):
    """Voice agent state machine states"""
    IDLE = "idle"              # Waiting for activation
    LISTENING = "listening"    # Listening for interviewer speech
    THINKING = "thinking"      # Processing speech, generating response
    SPEAKING = "speaking"      # Speaking the response
    INTERRUPTED = "interrupted"  # Was interrupted, transitioning to listening
    PAUSED = "paused"          # Temporarily paused


@dataclass
class VoiceAgentConfig:
    """Configuration for voice agent"""
    # VAD settings
    vad_threshold: float = 0.02
    vad_sensitivity: int = 3  # 1-5
    silence_timeout: float = 1.0  # seconds of silence before speech considered ended
    min_speech_duration: float = 0.8  # seconds — ignore very short noises

    # TTS settings
    voice: str = "en-US-AriaNeural"
    speech_rate: str = "+0%"  # Can be +50%, -20%, etc.
    speech_volume: str = "+0%"

    # Response settings
    max_response_length: int = 500  # characters
    response_delay: float = 0.3  # seconds before starting to speak
    enable_interruption: bool = True

    # AI model settings
    ai_model: str = "adaptive"
    temperature: float = 0.7
    system_prompt: str = (
        "You are an expert interview coach. The user is in a technical interview. "
        "Provide concise, clear, actionable answers. Be direct and professional. "
        "If asked a coding question, outline the approach first, then provide code. "
        "Keep responses under 150 words when possible."
    )

    # Interview context
    company: str = ""
    role: str = ""
    skills: List[str] = field(default_factory=list)
    experience: str = ""


@dataclass
class VoiceAgentSession:
    """Session data for voice agent"""
    session_id: str
    user_id: str
    started_at: datetime = field(default_factory=datetime.now)
    state: VoiceAgentState = VoiceAgentState.IDLE
    conversation_history: list = field(default_factory=list)
    current_interviewer_text: str = ""
    current_ai_response: str = ""
    interruption_count: int = 0
    total_speech_time: float = 0.0


class VoiceActivityDetector:
    """
    Voice Activity Detection using energy-based approach.
    Detects when someone is speaking based on audio energy.
    """

    def __init__(self, threshold: float = 0.02, sensitivity: int = 3):
        self.threshold = threshold
        self.sensitivity = sensitivity
        self.is_speaking = False
        self.speech_start_time: Optional[datetime] = None
        self.silence_start_time: Optional[datetime] = None
        self.buffer: list = []

    def process_audio_chunk(self, audio_data: bytes) -> Dict[str, Any]:
        """
        Process audio chunk and detect voice activity.
        audio_data: raw bytes (int16 PCM or float32 PCM)
        Returns dict with detected speech state.
        """
        try:
            audio_array = _bytes_to_float32(audio_data)
            if len(audio_array) == 0:
                return {"is_speaking": False, "confidence": 0.0}

            # Calculate RMS energy
            rms = np.sqrt(np.mean(audio_array ** 2))
            energy = float(rms)

            # Hysteresis: require slightly higher energy to start speaking than to keep speaking
            start_threshold = self.threshold * (1.0 + (3 - self.sensitivity) * 0.2)
            stop_threshold = self.threshold * 0.8

            was_speaking = self.is_speaking
            if not self.is_speaking:
                self.is_speaking = energy > start_threshold
            else:
                self.is_speaking = energy > stop_threshold

            result = {
                "is_speaking": self.is_speaking,
                "energy": energy,
                "confidence": min(1.0, energy / (self.threshold * 3))
            }

            now = datetime.now()

            # State transitions
            if self.is_speaking and not was_speaking:
                self.speech_start_time = now
                self.silence_start_time = None
                result["event"] = "speech_started"
            elif not self.is_speaking and was_speaking:
                self.silence_start_time = now
                if self.speech_start_time:
                    duration = (now - self.speech_start_time).total_seconds()
                    result["event"] = "speech_ended"
                    result["duration"] = duration
                    self.speech_start_time = None
            elif not self.is_speaking and self.silence_start_time:
                silence_duration = (now - self.silence_start_time).total_seconds()
                result["silence_duration"] = silence_duration

            return result

        except Exception as e:
            logger.error("[VAD] Processing error: %s", str(e))
            return {"is_speaking": False, "error": "An internal error occurred"}

    def reset(self):
        """Reset VAD state"""
        self.is_speaking = False
        self.speech_start_time = None
        self.silence_start_time = None
        self.buffer = []


class TextToSpeechEngine:
    """
    Text-to-speech engine using Edge TTS.
    Provides streaming audio for low latency.
    """

    def __init__(self, config: VoiceAgentConfig):
        self.config = config
        self.is_speaking = False
        self.current_text = ""
        self._stop_requested = False

    async def speak(self, text: str, on_chunk: Optional[Callable] = None) -> bool:
        """
        Convert text to speech.
        Optionally streams chunks via callback.
        """
        if not HAS_EDGE_TTS:
            logger.warning("[TTS] Edge TTS not available")
            return False

        if not text:
            return False

        self.is_speaking = True
        self.current_text = text
        self._stop_requested = False

        try:
            communicate = edge_tts.Communicate(
                text,
                self.config.voice,
                rate=self.config.speech_rate,
                volume=self.config.speech_volume
            )

            async for chunk in communicate.stream():
                if self._stop_requested:
                    break
                if chunk["type"] == "audio":
                    if on_chunk:
                        await on_chunk(chunk["data"])

            return not self._stop_requested

        except Exception as e:
            logger.error("[TTS] Speech generation failed: %s", str(e))
            return False

        finally:
            self.is_speaking = False
            self.current_text = ""

    async def stop(self):
        """Stop current speech"""
        self._stop_requested = True
        self.is_speaking = False

    def is_active(self) -> bool:
        """Check if TTS is currently speaking"""
        return self.is_speaking


class AIResponseGenerator:
    """
    Generates AI responses using the existing AI router.
    Maintains conversation context.
    """

    def __init__(self, config: VoiceAgentConfig):
        self.config = config

    def _build_prompt(self, interviewer_question: str, conversation_history: list) -> str:
        """Build a string prompt for route_ai from context and history."""
        parts = []

        # System prompt
        parts.append(self.config.system_prompt)

        # Interview context
        context_parts = []
        if self.config.company:
            context_parts.append(f"Company: {self.config.company}")
        if self.config.role:
            context_parts.append(f"Role: {self.config.role}")
        if self.config.experience:
            context_parts.append(f"Experience: {self.config.experience}")
        if self.config.skills:
            context_parts.append(f"Skills: {', '.join(self.config.skills)}")

        if context_parts:
            parts.append("\nInterview Context:\n" + "\n".join(context_parts))

        # Conversation history (last 3 exchanges)
        if conversation_history:
            parts.append("\nConversation so far:")
            for msg in conversation_history[-6:]:
                role_label = "Interviewer" if msg.get("role") == "user" else "Candidate"
                parts.append(f"{role_label}: {msg.get('content', '')}")

        # Current question
        parts.append(f"\nInterviewer just asked: {interviewer_question}")
        parts.append("\nProvide a concise, helpful response for the candidate:")

        return "\n".join(parts)

    async def generate_response(
        self,
        interviewer_question: str,
        conversation_history: list
    ) -> str:
        """
        Generate AI response to interviewer's question.
        """
        if not HAS_AI_ROUTER:
            logger.warning("[AI] AI router not available, using fallback")
            return self._fallback_response(interviewer_question)

        try:
            prompt = self._build_prompt(interviewer_question, conversation_history)

            # Run route_ai in thread pool since it's sync
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: route_ai(prompt, mode=self.config.ai_model, style="concise")
            )

            response = result.get("response", "")
            if response and response not in {"AI error", "AI service unavailable.", ""}:
                return response

            logger.warning("[AI] Empty or error response from router")
            return self._fallback_response(interviewer_question)

        except Exception as e:
            logger.error("[AI] Response generation failed: %s", str(e))
            return "I'm sorry, I couldn't generate a response right now."

    def _fallback_response(self, question: str) -> str:
        """Fallback response when AI router unavailable"""
        return (
            f"I heard the question about '{question[:50]}...'. "
            "I'm having trouble connecting to the AI service right now. "
            "Try rephrasing or ask again in a moment."
        )


# ==============================
# AUDIO UTILITIES
# ==============================

def _bytes_to_float32(audio_data: bytes) -> np.ndarray:
    """
    Convert raw audio bytes to float32 numpy array.
    Auto-detects int16 vs float32 based on byte count divisibility.
    """
    if not audio_data:
        return np.array([], dtype=np.float32)

    # Try float32 first (4 bytes per sample)
    if len(audio_data) % 4 == 0:
        try:
            arr = np.frombuffer(audio_data, dtype=np.float32)
            # Heuristic: if values are in reasonable float32 range (-1 to 1 mostly), use it
            if len(arr) > 0 and np.abs(arr).max() <= 2.0:
                return arr
        except Exception:
            pass

    # Fall back to int16 (2 bytes per sample)
    if len(audio_data) % 2 == 0:
        try:
            arr = np.frombuffer(audio_data, dtype=np.int16)
            return arr.astype(np.float32) / 32768.0
        except Exception:
            pass

    # Last resort: interpret as uint8
    arr = np.frombuffer(audio_data, dtype=np.uint8)
    return (arr.astype(np.float32) - 128.0) / 128.0


def _bytes_to_wav_file(audio_data: bytes, sample_rate: int = 16000) -> str:
    """Convert raw PCM bytes to a temporary WAV file for transcription."""
    float32_arr = _bytes_to_float32(audio_data)
    if len(float32_arr) == 0:
        return ""

    # Convert float32 (-1.0 to 1.0) to int16 for WAV
    int16_arr = (float32_arr * 32767).astype(np.int16)

    fd, path = tempfile.mkstemp(suffix=".wav")
    try:
        with wave.open(path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(int16_arr.tobytes())
        return path
    except Exception:
        os.close(fd)
        raise


# ==============================
# MAIN VOICE AGENT
# ==============================

class VoiceAgent:
    """
    Main voice agent that coordinates VAD, STT, AI response generation, and TTS.
    Provides real-time interview assistance.
    """

    def __init__(self, config: Optional[VoiceAgentConfig] = None):
        self.config = config or VoiceAgentConfig()
        self.session: Optional[VoiceAgentSession] = None

        # Components
        self.vad = VoiceActivityDetector(
            self.config.vad_threshold,
            self.config.vad_sensitivity
        )
        self.tts = TextToSpeechEngine(self.config)
        self.ai = AIResponseGenerator(self.config)

        # State
        self._state = VoiceAgentState.IDLE
        self._state_listeners: list = []

        # Audio buffer for STT (accumulated during LISTENING)
        self._listen_buffer: List[bytes] = []
        self._listen_buffer_bytes: int = 0
        self._max_listen_buffer_mb: int = 10  # Safety limit

    @property
    def state(self) -> VoiceAgentState:
        return self._state

    def _set_state(self, new_state: VoiceAgentState):
        """Update state and notify listeners"""
        old_state = self._state
        self._state = new_state
        if self.session:
            self.session.state = new_state

        for listener in self._state_listeners:
            try:
                listener(old_state, new_state)
            except Exception as e:
                logger.error("[VoiceAgent] State listener error: %s", str(e))

    def add_state_listener(self, listener: Callable[[VoiceAgentState, VoiceAgentState], None]):
        """Add a state change listener"""
        self._state_listeners.append(listener)

    def remove_state_listener(self, listener: Callable):
        """Remove a state change listener"""
        if listener in self._state_listeners:
            self._state_listeners.remove(listener)

    async def start_session(self, user_id: str, session_id: Optional[str] = None) -> VoiceAgentSession:
        """Start a new voice agent session"""
        self.session = VoiceAgentSession(
            session_id=session_id or f"va_{datetime.now().timestamp()}",
            user_id=user_id,
            state=VoiceAgentState.IDLE
        )
        self._set_state(VoiceAgentState.IDLE)
        self._listen_buffer = []
        self._listen_buffer_bytes = 0
        logger.info("[VoiceAgent] Session started: %s", self.session.session_id)
        return self.session

    async def end_session(self):
        """End the current session"""
        if self.tts.is_active():
            await self.tts.stop()

        if self.session:
            logger.info("[VoiceAgent] Session ended: %s", self.session.session_id)
            self.session = None

        self._set_state(VoiceAgentState.IDLE)
        self._state_listeners.clear()
        self._listen_buffer = []
        self._listen_buffer_bytes = 0

    async def process_audio(self, audio_data: bytes) -> Dict[str, Any]:
        """
        Process incoming audio chunk.
        Returns action that frontend should take.
        """
        if not self.session:
            return {"action": "error", "message": "No active session"}

        if not audio_data:
            return {"action": "continue"}

        # Accumulate audio during listening for later transcription
        if self.state == VoiceAgentState.LISTENING:
            self._accumulate_audio(audio_data)

        # Run VAD
        vad_result = self.vad.process_audio_chunk(audio_data)

        # State machine logic
        if self.state == VoiceAgentState.IDLE:
            return await self._handle_idle(vad_result)
        elif self.state == VoiceAgentState.LISTENING:
            return await self._handle_listening(vad_result)
        elif self.state == VoiceAgentState.THINKING:
            return await self._handle_thinking(vad_result)
        elif self.state == VoiceAgentState.SPEAKING:
            return await self._handle_speaking(vad_result)
        elif self.state == VoiceAgentState.INTERRUPTED:
            return await self._handle_interrupted(vad_result)

        return {"action": "continue"}

    def _accumulate_audio(self, audio_data: bytes):
        """Add audio to the listening buffer."""
        self._listen_buffer.append(audio_data)
        self._listen_buffer_bytes += len(audio_data)

        # Safety: drop old audio if buffer exceeds limit
        max_bytes = self._max_listen_buffer_mb * 1024 * 1024
        while self._listen_buffer_bytes > max_bytes and self._listen_buffer:
            dropped = self._listen_buffer.pop(0)
            self._listen_buffer_bytes -= len(dropped)

    def _flush_listen_buffer(self) -> bytes:
        """Return accumulated audio and clear buffer."""
        combined = b"".join(self._listen_buffer)
        self._listen_buffer = []
        self._listen_buffer_bytes = 0
        return combined

    async def _handle_idle(self, vad_result: Dict) -> Dict[str, Any]:
        """Handle IDLE state"""
        if vad_result.get("is_speaking"):
            self._set_state(VoiceAgentState.LISTENING)
            return {"action": "start_listening"}
        return {"action": "wait"}

    async def _handle_listening(self, vad_result: Dict) -> Dict[str, Any]:
        """Handle LISTENING state"""
        event = vad_result.get("event")

        if event == "speech_ended":
            duration = vad_result.get("duration", 0)
            if duration >= self.config.min_speech_duration:
                # Transcribe the buffered audio
                audio_bytes = self._flush_listen_buffer()
                transcript = await self._transcribe_audio(audio_bytes)

                if transcript and is_meaningful(transcript):
                    logger.info("[VoiceAgent] Transcribed: %s", transcript[:80])
                    if self.session:
                        self.session.current_interviewer_text = transcript

                    self._set_state(VoiceAgentState.THINKING)
                    return {
                        "action": "thinking",
                        "speech_duration": duration,
                        "transcript": transcript
                    }
                else:
                    logger.debug("[VoiceAgent] Speech too short or meaningless, returning to idle")
                    self._set_state(VoiceAgentState.IDLE)
                    return {"action": "wait", "reason": "no_meaningful_speech"}
            else:
                # Too short — ignore and go back to idle
                self._flush_listen_buffer()
                self._set_state(VoiceAgentState.IDLE)
                return {"action": "wait", "reason": "too_short"}

        # If silence has persisted past timeout, force end of speech
        silence_duration = vad_result.get("silence_duration", 0)
        if silence_duration >= self.config.silence_timeout and self._listen_buffer_bytes > 0:
            audio_bytes = self._flush_listen_buffer()
            transcript = await self._transcribe_audio(audio_bytes)

            if transcript and is_meaningful(transcript):
                if self.session:
                    self.session.current_interviewer_text = transcript
                self._set_state(VoiceAgentState.THINKING)
                return {
                    "action": "thinking",
                    "speech_duration": silence_duration,
                    "transcript": transcript
                }
            else:
                self._set_state(VoiceAgentState.IDLE)
                return {"action": "wait", "reason": "silence_no_speech"}

        return {"action": "continue_listening", "is_speaking": vad_result.get("is_speaking")}

    async def _transcribe_audio(self, audio_bytes: bytes) -> str:
        """Transcribe audio bytes to text using faster-whisper."""
        if not HAS_WHISPER:
            logger.warning("[VoiceAgent] Whisper not available, cannot transcribe")
            return ""

        if len(audio_bytes) < 3200:  # ~100ms at 16kHz float32
            return ""

        try:
            # Convert bytes to float32 numpy array
            audio_array = _bytes_to_float32(audio_bytes)

            if len(audio_array) == 0:
                return ""

            # Run transcription in thread pool (transcribe is CPU-bound)
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: transcribe(audio_array, mode="interview", streaming=False, language="en")
            )

            text = result.get("text", "") if isinstance(result, dict) else str(result)
            cleaned = clean_text(text) if text else None
            return cleaned or text.strip()

        except Exception as e:
            logger.error("[VoiceAgent] Transcription error: %s", str(e))
            return ""

    async def _handle_thinking(self, vad_result: Dict) -> Dict[str, Any]:
        """Handle THINKING state — generate AI response"""
        question = self.session.current_interviewer_text if self.session else "What do you think?"

        try:
            response = await self.ai.generate_response(
                question,
                self.session.conversation_history if self.session else [],
            )

            if self.session:
                self.session.current_ai_response = response
                self.session.conversation_history.append({"role": "user", "content": question})
                self.session.conversation_history.append({"role": "assistant", "content": response})

            self._set_state(VoiceAgentState.SPEAKING)

            # Start TTS in background (fire-and-forget; frontend can also play it)
            asyncio.create_task(self.tts.speak(response))

            return {"action": "speak", "text": response}

        except Exception as e:
            logger.error("[VoiceAgent] Thinking error: %s", str(e))
            self._set_state(VoiceAgentState.IDLE)
            return {"action": "error", "message": "An internal error occurred"}

    async def _handle_speaking(self, vad_result: Dict) -> Dict[str, Any]:
        """Handle SPEAKING state - check for interruptions"""
        if not self.config.enable_interruption:
            return {"action": "continue_speaking"}

        # Check if someone started speaking (interruption)
        if vad_result.get("is_speaking"):
            self._set_state(VoiceAgentState.INTERRUPTED)
            if self.session:
                self.session.interruption_count += 1
            await self.tts.stop()
            return {"action": "interrupted", "message": "Interruption detected"}

        if not self.tts.is_active():
            # Finished speaking
            self._set_state(VoiceAgentState.IDLE)
            return {"action": "finished_speaking"}

        return {"action": "continue_speaking"}

    async def _handle_interrupted(self, vad_result: Dict) -> Dict[str, Any]:
        """Handle INTERRUPTED state - transition back to listening"""
        self._set_state(VoiceAgentState.LISTENING)
        return {"action": "resume_listening"}

    async def speak_text(self, text: str) -> bool:
        """
        Speak the given text using TTS.
        Returns True if successful.
        """
        return await self.tts.speak(text)

    def get_session_stats(self) -> Dict[str, Any]:
        """Get current session statistics"""
        if not self.session:
            return {"error": "No active session"}

        duration = (datetime.now() - self.session.started_at).total_seconds()

        return {
            "session_id": self.session.session_id,
            "duration_seconds": duration,
            "state": self.session.state.value,
            "interruptions": self.session.interruption_count,
            "total_speech_time": self.session.total_speech_time,
            "conversation_turns": len(self.session.conversation_history) // 2,
        }

    def update_config(self, **kwargs):
        """Update configuration fields."""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
        # Re-initialize components that depend on config
        self.vad = VoiceActivityDetector(self.config.vad_threshold, self.config.vad_sensitivity)
        self.tts = TextToSpeechEngine(self.config)
        self.ai = AIResponseGenerator(self.config)


# Global voice agent instance
voice_agent = VoiceAgent()


# ==============================
# API Functions
# ==============================

async def create_session(user_id: str, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Create a new voice agent session"""
    agent = voice_agent
    if config:
        agent.update_config(**config)
    session = await agent.start_session(user_id)
    return {
        "session_id": session.session_id,
        "status": "created",
        "config": {
            "voice": agent.config.voice,
            "enable_interruption": agent.config.enable_interruption,
            "company": agent.config.company,
            "role": agent.config.role,
        }
    }


async def process_audio_chunk(session_id: str, audio_data: bytes) -> Dict[str, Any]:
    """Process audio chunk for the global voice agent session"""
    return await voice_agent.process_audio(audio_data)


async def end_session(session_id: str) -> Dict[str, Any]:
    """End the voice agent session"""
    await voice_agent.end_session()
    return {"status": "ended", "session_id": session_id}


def get_status() -> Dict[str, Any]:
    """Get voice agent status"""
    return {
        "available": HAS_EDGE_TTS and HAS_WHISPER and HAS_AI_ROUTER,
        "edge_tts": HAS_EDGE_TTS,
        "whisper": HAS_WHISPER,
        "ai_router": HAS_AI_ROUTER,
        "current_state": voice_agent.state.value if voice_agent else "idle",
    }


__all__ = [
    "VoiceAgent",
    "VoiceAgentConfig",
    "VoiceAgentSession",
    "VoiceAgentState",
    "VoiceActivityDetector",
    "TextToSpeechEngine",
    "AIResponseGenerator",
    "voice_agent",
    "create_session",
    "process_audio_chunk",
    "end_session",
    "get_status",
]
