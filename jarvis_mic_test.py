#!/usr/bin/env python3
"""Diagnostic: is the microphone actually reaching Python, and at what level?

Run this AFTER stopping Jarvis (Ctrl+C the other terminal). Records 3 seconds
from the default input device, prints the energy envelope, and tells you
whether the current wake threshold (0.03) would have fired.

Usage:
    source ~/venvs/local-ai/bin/activate
    python jarvis_mic_test.py
"""

from __future__ import annotations

import sys
import time

import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16000
DURATION_S = 3
WAKE_THRESHOLD = 0.03


def main() -> int:
    print("=" * 60)
    print("Jarvis microphone diagnostic")
    print("=" * 60)

    try:
        devices = sd.query_devices()
    except Exception as e:
        print(f"ERROR: sd.query_devices() failed: {e}")
        print("This usually means sounddevice cannot reach CoreAudio. "
              "Check that sounddevice is installed in the active venv.")
        return 2

    print(f"\n--- All audio devices ---")
    for i, d in enumerate(devices):
        kind = []
        if d.get("max_input_channels", 0) > 0:
            kind.append("IN")
        if d.get("max_output_channels", 0) > 0:
            kind.append("OUT")
        marker = ""
        default_in = sd.default.device[0] if isinstance(sd.default.device, (tuple, list)) else sd.default.device
        if i == default_in:
            marker = "  <-- DEFAULT INPUT"
        print(f"  [{i:2d}] {','.join(kind):7s}  {d['name']}{marker}")

    default_input = sd.query_devices(kind="input")
    print(f"\n--- Default input device ---")
    print(f"  Name:       {default_input['name']}")
    print(f"  Channels:   {default_input['max_input_channels']}")
    print(f"  Sample rate: {default_input['default_samplerate']}")

    print(f"\nRecording {DURATION_S} seconds. SAY 'JARVIS' loudly into the mic now...")
    for i in range(3, 0, -1):
        print(f"  {i}...", end=" ", flush=True)
        time.sleep(1)
    print("RECORDING")

    try:
        audio = sd.rec(
            int(DURATION_S * SAMPLE_RATE),
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype=np.float32,
        )
        sd.wait()
    except Exception as e:
        print(f"\nERROR: sd.rec() raised: {e}")
        print("\nThis usually means one of:")
        print("  1. No microphone permission for this terminal app")
        print("     -> System Settings > Privacy & Security > Microphone")
        print("     -> Enable the terminal app (iTerm or Terminal)")
        print("  2. Microphone device disconnected")
        print("  3. Another process has exclusive mic access")
        return 2

    audio = audio.flatten()
    mean_abs = float(np.abs(audio).mean())
    max_abs = float(np.abs(audio).max())
    min_val = float(audio.min())
    max_val = float(audio.max())
    # RMS
    rms = float(np.sqrt(np.mean(audio ** 2)))

    print(f"\n--- Recording stats ---")
    print(f"  Samples:       {len(audio)}")
    print(f"  Min amplitude: {min_val:+.4f}")
    print(f"  Max amplitude: {max_val:+.4f}")
    print(f"  Mean |abs|:    {mean_abs:.4f}")
    print(f"  Peak |abs|:    {max_abs:.4f}")
    print(f"  RMS:           {rms:.4f}")

    print(f"\n--- Wake-threshold analysis ---")
    print(f"  Current threshold:  {WAKE_THRESHOLD}")
    print(f"  Your mean |abs|:    {mean_abs:.4f}")
    if mean_abs == 0.0:
        print("\n*** PROBLEM: microphone returns pure silence. ***")
        print("    This is almost always a permission issue.")
        print("    Open System Settings > Privacy & Security > Microphone")
        print("    and verify iTerm (or Terminal) is listed AND enabled.")
        print("    If it's listed but toggled off, enable it and restart the")
        print("    terminal. If it's not listed at all, re-run Jarvis and")
        print("    accept the permission prompt when it appears.")
        return 1
    elif mean_abs < WAKE_THRESHOLD:
        ratio = mean_abs / WAKE_THRESHOLD
        suggested = max(0.005, mean_abs * 0.5)
        print(f"\n*** WARNING: your speech is {ratio*100:.0f}% of threshold. ***")
        print(f"    Wake word will NOT fire at current settings.")
        print(f"    Options:")
        print(f"      1. Speak louder / closer to mic")
        print(f"      2. Lower threshold:")
        print(f"         export JARVIS_WAKE_THRESHOLD={suggested:.3f}")
        print(f"         ./run-jarvis-gemma4.sh")
        print(f"      3. Check System Settings > Sound > Input and raise input level")
        return 1
    else:
        ratio = mean_abs / WAKE_THRESHOLD
        print(f"\n*** OK: your speech is {ratio*100:.0f}% of threshold. Wake word should fire. ***")
        print(f"    If Jarvis still isn't responding, the issue is elsewhere")
        print(f"    (transcription not returning 'jarvis', routing loop, etc).")
        print(f"    Check ./run-jarvis-health.sh --tail 20 after running Jarvis.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
