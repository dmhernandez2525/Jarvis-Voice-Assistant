#!/usr/bin/env python3
"""Speaker enrollment CLI for Jarvis.

Subcommands:

    python jarvis_enroll.py download
        Download the WeSpeaker ResNet34-LM ONNX from Hugging Face. Pin the
        revision SHA via the JARVIS_SPEAKER_REVISION env var.

    python jarvis_enroll.py enroll
        Record several short clips of your voice, embed each, average into
        a centroid, store the centroid in macOS Keychain.

    python jarvis_enroll.py verify
        Record one clip and score it against the enrolled centroid. Prints
        cosine similarity and accept/reject relative to the threshold.

    python jarvis_enroll.py info
        Print the current enrollment metadata (model SHA, dim, date, etc.).

Audit reference: ~/Desktop/command-center/research/local-ai-stack/12-Speaker-ID-Audit.md
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
import wave
from pathlib import Path
from typing import Optional

import numpy as np

from jarvis_logging import setup_logging
from jarvis_speaker import (
    DEFAULT_HF_FILE,
    DEFAULT_HF_REPO,
    DEFAULT_META_PATH,
    DEFAULT_MODEL_DIR,
    DEFAULT_REVISION_ENV,
    DEFAULT_THRESHOLD,
    EXPECTED_SAMPLE_RATE,
    KEYRING_SERVICE,
    KEYRING_USER,
    WeSpeakerEmbedder,
    download_model,
    load_centroid,
    save_centroid,
)

logger = logging.getLogger("jarvis.gemma4.enroll")

# --- Recording config -----------------------------------------------------

CLIPS_DEFAULT = 8
CLIP_SECONDS_DEFAULT = 6.0
CHUNK_FRAMES = 1024
CLIPS_DIR = Path(__file__).resolve().parent / "state" / "enrollment_clips"

# Phonetically diverse prompts. Mix of Harvard sentences and natural Jarvis
# commands. Audit Section 4 calls for "5-10 phonetically varied sentences
# (Harvard or CMU ARCTIC) plus at least 3 free-form typical Jarvis commands".
ENROLLMENT_PROMPTS = [
    "The birch canoe slid on the smooth planks. "
    "Glue the sheet to the dark blue background.",
    "It's easy to tell the depth of a well. "
    "These days a chicken leg is a rare dish.",
    "Rice is often served in round bowls. "
    "The juice of lemons makes fine punch.",
    "The box was thrown beside the parked truck. "
    "The hogs were fed chopped corn and garbage.",
    "Four hours of steady work faced us. "
    "Large size in stockings is hard to sell.",
    "Jarvis, what's the weather like today?",
    "Hey Jarvis, dim the lights and play some music.",
    "Jarvis, set a timer for fifteen minutes. "
    "Tell me when it goes off.",
    "Jarvis, what's on my calendar tomorrow morning?",
    "Hey Jarvis, can you increase the speed of your talking?",
]


# --- PyAudio recording ----------------------------------------------------

def record_clip(seconds: float, *, sample_rate: int = EXPECTED_SAMPLE_RATE) -> bytes:
    """Capture `seconds` of mono int16 PCM from the default input device."""
    import pyaudio

    pa = pyaudio.PyAudio()
    try:
        stream = pa.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=sample_rate,
            input=True,
            frames_per_buffer=CHUNK_FRAMES,
        )
    except OSError as e:
        pa.terminate()
        raise RuntimeError(
            f"Could not open the default input device (PyAudio: {e}). "
            "Check System Settings > Privacy & Security > Microphone for "
            "Terminal/iTerm permission."
        )

    total_frames = int(seconds * sample_rate)
    captured = 0
    chunks: list[bytes] = []
    last_print = 0.0
    start = time.monotonic()
    try:
        while captured < total_frames:
            want = min(CHUNK_FRAMES, total_frames - captured)
            buf = stream.read(want, exception_on_overflow=False)
            chunks.append(buf)
            captured += want
            now = time.monotonic()
            if now - last_print >= 0.5:
                elapsed = now - start
                remaining = max(0.0, seconds - elapsed)
                print(f"  recording... {remaining:4.1f}s remaining", end="\r", flush=True)
                last_print = now
    finally:
        try:
            stream.stop_stream()
            stream.close()
        finally:
            pa.terminate()

    print(" " * 60, end="\r")  # clear the recording line
    pcm = b"".join(chunks)

    # Quick energy check: warn if the clip looks silent.
    arr = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0
    if arr.size == 0:
        raise RuntimeError("zero-length recording; check microphone")
    rms = float(np.sqrt(np.mean(arr ** 2)))
    peak = float(np.max(np.abs(arr)))
    logger.info(
        "clip captured: seconds=%.1f bytes=%d rms=%.4f peak=%.4f",
        seconds, len(pcm), rms, peak,
    )
    if rms < 0.005:
        logger.warning(
            "clip RMS=%.4f looks silent; speak closer to the mic or check input level",
            rms,
        )
    return pcm


def save_wav(pcm: bytes, path: Path, *, sample_rate: int = EXPECTED_SAMPLE_RATE) -> None:
    """Persist a clip on disk for later re-embedding / threshold tuning."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sample_rate)
        f.writeframes(pcm)
    logger.info("clip saved: %s (%d bytes)", path, len(pcm))


# --- CLI: download --------------------------------------------------------

def cmd_download(args: argparse.Namespace) -> int:
    revision = args.revision or os.environ.get(DEFAULT_REVISION_ENV)
    info = download_model(
        repo_id=args.repo,
        filename=args.filename,
        revision=revision,
        local_dir=Path(args.local_dir),
    )
    print()
    print(f"  ONNX path:  {info.onnx_path}")
    print(f"  Repo:       {info.repo_id}")
    print(f"  Revision:   {info.revision}")
    print(f"  File:       {info.file}")
    print()
    if info.revision == "main":
        print(
            "  WARNING: revision 'main' is mutable. After verifying the model "
            "works, pin a 40-char SHA via:"
        )
        print(f"    export {DEFAULT_REVISION_ENV}=<sha-from-HF-tree>")
    return 0


# --- CLI: enroll ----------------------------------------------------------

def _prompt_continue(message: str) -> bool:
    """Block on stdin Enter; return False if user types 'q'/'quit'/'exit'."""
    try:
        ans = input(f"{message} [Enter to continue, q to quit] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        return False
    return ans not in {"q", "quit", "exit"}


def cmd_enroll(args: argparse.Namespace) -> int:
    onnx_path = _resolve_onnx_path(args)
    embedder = WeSpeakerEmbedder(onnx_path)

    n_clips = max(1, args.clips)
    clip_seconds = max(2.0, args.seconds)
    save_clips = bool(args.save_clips)

    print()
    print("=" * 64)
    print(" JARVIS speaker enrollment")
    print("=" * 64)
    print(f" Recording {n_clips} clips of {clip_seconds:.0f}s each "
          f"({n_clips * clip_seconds:.0f}s total).")
    print(" Speak naturally at your normal volume and pace.")
    print(" Vary your tone across clips. Mix in the prompts shown.")
    if save_clips:
        print(f" Audio will be saved under {CLIPS_DIR} for later threshold tuning.")
    print()

    embeddings: list[np.ndarray] = []
    clip_paths: list[Path] = []
    enroll_started = time.time()
    enrollment_id = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime(enroll_started))

    for i in range(n_clips):
        prompt = ENROLLMENT_PROMPTS[i % len(ENROLLMENT_PROMPTS)]
        print(f"--- Clip {i + 1}/{n_clips} ---")
        print(f"  Prompt: {prompt}")
        if not _prompt_continue("  Ready?"):
            print(" enrollment aborted by user")
            return 1
        print(f"  Recording {clip_seconds:.0f}s...")
        try:
            pcm = record_clip(clip_seconds)
        except RuntimeError as e:
            logger.error("recording failed: %s", e)
            print(f"  ERROR: {e}")
            return 2

        if save_clips:
            clip_path = CLIPS_DIR / enrollment_id / f"clip-{i + 1:02d}.wav"
            save_wav(pcm, clip_path)
            clip_paths.append(clip_path)

        try:
            emb = embedder(pcm, EXPECTED_SAMPLE_RATE)
        except Exception as e:
            logger.exception("embed failed for clip %d: %s", i + 1, e)
            print(f"  ERROR embedding clip: {e}")
            return 3
        embeddings.append(emb)
        print(f"  embedded ({emb.shape[0]}-dim)")
        print()

    if not embeddings:
        print("no clips captured; nothing to enroll")
        return 4

    # Average and re-normalize.
    stack = np.stack(embeddings, axis=0)
    centroid = stack.mean(axis=0)
    centroid = centroid / (np.linalg.norm(centroid) + 1e-9)
    centroid = centroid.astype(np.float32)

    # Self-coherence: how tight is the cluster?
    self_scores = [float(np.dot(centroid, e)) for e in embeddings]
    inter_scores = []
    for i in range(len(embeddings)):
        for j in range(i + 1, len(embeddings)):
            inter_scores.append(float(np.dot(embeddings[i], embeddings[j])))
    self_mean = float(np.mean(self_scores))
    self_min = float(np.min(self_scores))
    inter_mean = float(np.mean(inter_scores)) if inter_scores else float("nan")

    print("Enrollment summary:")
    print(f"  Clips embedded:        {len(embeddings)}")
    print(f"  Centroid dim:          {centroid.shape[0]}")
    print(f"  Avg sim(clip,centroid): {self_mean:.3f}")
    print(f"  Min sim(clip,centroid): {self_min:.3f}")
    print(f"  Avg pairwise sim:      {inter_mean:.3f}")
    print()
    if self_min < 0.5:
        print(
            "  WARNING: at least one clip has cosine sim < 0.5 with the "
            "centroid. That clip may be noisy or capture a different "
            "speaker. Consider re-recording it."
        )

    # Confirm before storing.
    if not _prompt_continue("Save this centroid to macOS Keychain?"):
        print("  not saved")
        return 0

    meta = {
        "enrollment_id": enrollment_id,
        "model_repo": getattr(args, "repo", DEFAULT_HF_REPO),
        "model_file": getattr(args, "filename", DEFAULT_HF_FILE),
        "model_revision": os.environ.get(DEFAULT_REVISION_ENV) or "main",
        "onnx_path": str(onnx_path),
        "sample_rate": EXPECTED_SAMPLE_RATE,
        "clips_recorded": len(embeddings),
        "clip_seconds": clip_seconds,
        "self_mean_similarity": self_mean,
        "self_min_similarity": self_min,
        "inter_mean_similarity": inter_mean,
        "saved_clips": [str(p) for p in clip_paths],
        "default_threshold": DEFAULT_THRESHOLD,
    }
    save_centroid(centroid, meta=meta)
    print(f"Saved. Suggested starting threshold: {DEFAULT_THRESHOLD:.2f}")
    print()
    print("Next steps:")
    print("  1. python jarvis_enroll.py verify    # try a held-out Daniel clip")
    print("  2. python jarvis_enroll.py verify    # try with a non-Daniel speaker")
    print("  3. tune threshold per the audit's threshold-tuning checklist")
    return 0


# --- CLI: verify ----------------------------------------------------------

def cmd_verify(args: argparse.Namespace) -> int:
    onnx_path = _resolve_onnx_path(args)
    embedder = WeSpeakerEmbedder(onnx_path)
    centroid = load_centroid()
    threshold = float(args.threshold) if args.threshold is not None else DEFAULT_THRESHOLD
    seconds = max(2.0, float(args.seconds))

    print()
    print("=" * 64)
    print(" JARVIS speaker verification probe")
    print("=" * 64)
    print(f" Recording {seconds:.0f}s. Speak naturally.")
    print()
    if not _prompt_continue("Ready?"):
        return 1
    pcm = record_clip(seconds)
    cand = embedder(pcm, EXPECTED_SAMPLE_RATE)
    score = float(np.dot(cand, centroid))
    decision = "ACCEPT" if score >= threshold else "REJECT"

    print()
    print(f"  cosine similarity: {score:.4f}")
    print(f"  threshold:         {threshold:.4f}")
    print(f"  decision:          {decision}")
    if score >= threshold:
        margin = score - threshold
        print(f"  margin:            +{margin:.4f}")
    else:
        margin = threshold - score
        print(f"  margin:            -{margin:.4f}")
    return 0 if score >= threshold else 10


# --- CLI: info ------------------------------------------------------------

def cmd_info(_: argparse.Namespace) -> int:
    print()
    print(f"Keyring service: {KEYRING_SERVICE}")
    print(f"Keyring user:    {KEYRING_USER}")
    try:
        c = load_centroid()
        print(f"Centroid:        loaded ok, dim={c.shape[0]}, "
              f"norm={float(np.linalg.norm(c)):.3f}")
    except RuntimeError as e:
        print(f"Centroid:        NOT enrolled ({e})")

    if DEFAULT_META_PATH.is_file():
        print()
        print(f"Metadata: {DEFAULT_META_PATH}")
        try:
            meta = json.loads(DEFAULT_META_PATH.read_text())
            print(json.dumps(meta, indent=2))
        except Exception as e:
            print(f"  (could not parse: {e})")
    else:
        print(f"Metadata file missing: {DEFAULT_META_PATH}")

    revision = os.environ.get(DEFAULT_REVISION_ENV)
    print()
    print(f"{DEFAULT_REVISION_ENV} = {revision or '(unset)'}")
    if not revision:
        print("  Pin a SHA via this env var before production use.")
    return 0


# --- helpers --------------------------------------------------------------

def _resolve_onnx_path(args: argparse.Namespace) -> Path:
    if args.onnx_path:
        return Path(args.onnx_path)

    # Prefer the file the download subcommand placed.
    candidate = Path(args.local_dir) / args.filename
    if candidate.is_file():
        return candidate

    # huggingface_hub puts files at <local_dir>/<filename> directly when
    # local_dir is set, but older versions used a snapshot subdir. Try a
    # recursive lookup as a last resort.
    matches = list(Path(args.local_dir).rglob(args.filename))
    if matches:
        return matches[0]

    raise FileNotFoundError(
        f"Could not find {args.filename} under {args.local_dir}. "
        f"Run `python jarvis_enroll.py download` first."
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="jarvis_enroll",
        description="Speaker enrollment and verification for Jarvis.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--repo", default=DEFAULT_HF_REPO,
        help=f"HF repo id (default: {DEFAULT_HF_REPO})",
    )
    common.add_argument(
        "--filename", default=DEFAULT_HF_FILE,
        help=f"ONNX file inside the repo (default: {DEFAULT_HF_FILE})",
    )
    common.add_argument(
        "--local-dir", default=str(DEFAULT_MODEL_DIR),
        help="Where to cache the ONNX file on disk",
    )
    common.add_argument(
        "--onnx-path", default=None,
        help="Override the resolved ONNX path entirely",
    )

    p_dl = sub.add_parser("download", parents=[common],
                          help="Download the WeSpeaker ONNX from HF Hub")
    p_dl.add_argument(
        "--revision", default=None,
        help=f"HF revision SHA (or use {DEFAULT_REVISION_ENV} env var)",
    )
    p_dl.set_defaults(func=cmd_download)

    p_en = sub.add_parser("enroll", parents=[common],
                          help="Record clips and enroll your voice")
    p_en.add_argument("--clips", type=int, default=CLIPS_DEFAULT,
                      help=f"Number of clips (default: {CLIPS_DEFAULT})")
    p_en.add_argument("--seconds", type=float, default=CLIP_SECONDS_DEFAULT,
                      help=f"Seconds per clip (default: {CLIP_SECONDS_DEFAULT})")
    p_en.add_argument("--save-clips", action="store_true",
                      help="Persist WAV files under state/enrollment_clips/")
    p_en.set_defaults(func=cmd_enroll)

    p_vf = sub.add_parser("verify", parents=[common],
                          help="Score one clip against the enrolled centroid")
    p_vf.add_argument("--seconds", type=float, default=CLIP_SECONDS_DEFAULT,
                      help=f"Seconds to record (default: {CLIP_SECONDS_DEFAULT})")
    p_vf.add_argument("--threshold", type=float, default=None,
                      help=f"Override threshold (default: {DEFAULT_THRESHOLD})")
    p_vf.set_defaults(func=cmd_verify)

    p_info = sub.add_parser("info", help="Show current enrollment status")
    p_info.set_defaults(func=cmd_info)

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    setup_logging(name="jarvis.gemma4.enroll")
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
