#!/usr/bin/env python3
"""
Jarvis Orchestrator - Central Routing Server
Routes queries between PersonaPlex, VoiceForge, and Ollama

Endpoints:
- GET  /health              - Health check with service status
- POST /query               - Process audio query
- POST /text_query          - Process text query
- POST /mode                - Set conversation mode
- GET  /status              - Get full system status

Conversation Modes:
- full_duplex: PersonaPlex only (<500ms latency)
- hybrid: Smart routing between PersonaPlex and Ollama
- legacy: Traditional STT -> LLM -> TTS pipeline
"""

import os
import sys
import json
import time
import yaml
import asyncio
import tempfile
import logging
from pathlib import Path
from typing import Optional, Dict, Any

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import whisper
import ollama
import httpx

# Import local modules
from personaplex_client import PersonaPlexClient
from voiceforge_tts import VoiceForgeTTS

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Security: Limit request size to 50MB for audio uploads
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50 MB

# Security: Configure CORS for local development only
# In production, specify allowed origins
ALLOWED_ORIGINS = os.environ.get("CORS_ORIGINS", "http://localhost:*,http://127.0.0.1:*")
CORS(app, origins=ALLOWED_ORIGINS.split(",") if ALLOWED_ORIGINS != "*" else "*")

# Load configuration
CONFIG_PATH = Path(__file__).parent / "config" / "jarvis.yaml"
with open(CONFIG_PATH) as f:
    config = yaml.safe_load(f)

# Global state
current_mode = config['defaults']['mode']
whisper_model = None
personaplex_client = None
voiceforge_client = None

# Model configuration
MODELS = config['models']


def load_whisper():
    """Load Whisper model for speech-to-text"""
    global whisper_model
    if whisper_model is None:
        model_name = config['whisper']['model']
        logger.info(f"Loading Whisper model: {model_name}")
        start = time.time()
        whisper_model = whisper.load_model(model_name)
        logger.info(f"Whisper loaded in {time.time() - start:.2f}s")
    return whisper_model


def get_personaplex_client():
    """Get or create PersonaPlex client"""
    global personaplex_client
    if personaplex_client is None:
        pp_config = config['servers']['personaplex']
        personaplex_client = PersonaPlexClient(
            host=pp_config['host'],
            port=pp_config['port'],
            path=pp_config['websocket_path']
        )
    return personaplex_client


def get_voiceforge_client():
    """Get or create VoiceForge client"""
    global voiceforge_client
    if voiceforge_client is None:
        vf_config = config['servers']['voiceforge']
        voiceforge_client = VoiceForgeTTS(
            host=vf_config['host'],
            port=vf_config['port']
        )
    return voiceforge_client


def analyze_query_complexity(text: str) -> str:
    """
    Use fast router model to analyze query complexity.
    Returns: 'simple', 'moderate', or 'complex'
    """
    logger.info("Analyzing query complexity...")
    start = time.time()

    analysis_prompt = f"""Analyze this query and classify its complexity. Respond with ONLY ONE WORD:

SIMPLE - Basic facts, greetings, simple questions, jokes, casual chat
MODERATE - Explanations, comparisons, creative writing, code generation
COMPLEX - Deep analysis, multi-step reasoning, philosophical questions, complex technical tasks

Query: "{text}"

Classification:"""

    try:
        response = ollama.generate(
            model=MODELS['router'],
            prompt=analysis_prompt,
            stream=False,
            options={"temperature": 0.3}
        )

        classification = response['response'].strip().upper()

        if "SIMPLE" in classification:
            complexity = "simple"
        elif "MODERATE" in classification:
            complexity = "moderate"
        else:
            complexity = "complex"

        logger.info(f"Complexity: {complexity} (analyzed in {(time.time() - start)*1000:.0f}ms)")
        return complexity

    except Exception as e:
        logger.error(f"Error analyzing complexity: {e}")
        return "moderate"  # Default to moderate on error


def route_query(text: str, complexity: str) -> str:
    """Route query to appropriate model based on complexity"""

    if current_mode == "full_duplex":
        # PersonaPlex handles everything in full duplex mode
        return "personaplex"

    elif current_mode == "hybrid":
        # Smart routing based on complexity
        if complexity == "simple":
            # Simple queries can go to PersonaPlex for speed
            return "personaplex"
        else:
            # Complex queries go to Ollama
            return "ollama"

    else:  # legacy mode
        return "ollama"


def get_ollama_response(text: str, complexity: str) -> str:
    """Get response from Ollama based on complexity"""

    # Select model based on complexity
    if complexity == "simple":
        model = MODELS['fast']
    elif complexity == "moderate":
        model = MODELS['balanced']
    else:
        model = MODELS['powerful']

    logger.info(f"Using Ollama model: {model}")
    start = time.time()

    # Build prompt
    if "dolphin" in model.lower():
        prompt = text
    else:
        prompt = f"""You are JARVIS, a helpful AI assistant. Be direct and conversational.

User: {text}
JARVIS:"""

    response = ollama.generate(
        model=model,
        prompt=prompt,
        stream=False,
        options={
            "temperature": 0.8,
            "top_p": 0.9
        }
    )

    answer = response['response'].strip()
    logger.info(f"Ollama response in {(time.time() - start)*1000:.0f}ms")
    return answer


async def check_service_health(url: str, timeout: float = 2.0) -> bool:
    """Check if a service is healthy"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=timeout)
            return response.status_code == 200
    except Exception:
        return False


# Flask Routes

@app.route('/health', methods=['GET'])
def health():
    """Health check with service status"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    ollama_url = f"http://{config['servers']['ollama']['host']}:{config['servers']['ollama']['port']}/api/tags"
    voiceforge_url = f"http://{config['servers']['voiceforge']['host']}:{config['servers']['voiceforge']['port']}/health"
    personaplex_url = f"http://{config['servers']['personaplex']['host']}:{config['servers']['personaplex']['port']}/health"

    try:
        ollama_ok = loop.run_until_complete(check_service_health(ollama_url))
        voiceforge_ok = loop.run_until_complete(check_service_health(voiceforge_url))
        personaplex_ok = loop.run_until_complete(check_service_health(personaplex_url))
    finally:
        loop.close()

    return jsonify({
        "status": "ok",
        "mode": current_mode,
        "whisper_model": config['whisper']['model'],
        "ollama_connected": ollama_ok,
        "voiceforge_connected": voiceforge_ok,
        "personaplex_connected": personaplex_ok,
    })


@app.route('/status', methods=['GET'])
def status():
    """Get full system status"""
    return jsonify({
        "mode": current_mode,
        "available_modes": list(config['modes'].keys()),
        "models": MODELS,
        "whisper_loaded": whisper_model is not None,
        "servers": config['servers'],
    })


@app.route('/mode', methods=['GET', 'POST'])
def mode():
    """Get or set conversation mode"""
    global current_mode

    if request.method == 'GET':
        return jsonify({
            "mode": current_mode,
            "available": list(config['modes'].keys()),
            "description": config['modes'][current_mode]['description']
        })

    # POST - set mode
    data = request.get_json()
    if not data or 'mode' not in data:
        return jsonify({"error": "Mode not specified"}), 400

    new_mode = data['mode']
    if new_mode not in config['modes']:
        return jsonify({"error": f"Invalid mode. Available: {list(config['modes'].keys())}"}), 400

    current_mode = new_mode
    logger.info(f"Mode changed to: {current_mode}")
    return jsonify({
        "status": "ok",
        "mode": current_mode,
        "description": config['modes'][current_mode]['description']
    })


def validate_wav_header(data: bytes) -> bool:
    """Validate that data starts with a WAV file header."""
    if len(data) < 12:
        return False
    # WAV files start with "RIFF" and contain "WAVE"
    return data[:4] == b'RIFF' and data[8:12] == b'WAVE'


@app.route('/query', methods=['POST'])
def query():
    """
    Process audio query.
    Expects: WAV audio file in request
    Returns: JSON with transcription, response, and routing info
    """
    total_start = time.time()

    # Get audio file
    if 'audio' not in request.files:
        # Check if raw audio data in body
        if request.content_type == 'audio/wav':
            audio_data = request.data
        else:
            return jsonify({"error": "No audio provided"}), 400
    else:
        audio_data = request.files['audio'].read()

    # Security: Validate audio data
    if not audio_data:
        return jsonify({"error": "Empty audio data"}), 400

    if len(audio_data) < 44:  # Minimum WAV header size
        return jsonify({"error": "Audio data too small"}), 400

    if not validate_wav_header(audio_data):
        return jsonify({"error": "Invalid audio format - expected WAV"}), 400

    # Save temporarily for Whisper
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False, mode='wb') as f:
        temp_path = f.name
        f.write(audio_data)

    try:
        # Transcribe
        logger.info("Transcribing audio...")
        stt_start = time.time()
        model = load_whisper()
        result = model.transcribe(temp_path)
        text = result["text"].strip()
        stt_time = time.time() - stt_start
        logger.info(f"Transcribed in {stt_time*1000:.0f}ms: {text}")

        if not text:
            return jsonify({"error": "No speech detected"}), 400

        # Analyze complexity and route
        complexity = analyze_query_complexity(text)
        backend = route_query(text, complexity)

        # Get response
        llm_start = time.time()
        if backend == "personaplex":
            # Use PersonaPlex for full duplex
            try:
                client = get_personaplex_client()
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                response_text = loop.run_until_complete(client.send_text(text))
                loop.close()
            except Exception as e:
                logger.warning(f"PersonaPlex failed, falling back to Ollama: {e}")
                response_text = get_ollama_response(text, complexity)
                backend = "ollama_fallback"
        else:
            response_text = get_ollama_response(text, complexity)

        llm_time = time.time() - llm_start

        total_time = time.time() - total_start

        return jsonify({
            "transcription": text,
            "response": response_text,
            "processing_time": total_time,
            "routed_to": backend,
            "complexity": complexity,
            "timings": {
                "stt_ms": int(stt_time * 1000),
                "llm_ms": int(llm_time * 1000),
                "total_ms": int(total_time * 1000)
            }
        })

    finally:
        os.unlink(temp_path)


@app.route('/text_query', methods=['POST'])
def text_query():
    """
    Process text query (for testing).
    Expects: JSON with 'text' field
    Returns: JSON with response
    """
    data = request.get_json()
    if not data or 'text' not in data:
        return jsonify({"error": "No text provided"}), 400

    text = data['text']
    logger.info(f"Text query: {text}")

    total_start = time.time()

    # Analyze and route
    complexity = analyze_query_complexity(text)
    backend = route_query(text, complexity)

    # Get response
    llm_start = time.time()
    if backend == "personaplex":
        try:
            client = get_personaplex_client()
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            response_text = loop.run_until_complete(client.send_text(text))
            loop.close()
        except Exception as e:
            logger.warning(f"PersonaPlex failed, falling back to Ollama: {e}")
            response_text = get_ollama_response(text, complexity)
            backend = "ollama_fallback"
    else:
        response_text = get_ollama_response(text, complexity)

    llm_time = time.time() - llm_start
    total_time = time.time() - total_start

    return jsonify({
        "transcription": text,
        "response": response_text,
        "processing_time": total_time,
        "routed_to": backend,
        "complexity": complexity,
        "timings": {
            "llm_ms": int(llm_time * 1000),
            "total_ms": int(total_time * 1000)
        }
    })


@app.route('/tts', methods=['POST'])
def tts():
    """
    Generate speech from text using VoiceForge.
    Expects: JSON with 'text' field, optional 'speaker', 'language', 'voice_profile'
    Returns: Audio file path or stream
    """
    data = request.get_json()
    if not data or 'text' not in data:
        return jsonify({"error": "No text provided"}), 400

    text = data['text']
    speaker = data.get('speaker', config['defaults']['tts_speaker'])
    language = data.get('language', config['defaults']['tts_language'])
    voice_profile = data.get('voice_profile')

    try:
        client = get_voiceforge_client()

        if voice_profile:
            # Use voice cloning
            output_path = client.generate_cloned(
                text=text,
                profile_path=voice_profile,
                language=language
            )
        else:
            # Use preset speaker
            output_path = client.generate_custom(
                text=text,
                speaker=speaker,
                language=language
            )

        return jsonify({
            "status": "success",
            "output_path": output_path
        })

    except ValueError as e:
        # Path validation errors are safe to show
        logger.warning(f"TTS validation error: {e}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        # Log full error but return generic message
        logger.error(f"TTS error: {e}", exc_info=True)
        return jsonify({"error": "Failed to generate speech"}), 500


def main():
    """Start the orchestrator server"""
    print("\n" + "=" * 60)
    print("JARVIS ORCHESTRATOR SERVER")
    print("=" * 60)
    print(f"\nMode: {current_mode}")
    print(f"Whisper: {config['whisper']['model']}")
    print(f"\nModels:")
    print(f"  Router:   {MODELS['router']}")
    print(f"  Fast:     {MODELS['fast']}")
    print(f"  Balanced: {MODELS['balanced']}")
    print(f"  Powerful: {MODELS['powerful']}")
    print(f"\nEndpoints:")
    print(f"  GET  /health      - Health check with service status")
    print(f"  GET  /status      - Full system status")
    print(f"  GET  /mode        - Get current mode")
    print(f"  POST /mode        - Set conversation mode")
    print(f"  POST /query       - Process audio query")
    print(f"  POST /text_query  - Process text query")
    print(f"  POST /tts         - Generate speech")
    print(f"\nStarting on 0.0.0.0:{config['servers']['orchestrator']['port']}...")
    print("=" * 60 + "\n")

    # Preload Whisper
    load_whisper()

    app.run(
        host='0.0.0.0',
        port=config['servers']['orchestrator']['port'],
        debug=False
    )


if __name__ == '__main__':
    main()
