"""
voice_agent.py - AI Voice Agent for Real-Time Interview Assistance
T20: Biggest competitive gap - MeetGeek has this

Features:
- Voice Activity Detection (VAD) - detect when interviewer speaks
- Real-time speech-to-text for interviewer questions
- AI response generation using existing AI router
- Text-to-speech with Edge TTS integration
- Interruption handling (stop speaking when interrupted)
- Natural conversation flow with state machine
"""

import os
import json
import asyncio
import logging
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger("voice_agent")

# Try importing required libraries
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

try:
    import edge_tts
    HAS_EDGE_TTS = True
except ImportError:
    HAS_EDGE_TTS = False


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
    silence_timeout: float = 2.0  # seconds
    min_speech_duration: float = 0.5  # seconds

    # TTS settings
    voice: str = "en-US-AriaNeural"
    speech_rate: str = "+0%"  # Can be +50%, -20%, etc.
    speech_volume: str = "+0%"

    # Response settings
    max_response_length: int = 500  # characters
    response_delay: float = 0.5  # seconds before starting to speak
    enable_interruption: bool = True

    # AI model settings
    ai_model: str = "gpt-4"
    temperature: float = 0.7
    system_prompt: str = "You are a helpful assistant in a technical interview. Provide concise, clear answers."


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
        Returns dict with detected speech state.
        """
        if not HAS_NUMPY:
            return {"is_speaking": False, "confidence": 0.0}

        try:
            # Convert bytes to numpy array (assuming 16-bit PCM)
            audio_array = np.frombuffer(audio_data, dtype=np.int16)

            # Calculate RMS energy
            if len(audio_array) > 0:
                rms = np.sqrt(np.mean(audio_array.astype(np.float32) ** 2))
                # Normalize to 0-1 range (assuming 16-bit max value)
                energy = rms / 32768.0
            else:
                energy = 0.0

            # Detect speech based on threshold
            was_speaking = self.is_speaking
            self.is_speaking = energy > self.threshold

            result = {
                "is_speaking": self.is_speaking,
                "energy": energy,
                "confidence": min(1.0, energy / (self.threshold * 2))
            }

            # State transitions
            if self.is_speaking and not was_speaking:
                # Speech started
                self.speech_start_time = datetime.now()
                result["event"] = "speech_started"
            elif not self.is_speaking and was_speaking:
                # Speech ended
                if self.speech_start_time:
                    duration = (datetime.now() - self.speech_start_time).total_seconds()
                    result["event"] = "speech_ended"
                    result["duration"] = duration
                    self.speech_start_time = None

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
        self.audio_queue = asyncio.Queue()

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

        try:
            # Generate speech using Edge TTS
            communicate = edge_tts.Communicate(
                text,
                self.config.voice,
                rate=self.config.speech_rate,
                volume=self.config.speech_volume
            )

            # Stream audio chunks
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    if on_chunk:
                        await on_chunk(chunk["data"])
                    await self.audio_queue.put(chunk["data"])

            return True

        except Exception as e:
            logger.error("[TTS] Speech generation failed: %s", str(e))
            return False

        finally:
            self.is_speaking = False
            self.current_text = ""

    async def stop(self):
        """Stop current speech"""
        self.is_speaking = False
        # Clear the queue
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except:
                break

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

    async def generate_response(
        self,
        interviewer_question: str,
        conversation_history: list,
        context: Dict = None
    ) -> str:
        """
        Generate AI response to interviewer's question.
        """
        try:
            # Build prompt with context
            messages = [
                {"role": "system", "content": self.config.system_prompt}
            ]

            # Add conversation history
            for msg in conversation_history[-5:]:  # Keep last 5 messages for context
                messages.append(msg)

            # Add current question
            messages.append({"role": "user", "content": interviewer_question})

            # Try to use existing AI router if available
            try:
                from ai_router import route_ai
                response = await route_ai(
                    messages,
                    model_preference=self.config.ai_model,
                    temperature=self.config.temperature
                )
                return response
            except ImportError:
                logger.warning("[AI] ai_router not available, using fallback")
                return self._fallback_response(interviewer_question)

        except Exception as e:
            logger.error("[AI] Response generation failed: %s", str(e))
            return "I'm sorry, I couldn't generate a response right now."

    def _fallback_response(self, question: str) -> str:
        """Fallback response when AI router unavailable"""
        return f"I heard: '{question[:50]}...'. This is a fallback response. Please configure the AI router."


class VoiceAgent:
    """
    Main voice agent that coordinates VAD, TTS, and AI response generation.
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

        # Audio buffer for VAD
        self._audio_buffer: list = []

    @property
    def state(self) -> VoiceAgentState:
        return self._state

    def _set_state(self, new_state: VoiceAgentState):
        """Update state and notify listeners"""
        old_state = self._state
        self._state = new_state
        if self.session:
            self.session.state = new_state

        # Notify listeners
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
        logger.info(f"[VoiceAgent] Session started: {self.session.session_id}")
        return self.session

    async def end_session(self):
        """End the current session"""
        if self.tts.is_active():
            await self.tts.stop()

        if self.session:
            logger.info(f"[VoiceAgent] Session ended: {self.session.session_id}")
            self.session = None

        self._set_state(VoiceAgentState.IDLE)
        self._state_listeners.clear()

    async def process_audio(self, audio_data: bytes) -> Dict[str, Any]:
        """
        Process incoming audio chunk.
        Returns action that frontend should take.
        """
        if not self.session:
            return {"action": "error", "message": "No active session"}

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
            # Speech ended, transition to thinking
            duration = vad_result.get("duration", 0)
            if duration >= self.config.min_speech_duration:
                self._set_state(VoiceAgentState.THINKING)

                # In a real implementation, we would:
                # 1. Send audio to STT service
                # 2. Get transcript
                # 3. Generate AI response
                # For now, simulate the process

                return {
                    "action": "thinking",
                    "speech_duration": duration
                }

        return {"action": "continue_listening", "is_speaking": vad_result.get("is_speaking")}

    async def _handle_thinking(self, vad_result: Dict) -> Dict[str, Any]:
        """Handle THINKING state"""
        # Generate AI response
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


# Global voice agent instance
voice_agent = VoiceAgent()


# API Functions
async def create_session(user_id: str, config: Optional[VoiceAgentConfig] = None) -> Dict[str, Any]:
    """Create a new voice agent session"""
    agent = VoiceAgent(config)
    session = await agent.start_session(user_id)
    return {
        "session_id": session.session_id,
        "status": "created",
        "config": {
            "voice": agent.config.voice,
            "enable_interruption": agent.config.enable_interruption,
        }
    }


async def process_audio_chunk(session_id: str, audio_data: bytes) -> Dict[str, Any]:
    """Process audio chunk for a session"""
    # In production, would look up session by ID
    # For now, use global instance
    return await voice_agent.process_audio(audio_data)


async def end_session(session_id: str) -> Dict[str, Any]:
    """End a voice agent session"""
    await voice_agent.end_session()
    return {"status": "ended", "session_id": session_id}


def get_status() -> Dict[str, Any]:
    """Get voice agent status"""
    return {
        "available": HAS_EDGE_TTS and HAS_NUMPY,
        "edge_tts": HAS_EDGE_TTS,
        "numpy": HAS_NUMPY,
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
