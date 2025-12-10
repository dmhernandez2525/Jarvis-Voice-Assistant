#!/usr/bin/env python3
"""
JARVIS Voice Assistant - Smart Router
Uses a fast model to analyze queries and route to the appropriate model:
- Simple queries → Fast 7b model (0.5s)
- Moderate queries → Balanced 32b model (2-3s)
- Complex queries → Powerful 72b model (5-8s)

Best of all worlds: Speed when possible, intelligence when needed
"""

import whisper
import sounddevice as sd
import numpy as np
import ollama
import tempfile
import os
from scipy.io import wavfile
import time
from TTS.api import TTS

class SmartJarvis:
    def __init__(self, whisper_model="large"):
        print("Initializing Smart JARVIS with Model Router...")

        print(f"Loading Whisper model: {whisper_model}")
        start = time.time()
        self.whisper = whisper.load_model(whisper_model)
        print(f"  ⏱  Loaded in {int((time.time() - start) * 1000)}ms")

        # Model configuration
        self.router_model = "qwen2.5:7b"          # Fast model for routing decisions
        self.fast_model = "dolphin-mistral:7b"    # Fast, uncensored
        self.balanced_model = "qwen2.5:32b"       # Balanced performance
        self.powerful_model = "qwen2.5:72b"       # Maximum intelligence

        print("\nModel Configuration:")
        print(f"  🔀 Router: {self.router_model}")
        print(f"  ⚡ Fast: {self.fast_model}")
        print(f"  ⚖️  Balanced: {self.balanced_model}")
        print(f"  🧠 Powerful: {self.powerful_model}")

        print("\nInitializing Coqui TTS (open-source)...")
        start = time.time()
        self.tts = TTS("tts_models/en/ljspeech/tacotron2-DDC")
        print(f"  ⏱  Initialized in {int((time.time() - start) * 1000)}ms")

        self.sample_rate = 16000
        self.wake_threshold = 0.03
        self.wake_duration = 1.5
        self.command_duration = 15

        # Statistics tracking
        self.stats = {
            "fast_count": 0,
            "balanced_count": 0,
            "powerful_count": 0,
            "total_time_saved": 0
        }

        print("\n" + "="*60)
        print("Smart JARVIS is ready!")
        print("Automatically routes queries to optimal model")
        print("="*60 + "\n")

    def analyze_query_complexity(self, text):
        """
        Use fast router model to analyze query and determine complexity
        Returns: 'fast', 'balanced', or 'powerful'
        """
        print("🔀 Analyzing query complexity...")
        start = time.time()

        analysis_prompt = f"""Analyze this query and classify its complexity. Respond with ONLY ONE WORD:

SIMPLE - Basic facts, greetings, simple questions, jokes, casual chat
MODERATE - Explanations, comparisons, creative writing, code generation
COMPLEX - Deep analysis, multi-step reasoning, philosophical questions, complex technical tasks

Query: "{text}"

Classification:"""

        response = ollama.generate(
            model=self.router_model,
            prompt=analysis_prompt,
            stream=False,
            options={"temperature": 0.3}  # Low temperature for consistent routing
        )

        classification = response['response'].strip().upper()

        # Map to model choice
        if "SIMPLE" in classification or "FAST" in classification:
            choice = "fast"
            model = self.fast_model
            expected_time = "0.5-1s"
        elif "MODERATE" in classification or "BALANCED" in classification:
            choice = "balanced"
            model = self.balanced_model
            expected_time = "2-3s"
        else:  # COMPLEX or uncertain
            choice = "powerful"
            model = self.powerful_model
            expected_time = "5-8s"

        route_time = int((time.time() - start) * 1000)
        print(f"  ⏱  Routing decision: {route_time}ms")
        print(f"  📊 Complexity: {classification[:20]}")
        print(f"  🎯 Selected: {choice.upper()} model ({model})")
        print(f"  ⏰ Expected time: {expected_time}")

        return choice, model

    def listen_for_wakeword(self):
        """Listen for wake word using simple energy detection + Whisper verification"""
        print("Listening for wake word...")

        try:
            while True:
                audio = sd.rec(
                    int(self.wake_duration * self.sample_rate),
                    samplerate=self.sample_rate,
                    channels=1,
                    dtype=np.float32
                )
                sd.wait()

                if np.abs(audio).mean() > self.wake_threshold:
                    print("\n🎧 Sound detected, verifying...")
                    start = time.time()

                    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                        temp_path = f.name
                        wavfile.write(temp_path, self.sample_rate, (audio * 32767).astype(np.int16).flatten())

                    result = self.whisper.transcribe(temp_path, language="en")
                    text = result["text"].strip().lower()
                    os.unlink(temp_path)

                    verify_time = int((time.time() - start) * 1000)
                    print(f"  ⏱  Wake word verification: {verify_time}ms")

                    if "jarvis" in text:
                        print("🎯 Wake word 'Jarvis' detected!")
                        return True
                    else:
                        print(f"   False alarm: '{text}'")

                time.sleep(0.1)

        except KeyboardInterrupt:
            return False

    def listen(self, duration=15):
        """Record audio from microphone"""
        print(f"🎤 Recording for {duration} seconds...")
        start = time.time()

        recording = sd.rec(
            int(duration * self.sample_rate),
            samplerate=self.sample_rate,
            channels=1,
            dtype=np.float32
        )
        sd.wait()

        record_time = int((time.time() - start) * 1000)
        print(f"  ⏱  Recording: {record_time}ms")
        return recording.flatten()

    def transcribe(self, audio):
        """Convert speech to text using Whisper"""
        print("🔄 Transcribing audio...")
        start = time.time()

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_path = f.name
            wavfile.write(temp_path, self.sample_rate, (audio * 32767).astype(np.int16))

        result = self.whisper.transcribe(temp_path)
        text = result["text"].strip()
        os.unlink(temp_path)

        transcribe_time = int((time.time() - start) * 1000)
        print(f"  ⏱  Transcription: {transcribe_time}ms")
        print(f"📝 You said: {text}")
        return text

    def get_smart_response(self, text):
        """Analyze query and route to appropriate model"""

        # Step 1: Analyze complexity
        complexity, selected_model = self.analyze_query_complexity(text)

        # Update statistics
        self.stats[f"{complexity}_count"] += 1

        # Step 2: Get response from selected model
        print(f"🤔 JARVIS thinking ({complexity} mode)...")
        start = time.time()

        # Build prompt based on model type
        if "dolphin" in selected_model.lower():
            # Dolphin models work better with direct prompts
            prompt = text
        else:
            # Qwen models benefit from system context
            prompt = f"""You are JARVIS, a helpful AI assistant. Be direct and conversational.

User: {text}
JARVIS:"""

        response = ollama.generate(
            model=selected_model,
            prompt=prompt,
            stream=False,
            options={
                "temperature": 0.8,
                "top_p": 0.9
            }
        )

        answer = response['response'].strip()
        llm_time = int((time.time() - start) * 1000)

        # Calculate time saved vs always using powerful model
        if complexity == "fast":
            time_saved = 5000 - llm_time  # Assume 72b would take 5s
            self.stats["total_time_saved"] += time_saved
        elif complexity == "balanced":
            time_saved = 5000 - llm_time
            self.stats["total_time_saved"] += time_saved

        print(f"  ⏱  LLM inference: {llm_time}ms")
        if complexity != "powerful":
            print(f"  💰 Time saved vs 72b: ~{time_saved}ms")
        print(f"💬 JARVIS: {answer}")
        return answer

    def speak(self, text):
        """Convert text to speech using Coqui TTS"""
        print("🔊 JARVIS speaking...")
        start = time.time()

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            output_path = f.name
            self.tts.tts_to_file(text=text, file_path=output_path)

        sample_rate, audio_data = wavfile.read(output_path)
        sd.play(audio_data, sample_rate)
        sd.wait()
        os.unlink(output_path)

        tts_time = int((time.time() - start) * 1000)
        print(f"  ⏱  Text-to-speech: {tts_time}ms")

    def print_stats(self):
        """Print usage statistics"""
        total = self.stats["fast_count"] + self.stats["balanced_count"] + self.stats["powerful_count"]
        if total == 0:
            return

        print("\n" + "="*60)
        print("📊 ROUTING STATISTICS")
        print("="*60)
        print(f"Fast model (dolphin-mistral:7b):  {self.stats['fast_count']:3d} queries ({self.stats['fast_count']/total*100:.1f}%)")
        print(f"Balanced (qwen2.5:32b):           {self.stats['balanced_count']:3d} queries ({self.stats['balanced_count']/total*100:.1f}%)")
        print(f"Powerful (qwen2.5:72b):           {self.stats['powerful_count']:3d} queries ({self.stats['powerful_count']/total*100:.1f}%)")
        print(f"\nTotal time saved: {self.stats['total_time_saved']/1000:.1f}s ({self.stats['total_time_saved']/1000/60:.1f} min)")
        print("="*60 + "\n")

    def run(self):
        """Run JARVIS with smart routing"""
        try:
            while True:
                total_start = time.time()

                if not self.listen_for_wakeword():
                    break

                audio = self.listen(duration=self.command_duration)
                text = self.transcribe(audio)

                if not text:
                    self.speak("I didn't catch that, sir.")
                    continue

                response = self.get_smart_response(text)
                self.speak(response)

                total_time = int((time.time() - total_start) * 1000)
                print(f"\n⏱  TOTAL RESPONSE TIME: {total_time}ms ({total_time/1000:.1f}s)")
                print("\nReady for next command...\n")

        except KeyboardInterrupt:
            print("\n\nShutting down JARVIS...")
            self.print_stats()

if __name__ == "__main__":
    jarvis = SmartJarvis(whisper_model="large")
    jarvis.run()
