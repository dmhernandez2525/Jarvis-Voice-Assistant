#!/usr/bin/env python3
"""
JARVIS Voice Assistant with Wake Word Detection
Uses "Jarvis" as the wake word to activate
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
import struct
import pvporcupine

class JarvisAssistant:
    def __init__(self, model_name="qwen2.5:72b", whisper_model="large"):
        print("Initializing JARVIS...")
        print(f"Loading Whisper model: {whisper_model}")
        self.whisper = whisper.load_model(whisper_model)

        print(f"Connecting to Ollama model: {model_name}")
        self.ollama_model = model_name

        print("Initializing text-to-speech...")
        self.tts = pyttsx3.init()
        self.tts.setProperty('rate', 175)  # Speed of speech

        # Initialize Porcupine for wake word detection
        print("Initializing wake word detection (Jarvis)...")
        self.porcupine = pvporcupine.create(
            keywords=['jarvis']  # Built-in wake word
        )

        self.sample_rate = 16000
        self.frame_length = self.porcupine.frame_length

        print("\n" + "="*60)
        print("JARVIS is ready!")
        print("Say 'Jarvis' to activate, then speak your command")
        print("="*60 + "\n")

    def listen_for_wakeword(self):
        """Listen for the wake word 'Jarvis'"""
        print("Listening for wake word...")

        audio_stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype='int16',
            blocksize=self.frame_length
        )

        audio_stream.start()

        try:
            while True:
                audio_frame, _ = audio_stream.read(self.frame_length)
                audio_frame = audio_frame.flatten()

                # Convert to bytes for porcupine
                keyword_index = self.porcupine.process(audio_frame)

                if keyword_index >= 0:
                    print("\n🎯 Wake word detected! Listening...")
                    audio_stream.stop()
                    return True

        except KeyboardInterrupt:
            audio_stream.stop()
            return False

    def listen(self, duration=5):
        """Record audio from microphone"""
        print(f"🎤 Recording for {duration} seconds...")
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
        print("🤔 JARVIS is thinking...")

        response = ollama.generate(
            model=self.ollama_model,
            prompt=text,
            stream=False
        )

        answer = response['response'].strip()
        print(f"💬 JARVIS: {answer}")
        return answer

    def speak(self, text):
        """Convert text to speech"""
        print("🔊 JARVIS speaking...")
        self.tts.say(text)
        self.tts.runAndWait()

    def run(self):
        """Run JARVIS with wake word detection"""
        try:
            while True:
                # Listen for wake word
                if not self.listen_for_wakeword():
                    break

                # Wake word detected, record command
                audio = self.listen(duration=5)

                # Transcribe
                text = self.transcribe(audio)

                if not text:
                    self.speak("I didn't catch that, sir.")
                    continue

                # Get response
                response = self.get_response(text)

                # Speak response
                self.speak(response)

                print("\nReady for next command...\n")

        except KeyboardInterrupt:
            print("\n\nShutting down JARVIS...")
        finally:
            if self.porcupine:
                self.porcupine.delete()

if __name__ == "__main__":
    # Initialize and run JARVIS
    jarvis = JarvisAssistant(
        model_name="qwen2.5:72b",
        whisper_model="large"
    )

    jarvis.run()
