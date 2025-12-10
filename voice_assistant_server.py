#!/usr/bin/env python3
"""
Voice Assistant API Server
Accepts audio from remote devices (like custom Echo replacements)
and returns audio responses
"""

from flask import Flask, request, send_file, jsonify
import whisper
import ollama
import pyttsx3
import tempfile
import os
import numpy as np
from scipy.io import wavfile
import io

app = Flask(__name__)

# Global instances (loaded once at startup)
print("Loading Whisper model...")
whisper_model = whisper.load_model("large")

print("Initializing TTS...")
tts_engine = pyttsx3.init()
tts_engine.setProperty('rate', 175)

OLLAMA_MODEL = "qwen2.5:72b"

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "model": OLLAMA_MODEL})

@app.route('/query', methods=['POST'])
def query():
    """
    Process voice query
    Expects: WAV audio file in request
    Returns: JSON with transcription and response text
    """
    try:
        # Get audio file from request
        if 'audio' not in request.files:
            return jsonify({"error": "No audio file provided"}), 400

        audio_file = request.files['audio']

        # Save temporarily
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_input = f.name
            audio_file.save(temp_input)

        # Transcribe
        print("Transcribing audio...")
        result = whisper_model.transcribe(temp_input)
        text = result["text"].strip()
        print(f"Transcribed: {text}")

        # Clean up input
        os.unlink(temp_input)

        if not text:
            return jsonify({"error": "No speech detected"}), 400

        # Get response from Ollama
        print("Getting response from Qwen...")
        response = ollama.generate(
            model=OLLAMA_MODEL,
            prompt=text,
            stream=False
        )
        answer = response['response'].strip()
        print(f"Response: {answer}")

        return jsonify({
            "transcription": text,
            "response": answer
        })

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/query_audio', methods=['POST'])
def query_audio():
    """
    Process voice query and return audio response
    Expects: WAV audio file in request
    Returns: WAV audio file with spoken response
    """
    try:
        # Get audio file from request
        if 'audio' not in request.files:
            return jsonify({"error": "No audio file provided"}), 400

        audio_file = request.files['audio']

        # Save temporarily
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_input = f.name
            audio_file.save(temp_input)

        # Transcribe
        print("Transcribing audio...")
        result = whisper_model.transcribe(temp_input)
        text = result["text"].strip()
        print(f"Transcribed: {text}")

        # Clean up input
        os.unlink(temp_input)

        if not text:
            return jsonify({"error": "No speech detected"}), 400

        # Get response from Ollama
        print("Getting response from Qwen...")
        response = ollama.generate(
            model=OLLAMA_MODEL,
            prompt=text,
            stream=False
        )
        answer = response['response'].strip()
        print(f"Response: {answer}")

        # Convert to speech
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_output = f.name

        tts_engine.save_to_file(answer, temp_output)
        tts_engine.runAndWait()

        # Return audio file
        return send_file(
            temp_output,
            mimetype='audio/wav',
            as_attachment=True,
            download_name='response.wav'
        )

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/text_query', methods=['POST'])
def text_query():
    """
    Process text query (for testing)
    Expects: JSON with 'text' field
    Returns: JSON with response
    """
    try:
        data = request.get_json()
        if not data or 'text' not in data:
            return jsonify({"error": "No text provided"}), 400

        text = data['text']
        print(f"Text query: {text}")

        # Get response from Ollama
        response = ollama.generate(
            model=OLLAMA_MODEL,
            prompt=text,
            stream=False
        )
        answer = response['response'].strip()
        print(f"Response: {answer}")

        return jsonify({"response": answer})

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("\n" + "="*60)
    print("VOICE ASSISTANT API SERVER")
    print("="*60)
    print("\nEndpoints:")
    print("  GET  /health         - Health check")
    print("  POST /query          - Audio in, JSON out (text response)")
    print("  POST /query_audio    - Audio in, audio out")
    print("  POST /text_query     - Text in, JSON out")
    print("\nStarting server on 0.0.0.0:5000...")
    print("="*60 + "\n")

    app.run(host='0.0.0.0', port=5000, debug=False)
