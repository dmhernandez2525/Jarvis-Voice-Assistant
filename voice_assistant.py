#!/usr/bin/env python3
"""
Voice Assistant - Maximum Intelligence Edition
Uses Whisper for speech-to-text and Qwen 2.5:72b for responses
"""

import whisper
import sounddevice as sd
import numpy as np
import ollama
import pyttsx3
import wave
import tempfile
import os
from scipy.io import wavfile
import time

class VoiceAssistant:
    def __init__(self, model_name="qwen2.5:72b", whisper_model="large"):
        print("Initializing Voice Assistant...")
        print(f"Loading Whisper model: {whisper_model}")
        self.whisper = whisper.load_model(whisper_model)

        print(f"Connecting to Ollama model: {model_name}")
        self.ollama_model = model_name

        print("Initializing text-to-speech...")
        self.tts = pyttsx3.init()
        self.tts.setProperty('rate', 175)  # Speed of speech

        self.sample_rate = 16000
        self.is_listening = False

        print("Voice Assistant ready!")

    def listen(self, duration=5):
        """Record audio from microphone"""
        print(f"\n🎤 Listening for {duration} seconds...")
        recording = sd.rec(
            int(duration * self.sample_rate),
            samplerate=self.sample_rate,
            channels=1,
            dtype=np.float32
        )
        sd.wait()
        print("✓ Recording complete")
        return recording.flatten()

    def transcribe(self, audio):
        """Convert speech to text using Whisper"""
        print("🔄 Transcribing audio...")

        # Save audio to temporary file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_path = f.name
            wavfile.write(temp_path, self.sample_rate, (audio * 32767).astype(np.int16))

        # Transcribe
        result = self.whisper.transcribe(temp_path)
        text = result["text"].strip()

        # Clean up
        os.unlink(temp_path)

        print(f"📝 You said: {text}")
        return text

    def get_response(self, text):
        """Get response from Qwen 2.5:72b"""
        print("🤔 Thinking...")

        response = ollama.generate(
            model=self.ollama_model,
            prompt=text,
            stream=False
        )

        answer = response['response'].strip()
        print(f"💬 Response: {answer}")
        return answer

    def speak(self, text):
        """Convert text to speech"""
        print("🔊 Speaking...")
        self.tts.say(text)
        self.tts.runAndWait()

    def run_interactive(self):
        """Run interactive voice assistant on this Mac"""
        print("\n" + "="*60)
        print("VOICE ASSISTANT - Interactive Mode")
        print("="*60)
        print("\nPress Enter to start recording, or 'q' to quit")

        while True:
            user_input = input("\n[Press Enter to speak, 'q' to quit]: ")

            if user_input.lower() == 'q':
                print("Goodbye!")
                break

            # Listen
            audio = self.listen(duration=5)

            # Transcribe
            text = self.transcribe(audio)

            if not text:
                print("No speech detected. Try again.")
                continue

            # Get response
            response = self.get_response(text)

            # Speak response
            self.speak(response)


if __name__ == "__main__":
    # Initialize and run
    assistant = VoiceAssistant(
        model_name="qwen2.5:72b",
        whisper_model="large"
    )

    assistant.run_interactive()
