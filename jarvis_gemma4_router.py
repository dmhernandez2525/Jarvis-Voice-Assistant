#!/usr/bin/env python3
"""JARVIS Voice Assistant, Gemma 4 Router variant.

Drop-in replacement for jarvis_smart_router.py that swaps the local AI stack:
  STT   Whisper Large       ->  Parakeet-MLX 0.6B v3       (~40x realtime)
  TTS   Coqui tacotron2-DDC ->  Kokoro-82M via mlx-audio   (~15x realtime)
  LLM   Qwen 2.5 family     ->  Gemma 4 family via Ollama

The routing architecture is preserved (router tier classifies, then one of
three tiers handles the reply). Models are Gemma 4 E2B (router + fast),
Gemma 4 26B A4B MoE (balanced daily driver), Gemma 4 31B dense (powerful).

Runs out of the hardened venv at ~/venvs/local-ai (Python 3.12 with audit-
pinned torch/transformers/pillow/mlx; Ollama on the primary account at
127.0.0.1:11434).
"""

import os
import tempfile
import time
from pathlib import Path

import numpy as np
import ollama
import sounddevice as sd
from scipy.io import wavfile

from jarvis_logging import setup_logging, write_session_summary

# Configure logging, crash capture, faulthandler, and the structured event log.
# Logs land in ~/Library/Logs/Jarvis-Gemma4/
logger, events, SESSION_ID, SESSION_START = setup_logging(name="jarvis.gemma4")

# Model configuration. Gemma 4 via Ollama (pulled 2026-04-23).
ROUTER_MODEL = os.environ.get("JARVIS_ROUTER_MODEL", "gemma4:e2b")
FAST_MODEL = os.environ.get("JARVIS_FAST_MODEL", "gemma4:e4b")
BALANCED_MODEL = os.environ.get("JARVIS_BALANCED_MODEL", "gemma4:26b")
POWERFUL_MODEL = os.environ.get("JARVIS_POWERFUL_MODEL", "gemma4:31b")

STT_MODEL_ID = os.environ.get(
    "JARVIS_STT_MODEL", "mlx-community/parakeet-tdt-0.6b-v3"
)
TTS_MODEL_ID = os.environ.get(
    "JARVIS_TTS_MODEL", "mlx-community/Kokoro-82M-bf16"
)
TTS_VOICE = os.environ.get("JARVIS_TTS_VOICE", "am_michael")
TTS_LANG_CODE = os.environ.get("JARVIS_TTS_LANG_CODE", "a")

# Routing mode: "direct" (default, always use balanced 26B) or "routed"
# (classify first, then pick tier). Direct is ~5s faster per query because
# it skips the e2b router cold-load cost.
ROUTING_MODE = os.environ.get("JARVIS_MODE", "direct").lower()

# Ollama keep_alive: how long to keep a model resident after a call. Longer
# = faster next query but more memory held. 15m is a safe default on 96GB.
OLLAMA_KEEP_ALIVE = os.environ.get("JARVIS_OLLAMA_KEEP_ALIVE", "15m")

# Audio settings. All thresholds env-overridable.
SAMPLE_RATE = 16000
# Threshold lowered from 0.03 to 0.010 after real-world measurement showed
# normal speech at mean ~0.015. 0.010 gives comfortable margin vs silence.
WAKE_THRESHOLD = float(os.environ.get("JARVIS_WAKE_THRESHOLD", "0.010"))
WAKE_DURATION_S = float(os.environ.get("JARVIS_WAKE_DURATION_S", "1.5"))

# Command capture: silence-based end-of-speech detection.
# Stops recording when COMMAND_SILENCE_S seconds of silence are heard after
# at least one speech chunk, OR after COMMAND_MAX_S seconds total.
COMMAND_MAX_S = float(os.environ.get("JARVIS_COMMAND_MAX_S", "10"))
COMMAND_SILENCE_S = float(os.environ.get("JARVIS_COMMAND_SILENCE_S", "1.2"))
COMMAND_CHUNK_S = float(os.environ.get("JARVIS_COMMAND_CHUNK_S", "0.2"))

# Heartbeat cadence while waiting for wake word.
WAKE_HEARTBEAT_EVERY = int(os.environ.get("JARVIS_WAKE_HEARTBEAT_EVERY", "4"))


class Gemma4Jarvis:
    """Voice assistant with Gemma 4 + Parakeet-MLX + Kokoro-82M."""

    def __init__(self) -> None:
        logger.info("Initializing Gemma 4 JARVIS")

        # STT
        logger.info("Loading Parakeet-MLX: %s", STT_MODEL_ID)
        start = time.time()
        from parakeet_mlx import from_pretrained
        self.stt = from_pretrained(STT_MODEL_ID)
        logger.info("  Parakeet loaded in %dms", int((time.time() - start) * 1000))

        # TTS (imported lazily, generate_audio writes a file)
        logger.info("TTS backend: %s (voice: %s)", TTS_MODEL_ID, TTS_VOICE)
        from mlx_audio.tts.generate import generate_audio
        self._generate_audio = generate_audio

        # LLM configuration (no preload; ollama keeps models warm on its end)
        logger.info(
            "LLM routing: router=%s fast=%s balanced=%s powerful=%s",
            ROUTER_MODEL, FAST_MODEL, BALANCED_MODEL, POWERFUL_MODEL,
        )

        self.stats = {
            "fast_count": 0,
            "balanced_count": 0,
            "powerful_count": 0,
            "total_time_saved_ms": 0,
        }

        logger.info("Gemma 4 JARVIS ready")

    # ----- STT -----

    def transcribe_wav(self, wav_path: str) -> str:
        """Parakeet-MLX transcribe from a WAV file path."""
        start = time.time()
        try:
            result = self.stt.transcribe(wav_path)
        except Exception as e:
            logger.error("Parakeet transcription failed: %s", e, exc_info=True)
            events.event("stt_error", wav=wav_path, error=str(e), exception_type=type(e).__name__)
            return ""
        text = result.text.strip() if hasattr(result, "text") else str(result).strip()
        duration_ms = int((time.time() - start) * 1000)
        logger.info("Parakeet transcribe: %dms, %d chars", duration_ms, len(text))
        events.event("stt_transcribe", duration_ms=duration_ms, text_len=len(text), text=text)
        return text

    def _audio_to_temp_wav(self, audio: np.ndarray) -> str:
        """Write float32 mono audio to a temp WAV and return the path."""
        fd, path = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        wavfile.write(path, SAMPLE_RATE, (audio * 32767).astype(np.int16))
        return path

    # ----- Wake word -----

    def listen_for_wakeword(self) -> bool:
        """Energy-threshold wake detection, Parakeet verification for 'jarvis'."""
        logger.info(
            "Listening for wake word (threshold=%.4f, window=%.1fs)",
            WAKE_THRESHOLD, WAKE_DURATION_S,
        )
        cycle = 0
        try:
            while True:
                cycle += 1
                audio = sd.rec(
                    int(WAKE_DURATION_S * SAMPLE_RATE),
                    samplerate=SAMPLE_RATE,
                    channels=1,
                    dtype=np.float32,
                )
                sd.wait()

                mean_abs = float(np.abs(audio).mean())

                # Heartbeat: emit current audio level periodically so we can
                # tell silence (mic permission missing) from "below threshold".
                if cycle % WAKE_HEARTBEAT_EVERY == 0:
                    peak = float(np.abs(audio).max())
                    logger.info(
                        "Mic heartbeat: mean=%.4f peak=%.4f threshold=%.4f cycle=%d",
                        mean_abs, peak, WAKE_THRESHOLD, cycle,
                    )
                    events.event(
                        "wake_heartbeat",
                        mean_abs=mean_abs,
                        peak_abs=peak,
                        threshold=WAKE_THRESHOLD,
                        cycle=cycle,
                    )

                if mean_abs <= WAKE_THRESHOLD:
                    time.sleep(0.1)
                    continue

                logger.info("Sound detected (mean=%.4f), verifying wake word", mean_abs)
                wav_path = self._audio_to_temp_wav(audio.flatten())
                try:
                    text = self.transcribe_wav(wav_path).lower()
                finally:
                    try:
                        os.unlink(wav_path)
                    except OSError as e:
                        logger.warning("Could not remove temp wav %s: %s", wav_path, e)

                if "jarvis" in text:
                    logger.info("Wake word detected")
                    events.event("wake_detected", text=text)
                    return True
                else:
                    logger.info("False alarm, heard: %r", text)
                    events.event("wake_false_alarm", text=text)

                time.sleep(0.1)
        except KeyboardInterrupt:
            events.event("wake_loop_interrupted")
            return False

    # ----- Command capture -----

    def listen_command(self) -> np.ndarray:
        """Record the user's command, stopping at end-of-speech.

        Records in COMMAND_CHUNK_S windows. After at least one chunk above
        WAKE_THRESHOLD (speech), stop once COMMAND_SILENCE_S of silence is
        observed. Hard cap at COMMAND_MAX_S to bound runaway recording.
        """
        logger.info(
            "Recording command (max=%.1fs, silence-end after %.1fs)",
            COMMAND_MAX_S, COMMAND_SILENCE_S,
        )
        start = time.time()

        chunk_samples = int(COMMAND_CHUNK_S * SAMPLE_RATE)
        silence_chunks_needed = max(1, int(COMMAND_SILENCE_S / COMMAND_CHUNK_S))
        max_chunks = int(COMMAND_MAX_S / COMMAND_CHUNK_S)

        buffers: list[np.ndarray] = []
        silence_count = 0
        heard_speech = False
        stopped_reason = "max_duration"

        try:
            stream = sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype=np.float32,
                blocksize=chunk_samples,
            )
            stream.start()
        except Exception as e:
            logger.error("Could not open input stream: %s", e, exc_info=True)
            events.event("command_stream_error", error=str(e))
            return np.zeros(0, dtype=np.float32)

        try:
            for i in range(max_chunks):
                data, _overflow = stream.read(chunk_samples)
                chunk = data[:, 0].copy()
                buffers.append(chunk)
                mean_abs = float(np.abs(chunk).mean())

                if mean_abs > WAKE_THRESHOLD:
                    heard_speech = True
                    silence_count = 0
                elif heard_speech:
                    silence_count += 1
                    if silence_count >= silence_chunks_needed:
                        stopped_reason = "silence_end"
                        break
        finally:
            try:
                stream.stop()
                stream.close()
            except Exception as e:
                logger.warning("Error closing input stream: %s", e)

        audio = np.concatenate(buffers) if buffers else np.zeros(0, dtype=np.float32)
        elapsed_ms = int((time.time() - start) * 1000)
        logger.info(
            "Recording done: %dms, %.1fs audio, reason=%s, speech=%s",
            elapsed_ms, len(audio) / SAMPLE_RATE, stopped_reason, heard_speech,
        )
        events.event(
            "command_recorded",
            duration_ms=elapsed_ms,
            audio_seconds=len(audio) / SAMPLE_RATE,
            stopped_reason=stopped_reason,
            heard_speech=heard_speech,
        )
        return audio

    def transcribe_command(self, audio: np.ndarray) -> str:
        """Transcribe the recorded command array."""
        wav_path = self._audio_to_temp_wav(audio)
        try:
            text = self.transcribe_wav(wav_path)
        finally:
            try:
                os.unlink(wav_path)
            except OSError as e:
                logger.warning("Could not remove temp wav %s: %s", wav_path, e)
        logger.info("User said: %r", text)
        return text

    # ----- LLM -----

    def analyze_query_complexity(self, text: str) -> tuple[str, str]:
        """Classify complexity. Returns (tier_name, ollama_model_tag).

        In direct mode (default), skip the classifier and go straight to the
        balanced model. In routed mode, do the old e2b-based classification.
        """
        if ROUTING_MODE == "direct":
            events.event("router_skipped", mode="direct", model=BALANCED_MODEL)
            return "balanced", BALANCED_MODEL

        logger.info("Classifying query complexity")
        start = time.time()

        analysis_prompt = (
            "Classify this query's complexity. Respond with ONLY ONE WORD.\n\n"
            "SIMPLE: basic facts, greetings, jokes, casual chat.\n"
            "MODERATE: explanations, comparisons, creative writing, code generation.\n"
            "COMPLEX: deep analysis, multi-step reasoning, complex technical tasks.\n\n"
            f'Query: "{text}"\n\nClassification:'
        )

        try:
            response = ollama.generate(
                model=ROUTER_MODEL,
                prompt=analysis_prompt,
                stream=False,
                keep_alive=OLLAMA_KEEP_ALIVE,
                options={"temperature": 0.3},
            )
        except Exception as e:
            logger.error("Router LLM call failed: %s", e, exc_info=True)
            events.event("router_error", error=str(e), exception_type=type(e).__name__)
            # Fail open to balanced, not powerful: don't burn 31B on an error.
            return "balanced", BALANCED_MODEL

        classification = response["response"].strip().upper()

        if "SIMPLE" in classification or "FAST" in classification:
            tier, model, eta = "fast", FAST_MODEL, "~1-2s"
        elif "MODERATE" in classification or "BALANCED" in classification:
            tier, model, eta = "balanced", BALANCED_MODEL, "~3-5s"
        else:
            tier, model, eta = "powerful", POWERFUL_MODEL, "~15-30s"

        duration_ms = int((time.time() - start) * 1000)
        logger.info(
            "Routing: %dms, class=%s -> tier=%s model=%s eta=%s",
            duration_ms, classification[:30], tier, model, eta,
        )
        events.event(
            "router_decision",
            duration_ms=duration_ms,
            classification=classification[:30],
            tier=tier,
            model=model,
            query_len=len(text),
        )
        return tier, model

    def get_smart_response(self, text: str) -> str:
        """Route and generate."""
        tier, model = self.analyze_query_complexity(text)
        self.stats[f"{tier}_count"] += 1

        logger.info("Generating response (tier=%s)", tier)
        start = time.time()

        prompt = (
            "You are JARVIS, a helpful AI assistant. Be direct and conversational.\n\n"
            f"User: {text}\nJARVIS:"
        )
        try:
            response = ollama.generate(
                model=model,
                prompt=prompt,
                stream=False,
                keep_alive=OLLAMA_KEEP_ALIVE,
                options={"temperature": 0.8, "top_p": 0.9},
            )
        except Exception as e:
            logger.error("LLM call failed: %s", e, exc_info=True)
            events.event("llm_error", tier=tier, model=model, error=str(e), exception_type=type(e).__name__)
            return "My apologies, sir. I encountered an error generating a response."

        answer = response["response"].strip()
        llm_ms = int((time.time() - start) * 1000)

        # Track time saved vs. always using the 31B tier (assume ~20s baseline).
        if tier in {"fast", "balanced"}:
            saved = max(0, 20000 - llm_ms)
            self.stats["total_time_saved_ms"] += saved

        logger.info("LLM inference: %dms", llm_ms)
        logger.info("JARVIS: %s", answer[:120] + ("..." if len(answer) > 120 else ""))
        events.event(
            "llm_response",
            tier=tier,
            model=model,
            duration_ms=llm_ms,
            input_len=len(text),
            output_len=len(answer),
            output_preview=answer[:200],
        )
        return answer

    # ----- TTS -----

    def speak(self, text: str) -> None:
        """Kokoro-82M -> WAV -> afplay via sounddevice."""
        logger.info("Speaking response (%d chars)", len(text))
        events.event("tts_start", text_len=len(text))
        start = time.time()

        tmp_dir = tempfile.mkdtemp(prefix="jarvis-tts-")
        prefix = os.path.join(tmp_dir, "utterance")
        try:
            self._generate_audio(
                text=text,
                model=TTS_MODEL_ID,
                voice=TTS_VOICE,
                file_prefix=prefix,
                audio_format="wav",
                lang_code=TTS_LANG_CODE,
                join_audio=True,
                verbose=False,
            )
        except Exception as e:
            logger.error("Kokoro TTS failed: %s", e, exc_info=True)
            events.event("tts_error", error=str(e), exception_type=type(e).__name__)
            return

        # Kokoro emits `{prefix}_000.wav` and optionally more chunks; play them in order.
        wav_files = sorted(Path(tmp_dir).glob("utterance*.wav"))
        if not wav_files:
            logger.error("Kokoro produced no WAV output in %s", tmp_dir)
            events.event("tts_no_output", tmp_dir=tmp_dir)
            return

        for wav in wav_files:
            try:
                sr, data = wavfile.read(str(wav))
                sd.play(data, sr)
                sd.wait()
            except Exception as e:
                logger.error("Playback of %s failed: %s", wav, e, exc_info=True)
            finally:
                try:
                    wav.unlink()
                except OSError as e:
                    logger.warning("Could not remove %s: %s", wav, e)

        try:
            os.rmdir(tmp_dir)
        except OSError:
            pass

        tts_ms = int((time.time() - start) * 1000)
        logger.info("TTS total: %dms", tts_ms)
        events.event(
            "tts_complete",
            duration_ms=tts_ms,
            text_len=len(text),
            chunk_count=len(wav_files),
        )

    # ----- Stats + loop -----

    def print_stats(self) -> None:
        total = sum(self.stats[k] for k in ("fast_count", "balanced_count", "powerful_count"))
        if total == 0:
            return
        logger.info("ROUTING STATS: fast=%d balanced=%d powerful=%d total=%d",
                    self.stats["fast_count"],
                    self.stats["balanced_count"],
                    self.stats["powerful_count"],
                    total)
        logger.info("Approx time saved vs always-31B: %.1fs",
                    self.stats["total_time_saved_ms"] / 1000)

    def run(self) -> None:
        try:
            while True:
                total_start = time.time()

                if not self.listen_for_wakeword():
                    break

                audio = self.listen_command()
                text = self.transcribe_command(audio)

                if not text:
                    self.speak("I didn't catch that, sir.")
                    events.event("empty_transcription")
                    continue

                response = self.get_smart_response(text)
                self.speak(response)

                roundtrip_ms = int((time.time() - total_start) * 1000)
                logger.info("TOTAL round-trip: %dms", roundtrip_ms)
                events.event("roundtrip_complete", duration_ms=roundtrip_ms)
        except KeyboardInterrupt:
            logger.info("Shutting down Gemma 4 JARVIS (Ctrl+C)")
            events.event("shutdown", reason="keyboard_interrupt")
            self.print_stats()
        finally:
            try:
                summary_path = write_session_summary(
                    session_id=SESSION_ID,
                    start_time=SESSION_START,
                    stats=self.stats,
                    extra={
                        "models": {
                            "router": ROUTER_MODEL,
                            "fast": FAST_MODEL,
                            "balanced": BALANCED_MODEL,
                            "powerful": POWERFUL_MODEL,
                            "stt": STT_MODEL_ID,
                            "tts": TTS_MODEL_ID,
                            "voice": TTS_VOICE,
                        },
                    },
                )
                logger.info("Session summary written: %s", summary_path)
            except Exception as e:
                logger.error("Failed to write session summary: %s", e, exc_info=True)


if __name__ == "__main__":
    Gemma4Jarvis().run()
