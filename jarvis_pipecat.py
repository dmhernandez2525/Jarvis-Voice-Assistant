#!/usr/bin/env python3
"""JARVIS Voice Assistant, Pipecat full-duplex variant (Option C).

Pipeline:
    mic -> Silero VAD -> Parakeet-MLX STT -> Gemma 4 (via Ollama OpenAI-compat)
       -> Kokoro-82M TTS (via mlx_audio.server OpenAI-compat) -> speaker

Full-duplex behavior: once VAD detects the user is speaking, Pipecat
automatically cancels any in-flight TTS output, so you can barge in on
the assistant without waiting for it to finish.

Requires these services running BEFORE this script starts. The launcher
(`run-jarvis-pipecat.sh`) handles both:

    1. Ollama:          http://127.0.0.1:11434   (ollama serve)
    2. mlx-audio:       http://127.0.0.1:8000    (python -m mlx_audio.server
                                                  --host 127.0.0.1 --port 8000)

All pinned env-overridable knobs use JARVIS_* variables, same as
jarvis_gemma4_router.py.

Security posture (per 05-Pipecat-Scenario-C-Audit.md):
  - Silero VAD uses Pipecat's bundled ONNX file (confirmed by audit,
    JIT/pickle path is not reachable).
  - We use our own mlx_audio.server for TTS (NOT Pipecat's kokoro service,
    which pulls kokoro-onnx from a 4-link pseudonymous supply chain).
  - All endpoints bound to 127.0.0.1 by default.
  - Parakeet-MLX weights are safetensors-only (confirmed by audit).
"""

from __future__ import annotations

import asyncio
import io
import os
import tempfile
import wave
from typing import AsyncGenerator, Optional

import numpy as np

# Pipecat
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import ErrorFrame, Frame, TranscriptionFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContext,
    LLMContextAggregatorPair,
)
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.services.openai.tts import OpenAITTSService
from pipecat.services.stt_service import SegmentedSTTService
from pipecat.transports.local.audio import (
    LocalAudioTransport,
    LocalAudioTransportParams,
)
from pipecat.utils.time import time_now_iso8601

# Ours
from jarvis_logging import setup_logging, write_session_summary

# --- Config ----------------------------------------------------------------

STT_MODEL_ID = os.environ.get(
    "JARVIS_STT_MODEL", "mlx-community/parakeet-tdt-0.6b-v3"
)

LLM_BASE_URL = os.environ.get("JARVIS_LLM_BASE_URL", "http://127.0.0.1:11434/v1")
LLM_MODEL = os.environ.get("JARVIS_LLM_MODEL", "gemma4:26b")
LLM_TEMPERATURE = float(os.environ.get("JARVIS_LLM_TEMPERATURE", "0.7"))

TTS_BASE_URL = os.environ.get("JARVIS_TTS_BASE_URL", "http://127.0.0.1:8000/v1")
TTS_MODEL = os.environ.get("JARVIS_TTS_MODEL", "mlx-community/Kokoro-82M-bf16")
TTS_VOICE = os.environ.get("JARVIS_TTS_VOICE", "am_michael")

# Sample rates: Pipecat defaults are 16k in, 24k out for TTS.
AUDIO_IN_SR = int(os.environ.get("JARVIS_AUDIO_IN_SR", "16000"))
AUDIO_OUT_SR = int(os.environ.get("JARVIS_AUDIO_OUT_SR", "24000"))

SYSTEM_PROMPT = os.environ.get(
    "JARVIS_SYSTEM_PROMPT",
    (
        "You are JARVIS, a helpful local voice assistant running on a "
        "MacBook Pro. Be direct and conversational. Keep replies short "
        "(one or two sentences) unless the user asks for detail. When "
        "you don't know something, say so plainly rather than guessing."
    ),
)

# --- Logging ---------------------------------------------------------------

logger, events, SESSION_ID, SESSION_START = setup_logging(name="jarvis.pipecat")


# --- Parakeet-MLX STT service ---------------------------------------------

class ParakeetMLXSTTService(SegmentedSTTService):
    """SegmentedSTTService that transcribes complete speech segments
    using Parakeet-MLX.

    Receives a raw WAV-bytes payload from SegmentedSTTService after VAD
    signals end-of-speech. Writes to a temp file, runs parakeet_mlx, and
    yields a single TranscriptionFrame.
    """

    def __init__(self, *, model_id: str, sample_rate: Optional[int] = None, **kwargs):
        super().__init__(sample_rate=sample_rate, **kwargs)
        self._model_id = model_id
        self._model = None
        logger.info("ParakeetMLXSTTService configured: model=%s", model_id)

    def _load_model(self):
        if self._model is not None:
            return
        from parakeet_mlx import from_pretrained
        logger.info("Loading Parakeet-MLX weights...")
        self._model = from_pretrained(self._model_id)
        logger.info("Parakeet-MLX ready")

    async def run_stt(self, audio: bytes) -> AsyncGenerator[Frame, None]:
        # Lazy-load the model on first call so the pipeline can start fast.
        if self._model is None:
            # Parakeet load is synchronous + ~1s. Run in a thread to avoid
            # stalling the event loop.
            await asyncio.to_thread(self._load_model)

        try:
            await self.start_processing_metrics()

            # parakeet-mlx takes a file path; write the WAV bytes out.
            fd, path = tempfile.mkstemp(suffix=".wav", prefix="jarvis-stt-")
            try:
                with os.fdopen(fd, "wb") as f:
                    f.write(audio)
                result = await asyncio.to_thread(self._model.transcribe, path)
            finally:
                try:
                    os.unlink(path)
                except OSError:
                    pass

            await self.stop_processing_metrics()

            text = (result.text if hasattr(result, "text") else str(result)).strip()

            if not text:
                logger.debug("Parakeet returned empty transcription")
                events.event("stt_empty")
                return

            logger.info("Parakeet transcribed: %r", text[:120])
            events.event("stt_transcribe", text=text, text_len=len(text))

            yield TranscriptionFrame(
                text,
                getattr(self, "_user_id", "") or "",
                time_now_iso8601(),
                result=result,
            )
        except Exception as e:
            logger.error("Parakeet STT failed: %s", e, exc_info=True)
            events.event("stt_error", error=str(e), exception_type=type(e).__name__)
            yield ErrorFrame(error=f"STT failure: {e}")


# --- Main ------------------------------------------------------------------

async def main() -> None:
    logger.info("Starting Jarvis Pipecat (Option C, full-duplex local)")
    events.event(
        "pipecat_config",
        stt_model=STT_MODEL_ID,
        llm_base_url=LLM_BASE_URL,
        llm_model=LLM_MODEL,
        tts_base_url=TTS_BASE_URL,
        tts_model=TTS_MODEL,
        tts_voice=TTS_VOICE,
    )

    transport = LocalAudioTransport(
        LocalAudioTransportParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            audio_in_sample_rate=AUDIO_IN_SR,
            audio_out_sample_rate=AUDIO_OUT_SR,
            vad_analyzer=SileroVADAnalyzer(),
        )
    )

    stt = ParakeetMLXSTTService(
        model_id=STT_MODEL_ID,
        sample_rate=AUDIO_IN_SR,
    )

    llm = OpenAILLMService(
        api_key="ollama-local-unused",  # Ollama ignores the key on loopback.
        base_url=LLM_BASE_URL,
        model=LLM_MODEL,
    )

    tts = OpenAITTSService(
        api_key="mlx-audio-local-unused",
        base_url=TTS_BASE_URL,
        model=TTS_MODEL,
        voice=TTS_VOICE,
        sample_rate=AUDIO_OUT_SR,
    )

    context = LLMContext(
        messages=[{"role": "system", "content": SYSTEM_PROMPT}],
    )
    aggregators = LLMContextAggregatorPair(context)

    pipeline = Pipeline([
        transport.input(),        # mic
        stt,                      # Parakeet segmented STT
        aggregators.user,         # records user turn into context
        llm,                      # Gemma 4 26B via Ollama
        tts,                      # Kokoro via mlx_audio.server
        transport.output(),       # speaker
        aggregators.assistant,    # records assistant turn into context
    ])

    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            enable_metrics=True,
            audio_in_sample_rate=AUDIO_IN_SR,
            audio_out_sample_rate=AUDIO_OUT_SR,
        ),
        conversation_id=SESSION_ID,
    )

    logger.info("Pipeline built. Speak into the mic whenever you're ready.")
    logger.info("Ctrl+C to exit.")
    events.event("pipecat_started")

    runner = PipelineRunner()
    try:
        await runner.run(task)
    finally:
        events.event("pipecat_stopped")
        try:
            summary_path = write_session_summary(
                session_id=SESSION_ID,
                start_time=SESSION_START,
                stats={"mode": "pipecat_local"},
                extra={
                    "config": {
                        "stt_model": STT_MODEL_ID,
                        "llm_model": LLM_MODEL,
                        "tts_model": TTS_MODEL,
                        "tts_voice": TTS_VOICE,
                    },
                },
            )
            logger.info("Session summary written: %s", summary_path)
        except Exception as e:
            logger.error("Failed to write session summary: %s", e, exc_info=True)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down Jarvis Pipecat (Ctrl+C)")
        events.event("shutdown", reason="keyboard_interrupt")
