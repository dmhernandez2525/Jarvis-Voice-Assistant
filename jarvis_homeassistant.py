#!/usr/bin/env python3
"""
JARVIS with Home Assistant Integration
Controls smart home devices via Home Assistant
"""

import whisper
import sounddevice as sd
import numpy as np
import ollama
import pyttsx3
import tempfile
import os
from scipy.io import wavfile
import pvporcupine
import requests
import json
import re

class JarvisHomeAssistant:
    def __init__(self,
                 model_name="qwen2.5:72b",
                 whisper_model="large",
                 ha_url="http://localhost:8123",
                 ha_token=None):

        print("Initializing JARVIS with Home Assistant...")

        # Initialize Whisper
        print(f"Loading Whisper model: {whisper_model}")
        self.whisper = whisper.load_model(whisper_model)

        # Initialize Ollama
        print(f"Connecting to Ollama model: {model_name}")
        self.ollama_model = model_name

        # Initialize TTS
        print("Initializing text-to-speech...")
        self.tts = pyttsx3.init()
        self.tts.setProperty('rate', 175)

        # Home Assistant configuration
        self.ha_url = ha_url
        self.ha_token = ha_token
        self.ha_headers = {
            "Authorization": f"Bearer {ha_token}",
            "Content-Type": "application/json"
        } if ha_token else {}

        # Initialize Porcupine wake word
        print("Initializing wake word detection (Jarvis)...")
        self.porcupine = pvporcupine.create(keywords=['jarvis'])

        self.sample_rate = 16000
        self.frame_length = self.porcupine.frame_length

        # Smart home device mapping
        self.device_keywords = {
            'light': ['light', 'lights', 'lamp', 'lamps'],
            'switch': ['switch', 'plug', 'outlet'],
            'thermostat': ['temperature', 'thermostat', 'heating', 'cooling'],
            'lock': ['lock', 'door'],
            'cover': ['blinds', 'curtains', 'shades', 'garage']
        }

        print("\n" + "="*60)
        print("JARVIS with Home Assistant is ready!")
        print("Say 'Jarvis' to activate")
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

                keyword_index = self.porcupine.process(audio_frame)

                if keyword_index >= 0:
                    print("\n🎯 Wake word detected!")
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
        return recording.flatten()

    def transcribe(self, audio):
        """Convert speech to text"""
        print("🔄 Transcribing...")
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_path = f.name
            wavfile.write(temp_path, self.sample_rate, (audio * 32767).astype(np.int16))

        result = self.whisper.transcribe(temp_path)
        text = result["text"].strip()
        os.unlink(temp_path)

        print(f"📝 You said: {text}")
        return text

    def control_homeassistant(self, command_text):
        """Parse command and control Home Assistant devices"""
        command_lower = command_text.lower()

        # Check if this is a smart home command
        is_smart_home = any(
            keyword in command_lower
            for keywords in self.device_keywords.values()
            for keyword in keywords
        )

        if not is_smart_home:
            return None  # Not a smart home command

        # Determine action
        if any(word in command_lower for word in ['turn on', 'switch on', 'open', 'unlock']):
            action = 'turn_on'
        elif any(word in command_lower for word in ['turn off', 'switch off', 'close', 'lock']):
            action = 'turn_off'
        elif 'set' in command_lower or 'temperature' in command_lower:
            action = 'set_value'
        else:
            return None

        # Extract device entity (simplified - in production, use entity IDs)
        # This is a placeholder - you'd map to actual Home Assistant entity IDs
        try:
            # Example: Call Home Assistant API
            if self.ha_token:
                response = requests.post(
                    f"{self.ha_url}/api/services/homeassistant/{action}",
                    headers=self.ha_headers,
                    json={"entity_id": "light.living_room"}  # Example
                )

                if response.status_code == 200:
                    return f"Smart home command executed: {action}"
                else:
                    return f"Failed to execute command: {response.text}"
            else:
                return "Home Assistant not configured. Command would execute: " + action

        except Exception as e:
            return f"Error controlling device: {str(e)}"

    def get_response(self, text):
        """Get response from LLM or execute smart home command"""

        # First, try to execute smart home command
        ha_result = self.control_homeassistant(text)

        if ha_result:
            print(f"🏠 Home Assistant: {ha_result}")
            return ha_result

        # If not a smart home command, use LLM
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
        """Run JARVIS"""
        try:
            while True:
                if not self.listen_for_wakeword():
                    break

                audio = self.listen(duration=5)
                text = self.transcribe(audio)

                if not text:
                    self.speak("I didn't catch that, sir.")
                    continue

                response = self.get_response(text)
                self.speak(response)

                print("\nReady for next command...\n")

        except KeyboardInterrupt:
            print("\n\nShutting down JARVIS...")
        finally:
            if self.porcupine:
                self.porcupine.delete()


if __name__ == "__main__":
    # Configuration
    HOME_ASSISTANT_URL = "http://192.168.1.100:8123"  # Change to your HA IP
    HOME_ASSISTANT_TOKEN = None  # Add your long-lived access token

    jarvis = JarvisHomeAssistant(
        model_name="qwen2.5:72b",
        whisper_model="large",
        ha_url=HOME_ASSISTANT_URL,
        ha_token=HOME_ASSISTANT_TOKEN
    )

    jarvis.run()
