#!/usr/bin/env python3
"""
Test client for the Voice Assistant API Server
Can be used from any device on your network
"""

import requests
import sounddevice as sd
import numpy as np
from scipy.io import wavfile
import tempfile
import os

SERVER_URL = "http://localhost:5000"  # Change to server IP for remote testing

def test_text_query():
    """Test with text query"""
    print("\n=== Testing Text Query ===")
    response = requests.post(
        f"{SERVER_URL}/text_query",
        json={"text": "What's the weather like today?"}
    )
    print(f"Response: {response.json()}")

def test_audio_query():
    """Test with audio query"""
    print("\n=== Testing Audio Query ===")
    print("Recording 5 seconds of audio...")

    # Record audio
    sample_rate = 16000
    duration = 5
    recording = sd.rec(
        int(duration * sample_rate),
        samplerate=sample_rate,
        channels=1,
        dtype=np.float32
    )
    sd.wait()
    print("Recording complete")

    # Save to temp file
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        temp_path = f.name
        wavfile.write(temp_path, sample_rate, (recording * 32767).astype(np.int16))

    # Send to server
    with open(temp_path, 'rb') as f:
        files = {'audio': f}
        response = requests.post(f"{SERVER_URL}/query", files=files)

    os.unlink(temp_path)

    if response.status_code == 200:
        data = response.json()
        print(f"Transcription: {data['transcription']}")
        print(f"Response: {data['response']}")
    else:
        print(f"Error: {response.json()}")

def test_health():
    """Test health endpoint"""
    print("\n=== Testing Health Endpoint ===")
    response = requests.get(f"{SERVER_URL}/health")
    print(f"Server status: {response.json()}")

if __name__ == "__main__":
    import sys

    print("Voice Assistant Test Client")
    print(f"Server: {SERVER_URL}\n")

    if len(sys.argv) > 1 and sys.argv[1] == "text":
        test_text_query()
    elif len(sys.argv) > 1 and sys.argv[1] == "audio":
        test_audio_query()
    else:
        # Run all tests
        test_health()
        test_text_query()
        # test_audio_query()  # Uncomment to test with microphone
