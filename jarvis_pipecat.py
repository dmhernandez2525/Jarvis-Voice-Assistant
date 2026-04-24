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
import time
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
# gemma4:e4b has ~300ms time-to-first-token vs gemma4:26b's ~1s+ because its
# weights are 9.6GB vs 17GB. For conversational voice UX the perceived speed
# dominates the modest quality gap. Override via JARVIS_LLM_MODEL=gemma4:26b
# for harder reasoning questions.
LLM_MODEL = os.environ.get("JARVIS_LLM_MODEL", "gemma4:e4b")
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
        "You are JARVIS, a local voice assistant running on a MacBook Pro. "
        "Always reply in ONE or TWO short sentences. No lists, no headers, "
        "no preamble like 'Sure!' or 'Of course'. Speak like a person, "
        "not a chatbot. If you don't know something, say so plainly in "
        "one sentence rather than guessing."
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

    If `preloaded_model` is supplied, that model is used directly (for
    warm-start). Otherwise the model is lazy-loaded on first transcription.
    """

    def __init__(
        self,
        *,
        model_id: str,
        preloaded_model: Optional[object] = None,
        sample_rate: Optional[int] = None,
        **kwargs,
    ):
        super().__init__(sample_rate=sample_rate, **kwargs)
        self._model_id = model_id
        self._model = preloaded_model
        if preloaded_model is not None:
            logger.info(
                "ParakeetMLXSTTService configured with preloaded model: %s",
                model_id,
            )
        else:
            logger.info(
                "ParakeetMLXSTTService configured (lazy load): %s", model_id
            )

    def _load_model(self):
        if self._model is not None:
            return
        from parakeet_mlx import from_pretrained
        logger.info("Loading Parakeet-MLX weights...")
        self._model = from_pretrained(self._model_id)
        logger.info("Parakeet-MLX ready")

    async def run_stt(self, audio: bytes) -> AsyncGenerator[Frame, None]:
        # Lazy-load only if warm-start didn't happen.
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


# --- Warm-start ------------------------------------------------------------

WARMUP_ENABLED = os.environ.get("JARVIS_WARMUP", "1") not in ("0", "false", "False")


def _warm_parakeet():
    """Load Parakeet-MLX weights into memory. Returns the loaded model."""
    from parakeet_mlx import from_pretrained
    logger.info("Warm-up: loading Parakeet-MLX (%s)...", STT_MODEL_ID)
    t0 = time.time()
    model = from_pretrained(STT_MODEL_ID)
    ms = int((time.time() - t0) * 1000)
    logger.info("Warm-up: Parakeet loaded in %dms", ms)
    events.event("warmup_stt", duration_ms=ms)
    return model


def _warm_ollama():
    """Send a tiny generate call so Ollama loads the LLM into Metal."""
    import ollama
    logger.info("Warm-up: pre-warming Ollama %s (keep_alive=15m)...", LLM_MODEL)
    t0 = time.time()
    try:
        ollama.generate(
            model=LLM_MODEL,
            prompt="Hello.",
            stream=False,
            keep_alive="15m",
            options={"num_predict": 1, "temperature": 0.1},
        )
    except Exception as e:
        logger.error("Warm-up: Ollama call failed: %s", e, exc_info=True)
        events.event("warmup_llm_error", error=str(e))
        return
    ms = int((time.time() - t0) * 1000)
    logger.info("Warm-up: Ollama %s resident in %dms", LLM_MODEL, ms)
    events.event("warmup_llm", duration_ms=ms, model=LLM_MODEL)


def _warm_kokoro():
    """Generate one tiny Kokoro clip so the voice file is cached and the
    mlx-audio server has loaded weights into Metal.

    Note: we call the mlx-audio Python API directly rather than hitting the
    running server, because the server warmup happens on its first request.
    Using the Python API gets BOTH paths warm in one go.
    """
    from mlx_audio.tts.generate import generate_audio
    logger.info("Warm-up: generating a throwaway Kokoro clip (voice=%s)...", TTS_VOICE)
    t0 = time.time()
    tmp_dir = tempfile.mkdtemp(prefix="jarvis-warmup-")
    prefix = os.path.join(tmp_dir, "warmup")
    try:
        generate_audio(
            text="Ready.",
            model=TTS_MODEL,
            voice=TTS_VOICE,
            file_prefix=prefix,
            audio_format="wav",
            lang_code="a",
            join_audio=True,
            verbose=False,
        )
    except Exception as e:
        logger.error("Warm-up: Kokoro generate failed: %s", e, exc_info=True)
        events.event("warmup_tts_error", error=str(e))
        return
    finally:
        # Clean up any produced files.
        try:
            for name in os.listdir(tmp_dir):
                try:
                    os.unlink(os.path.join(tmp_dir, name))
                except OSError:
                    pass
            os.rmdir(tmp_dir)
        except OSError:
            pass
    ms = int((time.time() - t0) * 1000)
    logger.info("Warm-up: Kokoro ready in %dms", ms)
    events.event("warmup_tts", duration_ms=ms, voice=TTS_VOICE)


async def warm_start() -> object:
    """Pre-load all three stages in parallel-on-threads so user's first
    utterance doesn't eat a 15-20s cold-load penalty.

    Returns the preloaded Parakeet model (or None if warmup disabled).
    """
    if not WARMUP_ENABLED:
        logger.info("Warm-up disabled (JARVIS_WARMUP=0). First query will be slow.")
        return None

    logger.info("Warm-up: starting (all three stages in parallel)")
    events.event("warmup_start")
    t0 = time.time()

    # Run all three warmups concurrently on threads to minimize wall time.
    results = await asyncio.gather(
        asyncio.to_thread(_warm_parakeet),
        asyncio.to_thread(_warm_ollama),
        asyncio.to_thread(_warm_kokoro),
        return_exceptions=True,
    )

    parakeet_result = results[0]
    for i, r in enumerate(results):
        if isinstance(r, Exception):
            name = ("parakeet", "ollama", "kokoro")[i]
            logger.error("Warm-up: %s raised %s: %s", name, type(r).__name__, r)

    total_ms = int((time.time() - t0) * 1000)
    logger.info("Warm-up: all stages ready in %dms (wall)", total_ms)
    events.event("warmup_complete", duration_ms=total_ms)

    return parakeet_result if not isinstance(parakeet_result, Exception) else None


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
        warmup_enabled=WARMUP_ENABLED,
    )

    preloaded_parakeet = await warm_start()

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
        preloaded_model=preloaded_parakeet,
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
