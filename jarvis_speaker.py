"""Speaker verification for Jarvis: WeSpeaker ResNet34-LM ONNX + FrameProcessor.

Pipeline insertion point (in jarvis_pipecat.py):

    transport.input() -> [probe] -> [gate] -> vad_processor -> audio_buffer ->
    stt -> speech_rate -> verifier -> aggregators.user() -> llm -> tts ->
    transport.output() -> aggregators.assistant()

The verifier drops only TranscriptionFrame when the just-spoken audio does not
match Daniel's enrolled centroid. Every other frame, including
UserStartedSpeakingFrame and UserStoppedSpeakingFrame, passes through
unchanged so the LLMUserAggregator turn state machine does not stall.

Audio capture is done by Pipecat's first-class AudioBufferProcessor upstream
of STT. Wire it up in the launcher with:

    audio_buffer.add_event_handler(
        "on_user_turn_audio_data", verifier.on_user_turn_audio,
    )

Source recommendation: ~/Desktop/command-center/research/local-ai-stack/12-Speaker-ID-Audit.md
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np

from pipecat.frames.frames import Frame, TranscriptionFrame
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

logger = logging.getLogger("jarvis.gemma4.speaker")


# --- Config ---------------------------------------------------------------

# hbredin's first-party Apache-2.0 ONNX redistribution of WeSpeaker ResNet34-LM.
# The HF revision SHA is intentionally NOT hardcoded: pin it via the
# JARVIS_SPEAKER_REVISION env var after the first download. A bare "main"
# default is allowed only because keys.set_password() guards production use.
DEFAULT_HF_REPO = "hbredin/wespeaker-voxceleb-resnet34-LM"
DEFAULT_HF_FILE = "speaker-embedding.onnx"
DEFAULT_REVISION_ENV = "JARVIS_SPEAKER_REVISION"

# Where the ONNX file is cached on disk (gitignored via state/).
DEFAULT_MODEL_DIR = Path(
    os.environ.get(
        "JARVIS_SPEAKER_MODEL_DIR",
        Path(__file__).resolve().parent / "state" / "models" / "wespeaker-resnet34-lm",
    )
)

# Keychain identifiers for the enrolled centroid.
KEYRING_SERVICE = os.environ.get("JARVIS_SPEAKER_KEYRING_SERVICE", "jarvis")
KEYRING_USER = os.environ.get("JARVIS_SPEAKER_KEYRING_USER", "daniel-centroid-v1")

# Where non-secret enrollment metadata lives (gitignored).
DEFAULT_META_PATH = Path(
    os.environ.get(
        "JARVIS_SPEAKER_META_PATH",
        Path(__file__).resolve().parent / "state" / "enrollment_meta.json",
    )
)

# Cosine-similarity threshold default for ResNet34-LM on L2-normalized
# embeddings. Per audit Section 6 this is a defensible starting point but
# MUST be replaced with a per-user calibrated value from the threshold-tuning
# checklist before production use.
DEFAULT_THRESHOLD = float(os.environ.get("JARVIS_SPEAKER_THRESHOLD", "0.55"))

# WeSpeaker family expects 16 kHz mono PCM.
EXPECTED_SAMPLE_RATE = 16000


# --- Embedding ------------------------------------------------------------

class WeSpeakerEmbedder:
    """Run WeSpeaker ResNet34-LM in onnxruntime and return a 192-dim embedding.

    Loads the ONNX session once and reuses it for every call. CoreML EP is
    preferred (Neural Engine + GPU on M2 Max); falls back to CPU if CoreML
    refuses the graph at first inference.
    """

    def __init__(self, onnx_path: str | os.PathLike):
        import onnxruntime as ort

        path = Path(onnx_path)
        if not path.is_file():
            raise FileNotFoundError(
                f"WeSpeaker ONNX missing at {path}. "
                f"Run `python jarvis_enroll.py download` first."
            )

        # CoreML first, CPU fallback. onnxruntime silently demotes per-node
        # ops it cannot offload, so listing both providers is the safe pattern.
        providers = ["CoreMLExecutionProvider", "CPUExecutionProvider"]
        self.sess = ort.InferenceSession(str(path), providers=providers)
        active = self.sess.get_providers()
        logger.info(
            "WeSpeakerEmbedder loaded: path=%s providers=%s",
            path, active,
        )
        if "CoreMLExecutionProvider" not in active:
            logger.warning(
                "CoreML EP not active; expect 2-3x slower inference on CPU"
            )

        inputs = self.sess.get_inputs()
        if not inputs:
            raise RuntimeError("ONNX session reports zero inputs")
        self.input_name = inputs[0].name
        self.onnx_path = path

    def __call__(self, pcm_bytes: bytes, sample_rate: int) -> np.ndarray:
        """Embed a single utterance.

        Args:
            pcm_bytes: int16 mono PCM.
            sample_rate: must equal EXPECTED_SAMPLE_RATE (16000).

        Returns:
            L2-normalized float32 vector (typically 192-dim).
        """
        if sample_rate != EXPECTED_SAMPLE_RATE:
            raise ValueError(
                f"WeSpeaker expects {EXPECTED_SAMPLE_RATE} Hz, got {sample_rate}"
            )
        if not pcm_bytes:
            raise ValueError("empty PCM buffer")

        x = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        x = x.reshape(1, -1)
        emb = self.sess.run(None, {self.input_name: x})[0].squeeze()
        norm = float(np.linalg.norm(emb))
        if norm < 1e-9:
            raise RuntimeError("embedding norm is zero; ONNX model misconfigured?")
        return (emb / norm).astype(np.float32)


# --- Centroid storage -----------------------------------------------------

def save_centroid(centroid: np.ndarray, *, meta: dict, meta_path: Path = DEFAULT_META_PATH) -> None:
    """Persist the enrolled centroid in macOS Keychain plus non-secret metadata.

    The centroid itself goes through `keyring`; metadata (model SHA, sample
    rate, enrollment date, etc.) goes to a gitignored JSON file so future
    sessions can verify consistency without unlocking Keychain.
    """
    import keyring

    if centroid.dtype != np.float32:
        centroid = centroid.astype(np.float32)
    if centroid.ndim != 1:
        raise ValueError(f"centroid must be 1-D, got shape {centroid.shape}")

    blob = base64.b64encode(centroid.tobytes()).decode("ascii")
    keyring.set_password(KEYRING_SERVICE, KEYRING_USER, blob)
    logger.info(
        "Centroid stored in keychain: service=%s user=%s dim=%d",
        KEYRING_SERVICE, KEYRING_USER, centroid.shape[0],
    )

    meta_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "embedding_dim": int(centroid.shape[0]),
        "centroid_sha256": hashlib.sha256(centroid.tobytes()).hexdigest(),
        "keyring_service": KEYRING_SERVICE,
        "keyring_user": KEYRING_USER,
        "saved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        **meta,
    }
    meta_path.write_text(json.dumps(payload, indent=2))
    logger.info("Enrollment metadata written: %s", meta_path)


def load_centroid() -> np.ndarray:
    """Fetch the enrolled centroid from macOS Keychain.

    Returns an L2-normalized float32 vector. Raises RuntimeError if no
    centroid has been enrolled yet (run `python jarvis_enroll.py enroll`).
    """
    import keyring

    blob = keyring.get_password(KEYRING_SERVICE, KEYRING_USER)
    if not blob:
        raise RuntimeError(
            f"No enrolled centroid in keychain (service={KEYRING_SERVICE} "
            f"user={KEYRING_USER}). Run `python jarvis_enroll.py enroll` first."
        )
    raw = base64.b64decode(blob)
    centroid = np.frombuffer(raw, dtype=np.float32)
    norm = float(np.linalg.norm(centroid))
    if norm < 1e-9:
        raise RuntimeError("loaded centroid has zero norm; re-enroll")
    return (centroid / norm).astype(np.float32)


# --- Model download -------------------------------------------------------

@dataclass
class DownloadedModel:
    onnx_path: Path
    repo_id: str
    revision: str
    file: str


def download_model(
    *,
    repo_id: str = DEFAULT_HF_REPO,
    filename: str = DEFAULT_HF_FILE,
    revision: Optional[str] = None,
    local_dir: Path = DEFAULT_MODEL_DIR,
) -> DownloadedModel:
    """Download the WeSpeaker ONNX from Hugging Face Hub.

    The revision SHA must be supplied via the JARVIS_SPEAKER_REVISION env var
    OR the `revision` arg. Pinning to "main" emits a security warning per the
    audit (tags and branches are mutable; production deployments need a
    40-char SHA).
    """
    from huggingface_hub import hf_hub_download

    if revision is None:
        revision = os.environ.get(DEFAULT_REVISION_ENV)

    if not revision:
        logger.warning(
            "%s not set and no revision arg provided; falling back to 'main'. "
            "Production use MUST pin a 40-char SHA per audit Section 8.",
            DEFAULT_REVISION_ENV,
        )
        revision = "main"
    elif len(revision) != 40 or not all(c in "0123456789abcdef" for c in revision.lower()):
        logger.warning(
            "revision=%s is not a 40-char hex SHA; HF tags and branches are "
            "mutable. Pin a SHA from the HF tree before production use.",
            revision,
        )

    local_dir.mkdir(parents=True, exist_ok=True)
    onnx_path = Path(
        hf_hub_download(
            repo_id=repo_id,
            filename=filename,
            revision=revision,
            local_dir=str(local_dir),
        )
    )
    logger.info(
        "Downloaded WeSpeaker ONNX: repo=%s revision=%s path=%s",
        repo_id, revision, onnx_path,
    )
    return DownloadedModel(
        onnx_path=onnx_path,
        repo_id=repo_id,
        revision=revision,
        file=filename,
    )


# --- FrameProcessor -------------------------------------------------------

class SpeakerVerificationProcessor(FrameProcessor):
    """Drop TranscriptionFrame when the just-spoken audio does not match Daniel.

    Pass-through for every other frame. UserStartedSpeakingFrame and
    UserStoppedSpeakingFrame must continue to flow so the LLMUserAggregator
    advances its turn state machine, otherwise the pipeline stalls.

    Wire the audio source via:

        audio_buffer = AudioBufferProcessor(
            sample_rate=16000, num_channels=1, buffer_size=0,
        )
        audio_buffer.add_event_handler(
            "on_user_turn_audio_data", verifier.on_user_turn_audio,
        )

    The buffer fires once per turn; the verifier caches the most recent PCM
    and consults it when a TranscriptionFrame arrives shortly after.
    """

    def __init__(
        self,
        *,
        embedder: WeSpeakerEmbedder,
        enrolled_centroid: np.ndarray,
        threshold: float = DEFAULT_THRESHOLD,
        sample_rate: int = EXPECTED_SAMPLE_RATE,
        event_log=None,
        on_reject=None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._embedder = embedder

        ref = np.asarray(enrolled_centroid, dtype=np.float32)
        norm = float(np.linalg.norm(ref))
        if norm < 1e-9:
            raise ValueError("enrolled_centroid has zero norm")
        self._ref = ref / norm

        self._threshold = float(threshold)
        self._sample_rate = int(sample_rate)
        self._events = event_log
        self._on_reject = on_reject  # optional callable(turn_id, score, reason)

        self._last_pcm: Optional[bytes] = None
        self._last_sr: int = self._sample_rate
        self._turn_id: int = 0
        self._accepts: int = 0
        self._rejects: int = 0

        logger.info(
            "SpeakerVerificationProcessor ready: threshold=%.3f dim=%d sr=%d",
            self._threshold, self._ref.shape[0], self._sample_rate,
        )

    @property
    def stats(self) -> dict:
        return {
            "turns_seen": self._turn_id,
            "accepts": self._accepts,
            "rejects": self._rejects,
            "threshold": self._threshold,
        }

    async def on_user_turn_audio(
        self,
        processor,
        audio: bytes,
        sample_rate: int,
        num_channels: int,
    ) -> None:
        """Called by AudioBufferProcessor when a user turn ends.

        Cache the raw PCM so process_frame can score it against the enrolled
        centroid as soon as the matching TranscriptionFrame arrives.
        """
        if num_channels != 1:
            logger.warning(
                "expected mono audio, got %d channels; using channel 0",
                num_channels,
            )
        self._last_pcm = audio
        self._last_sr = int(sample_rate)
        self._turn_id += 1
        logger.debug(
            "user turn captured: turn_id=%d bytes=%d sr=%d",
            self._turn_id, len(audio), sample_rate,
        )

    async def process_frame(self, frame: Frame, direction: FrameDirection) -> None:
        # Required first call per pipecat issue #2007 (silent hang otherwise).
        await super().process_frame(frame, direction)

        if not isinstance(frame, TranscriptionFrame):
            await self.push_frame(frame, direction)
            return

        if self._last_pcm is None:
            await self._reject(frame, direction, score=None, reason="no_audio_buffer")
            return

        try:
            cand = self._embedder(self._last_pcm, self._last_sr)
        except Exception as e:
            logger.exception("speaker embed failure: %s", e)
            await self._reject(frame, direction, score=None, reason="embed_error")
            return

        score = float(np.dot(cand, self._ref))
        if score >= self._threshold:
            self._accepts += 1
            self._emit_event(frame, "accept", score, "ok")
            logger.info(
                "speaker accept: turn_id=%d score=%.3f threshold=%.3f",
                self._turn_id, score, self._threshold,
            )
            await self.push_frame(frame, direction)
        else:
            await self._reject(
                frame, direction, score=score, reason="below_threshold",
            )

    async def _reject(
        self,
        frame: TranscriptionFrame,
        direction: FrameDirection,
        *,
        score: Optional[float],
        reason: str,
    ) -> None:
        self._rejects += 1
        self._emit_event(frame, "reject", score, reason)
        logger.warning(
            "speaker reject: turn_id=%d reason=%s score=%s threshold=%.3f preview=%r",
            self._turn_id, reason,
            f"{score:.3f}" if score is not None else "n/a",
            self._threshold,
            (frame.text or "")[:64],
        )
        if self._on_reject is not None:
            try:
                self._on_reject(self._turn_id, score, reason)
            except Exception as cb_err:
                logger.exception("on_reject callback raised: %s", cb_err)
        # Deliberately no push_frame; the LLM never sees this transcription.

    def _emit_event(
        self,
        frame: TranscriptionFrame,
        decision: str,
        score: Optional[float],
        reason: str,
    ) -> None:
        if self._events is None:
            return
        try:
            audio_ms = (
                int(1000 * len(self._last_pcm) / (2 * self._last_sr))
                if self._last_pcm else None
            )
            self._events.event(
                "speaker_verify",
                turn_id=self._turn_id,
                decision=decision,
                reason=reason,
                score=score,
                threshold=self._threshold,
                transcript_preview=(frame.text or "")[:64],
                audio_ms=audio_ms,
            )
        except Exception as e:
            logger.exception("event emit failed: %s", e)
