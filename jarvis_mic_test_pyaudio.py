#!/usr/bin/env python3
"""PyAudio-specific mic diagnostic for Pipecat's LocalAudioTransport.

Pipecat uses PyAudio (not sounddevice) for LocalAudioTransport. macOS TCC
tracks microphone permissions per-library: your iTerm grant for
sounddevice does NOT automatically apply to PyAudio. If the PyAudio
permission prompt was missed or denied, Pipecat reads pure silence.

This script opens a PyAudio input stream in the exact same way as Pipecat
does, records 3 seconds, and reports what's actually coming in.

Usage (from the iTerm window where Jarvis was running, AFTER Ctrl+C):
    source ~/venvs/local-ai/bin/activate
    python jarvis_mic_test_pyaudio.py
"""

from __future__ import annotations

import sys
import time

import numpy as np
import pyaudio

SAMPLE_RATE = 16000
CHANNELS = 1
FORMAT = pyaudio.paInt16
CHUNK = 1024
DURATION_S = 3


def main() -> int:
    print("=" * 60)
    print("Jarvis PyAudio mic diagnostic (Pipecat's audio backend)")
    print("=" * 60)

    pa = pyaudio.PyAudio()

    print(f"\n--- PyAudio devices ---")
    default_in = None
    try:
        info = pa.get_default_input_device_info()
        default_in = info["index"]
        print(f"Default input: #{default_in} - {info['name']}")
        print(f"  Channels:    {info['maxInputChannels']}")
        print(f"  Sample rate: {int(info['defaultSampleRate'])}")
    except Exception as e:
        print(f"Could not get default input: {e}")

    print(f"\n--- All input-capable devices ---")
    for i in range(pa.get_device_count()):
        try:
            info = pa.get_device_info_by_index(i)
            if info["maxInputChannels"] > 0:
                marker = "  <-- DEFAULT" if i == default_in else ""
                print(f"  [{i:2d}] {info['name']}{marker}")
        except Exception:
            pass

    print(f"\n--- Opening PyAudio input stream ---")
    print(f"  format={pyaudio.paInt16}  channels={CHANNELS}  rate={SAMPLE_RATE}")
    try:
        stream = pa.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=SAMPLE_RATE,
            input=True,
            frames_per_buffer=CHUNK,
        )
    except Exception as e:
        print(f"\nERROR: pa.open() raised: {e}")
        print("\nThis typically means:")
        print("  1. PyAudio does not have microphone permission for this terminal.")
        print("     Fix: System Settings > Privacy & Security > Microphone,")
        print("          enable iTerm (and/or 'python').")
        print("  2. The default input device is missing or locked by another app.")
        pa.terminate()
        return 2

    print(f"\nRecording {DURATION_S} seconds. SAY 'JARVIS, TESTING' loudly now...")
    for i in range(3, 0, -1):
        print(f"  {i}...", end=" ", flush=True)
        time.sleep(1)
    print("RECORDING")

    frames = []
    total_samples = int(SAMPLE_RATE * DURATION_S / CHUNK) * CHUNK
    chunks = total_samples // CHUNK
    for _ in range(chunks):
        data = stream.read(CHUNK, exception_on_overflow=False)
        frames.append(np.frombuffer(data, dtype=np.int16))

    stream.stop_stream()
    stream.close()
    pa.terminate()

    audio = np.concatenate(frames).astype(np.float32) / 32768.0
    mean_abs = float(np.abs(audio).mean())
    max_abs = float(np.abs(audio).max())
    rms = float(np.sqrt(np.mean(audio ** 2)))

    print(f"\n--- PyAudio recording stats ---")
    print(f"  Samples:       {len(audio)}")
    print(f"  Min amplitude: {audio.min():+.4f}")
    print(f"  Max amplitude: {audio.max():+.4f}")
    print(f"  Mean |abs|:    {mean_abs:.4f}")
    print(f"  Peak |abs|:    {max_abs:.4f}")
    print(f"  RMS:           {rms:.4f}")

    print(f"\n--- Verdict ---")
    if mean_abs == 0.0 and max_abs == 0.0:
        print("*** PyAudio returns pure silence. ***")
        print("    macOS TCC is blocking PyAudio from this terminal.")
        print("    Fix path A (recommended):")
        print("      System Settings > Privacy & Security > Microphone")
        print("      > ensure iTerm is toggled ON")
        print("      > if there's a separate 'python' entry, toggle it ON")
        print("      > restart iTerm completely (quit, reopen)")
        print("    Fix path B (if path A doesn't help):")
        print("      System Settings > Privacy & Security > Microphone")
        print("      > REMOVE iTerm from the list using the minus button")
        print("      > re-run Jarvis, accept the new permission prompt")
        return 1
    elif mean_abs < 0.003:
        print("*** Very low signal. Mic is reaching PyAudio but almost silent. ***")
        print("    You likely need to speak closer/louder, or your system input")
        print("    level is set very low:")
        print("      System Settings > Sound > Input > raise the input volume")
        return 1
    else:
        print(f"*** OK: PyAudio captured audio at mean {mean_abs:.4f}. ***")
        print("    If Pipecat still isn't reacting, the issue is inside the")
        print("    Pipecat pipeline (VAD threshold, frame routing). Tell the")
        print("    agent to enable TRACE logging on pipecat.audio.vad.silero.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
