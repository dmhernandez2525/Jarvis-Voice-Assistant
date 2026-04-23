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

import logging
import os
import tempfile
import time
from pathlib import Path

import numpy as np
import ollama
import sounddevice as sd
from scipy.io import wavfile

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("jarvis.gemma4")

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
TTS_VOICE = os.environ.get("JARVIS_TTS_VOICE", "af_heart")

# Audio settings (match jarvis_smart_router.py so wake-word tuning carries over)
SAMPLE_RATE = 16000
WAKE_THRESHOLD = 0.03
WAKE_DURATION_S = 1.5
COMMAND_DURATION_S = 15


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
            return ""
        text = result.text.strip() if hasattr(result, "text") else str(result).strip()
        logger.info(
            "Parakeet transcribe: %dms, %d chars",
            int((time.time() - start) * 1000),
            len(text),
        )
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
        logger.info("Listening for wake word")
        try:
            while True:
                audio = sd.rec(
                    int(WAKE_DURATION_S * SAMPLE_RATE),
                    samplerate=SAMPLE_RATE,
                    channels=1,
                    dtype=np.float32,
                )
                sd.wait()

                if np.abs(audio).mean() <= WAKE_THRESHOLD:
                    time.sleep(0.1)
                    continue

                logger.info("Sound detected, verifying wake word")
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
                    return True
                else:
                    logger.info("False alarm, heard: %r", text)

                time.sleep(0.1)
        except KeyboardInterrupt:
            return False

    # ----- Command capture -----

    def listen_command(self, duration: float = COMMAND_DURATION_S) -> np.ndarray:
        """Record the user's command from the default input device."""
        logger.info("Recording command (%ds)", duration)
        start = time.time()
        recording = sd.rec(
            int(duration * SAMPLE_RATE),
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype=np.float32,
        )
        sd.wait()
        logger.info("Recording done in %dms", int((time.time() - start) * 1000))
        return recording.flatten()

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
        """Classify complexity. Returns (tier_name, ollama_model_tag)."""
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
                options={"temperature": 0.3},
            )
        except Exception as e:
            logger.error("Router LLM call failed: %s", e, exc_info=True)
            # Fail open to balanced, not powerful: don't burn 31B on an error.
            return "balanced", BALANCED_MODEL

        classification = response["response"].strip().upper()

        if "SIMPLE" in classification or "FAST" in classification:
            tier, model, eta = "fast", FAST_MODEL, "~1-2s"
        elif "MODERATE" in classification or "BALANCED" in classification:
            tier, model, eta = "balanced", BALANCED_MODEL, "~3-5s"
        else:
            tier, model, eta = "powerful", POWERFUL_MODEL, "~15-30s"

        logger.info(
            "Routing: %dms, class=%s -> tier=%s model=%s eta=%s",
            int((time.time() - start) * 1000),
            classification[:30],
            tier,
            model,
            eta,
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
                options={"temperature": 0.8, "top_p": 0.9},
            )
        except Exception as e:
            logger.error("LLM call failed: %s", e, exc_info=True)
            return "My apologies, sir. I encountered an error generating a response."

        answer = response["response"].strip()
        llm_ms = int((time.time() - start) * 1000)

        # Track time saved vs. always using the 31B tier (assume ~20s baseline).
        if tier in {"fast", "balanced"}:
            saved = max(0, 20000 - llm_ms)
            self.stats["total_time_saved_ms"] += saved

        logger.info("LLM inference: %dms", llm_ms)
        logger.info("JARVIS: %s", answer[:120] + ("..." if len(answer) > 120 else ""))
        return answer

    # ----- TTS -----

    def speak(self, text: str) -> None:
        """Kokoro-82M -> WAV -> afplay via sounddevice."""
        logger.info("Speaking response (%d chars)", len(text))
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
                lang_code="a",
                join_audio=True,
                verbose=False,
            )
        except Exception as e:
            logger.error("Kokoro TTS failed: %s", e, exc_info=True)
            return

        # Kokoro emits `{prefix}_000.wav` and optionally more chunks; play them in order.
        wav_files = sorted(Path(tmp_dir).glob("utterance*.wav"))
        if not wav_files:
            logger.error("Kokoro produced no WAV output in %s", tmp_dir)
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

        logger.info("TTS total: %dms", int((time.time() - start) * 1000))

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
                    continue

                response = self.get_smart_response(text)
                self.speak(response)

                logger.info(
                    "TOTAL round-trip: %dms",
                    int((time.time() - total_start) * 1000),
                )
        except KeyboardInterrupt:
            logger.info("Shutting down Gemma 4 JARVIS")
            self.print_stats()


if __name__ == "__main__":
    Gemma4Jarvis().run()
