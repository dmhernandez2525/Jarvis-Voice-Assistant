#!/usr/bin/env python3
"""
PersonaPlex Proxy Server (MLX Version with Smart Routing)

Features:
- Moshi MLX for real-time voice conversation
- Smart routing to Ollama for complex queries
- Voice activity detection for better UI feedback
- Streaming text responses

Ports:
- 8999: Proxy (Swift app connects here)
- 8998: Moshi MLX
- 11434: Ollama (for complex queries)
"""

import asyncio
import json
import logging
import time
import numpy as np
from typing import Optional
from dataclasses import dataclass
import aiohttp
from aiohttp import web, WSMsgType

# sphn library from Kyutai (same as moshi uses)
try:
    import sphn
    SPHN_AVAILABLE = True
except ImportError:
    SPHN_AVAILABLE = False
    print("WARNING: sphn not available")

# Import smart router
from smart_router import SmartRouter, QueryComplexity

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
PROXY_PORT = 8999
MOSHI_HOST = "localhost"
MOSHI_PORT = 8998
OLLAMA_HOST = "localhost"
OLLAMA_PORT = 11434
MOSHI_SAMPLE_RATE = 24000
APP_SAMPLE_RATE = 16000
MOSHI_FRAME_SIZE = 1920

# Voice activity detection thresholds
VAD_THRESHOLD = 0.02  # RMS threshold for speech detection
VAD_SILENCE_DURATION = 0.8  # Seconds of silence to consider end of speech


@dataclass
class ConversationState:
    """Track conversation state for better UX."""
    user_speaking: bool = False
    assistant_speaking: bool = False
    last_user_audio_time: float = 0
    last_assistant_audio_time: float = 0
    pending_user_text: str = ""  # Accumulated user speech (if we had transcription)
    pending_assistant_text: str = ""
    current_query_routed: bool = False  # True if current query went to Ollama


class MoshiMLXProxy:
    """Proxy server with smart routing between Moshi and Ollama."""

    def __init__(self):
        self.router = SmartRouter(OLLAMA_HOST, OLLAMA_PORT)
        self.ollama_model = "deepseek-r1:8b"

    async def handle_websocket(self, request):
        """Handle WebSocket connection from Swift app."""
        ws_app = web.WebSocketResponse()
        await ws_app.prepare(request)

        connection_id = id(ws_app)
        logger.info(f"New connection from app: {connection_id}")

        # Check Ollama availability
        ollama_available = await self.router.check_ollama()
        logger.info(f"Ollama available: {ollama_available}")

        moshi_url = f"ws://{MOSHI_HOST}:{MOSHI_PORT}/api/chat"
        state = ConversationState()

        try:
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(moshi_url, timeout=aiohttp.ClientTimeout(total=60)) as ws_moshi:
                    logger.info(f"Connected to moshi MLX for {connection_id}")

                    # Wait for handshake from moshi
                    handshake_msg = await ws_moshi.receive()
                    if handshake_msg.type == WSMsgType.BINARY and handshake_msg.data[0:1] == b'\x00':
                        logger.info("Received handshake from moshi")

                    # Send initial state to app
                    await ws_app.send_json({
                        "type": "state",
                        "state": "connected",
                        "ollama_available": ollama_available
                    })

                    # Create sphn encoder/decoder
                    opus_writer = sphn.OpusStreamWriter(MOSHI_SAMPLE_RATE)
                    opus_reader = sphn.OpusStreamReader(MOSHI_SAMPLE_RATE)

                    # Bidirectional forwarding with state tracking
                    app_to_moshi = asyncio.create_task(
                        self._forward_app_to_moshi(ws_app, ws_moshi, opus_writer, state, connection_id)
                    )
                    moshi_to_app = asyncio.create_task(
                        self._forward_moshi_to_app(ws_moshi, ws_app, opus_reader, state, connection_id)
                    )

                    done, pending = await asyncio.wait(
                        [app_to_moshi, moshi_to_app],
                        return_when=asyncio.FIRST_COMPLETED
                    )

                    for task in pending:
                        task.cancel()
                        try:
                            await task
                        except asyncio.CancelledError:
                            pass

        except aiohttp.ClientError as e:
            logger.error(f"Failed to connect to moshi: {e}")
            await ws_app.send_json({"type": "error", "message": f"Cannot connect to Moshi: {e}"})
        except Exception as e:
            logger.error(f"Proxy error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            logger.info(f"Connection closed: {connection_id}")

        return ws_app

    async def _forward_app_to_moshi(self, ws_app, ws_moshi, opus_writer, state: ConversationState, connection_id):
        """Forward audio from app to moshi with voice activity detection."""
        audio_buffer = np.array([], dtype=np.float32)
        chunk_count = 0
        forward_count = 0
        last_vad_state = False
        last_state_update = 0

        try:
            async for msg in ws_app:
                if msg.type == WSMsgType.BINARY:
                    new_data = np.frombuffer(msg.data, dtype=np.float32)

                    # Voice Activity Detection
                    rms = np.sqrt(np.mean(new_data ** 2))
                    is_speech = rms > VAD_THRESHOLD
                    current_time = time.time()

                    if is_speech:
                        state.user_speaking = True
                        state.last_user_audio_time = current_time
                    elif state.user_speaking and (current_time - state.last_user_audio_time) > VAD_SILENCE_DURATION:
                        state.user_speaking = False

                    # Send state update to app (throttled to avoid spam)
                    if is_speech != last_vad_state or (current_time - last_state_update) > 0.5:
                        if state.user_speaking and not state.assistant_speaking:
                            await ws_app.send_json({
                                "type": "state",
                                "state": "user_speaking",
                                "detail": "Listening to you..."
                            })
                        last_vad_state = is_speech
                        last_state_update = current_time

                    # Resample and buffer
                    resampled = sphn.resample(new_data, APP_SAMPLE_RATE, MOSHI_SAMPLE_RATE)
                    audio_buffer = np.concatenate([audio_buffer, resampled])

                    chunk_count += 1
                    if chunk_count % 100 == 0:
                        logger.info(f"Audio chunks: {chunk_count}, VAD: {'speech' if is_speech else 'silence'}")

                    # Process in frames
                    while len(audio_buffer) >= MOSHI_FRAME_SIZE:
                        chunk = audio_buffer[:MOSHI_FRAME_SIZE]
                        audio_buffer = audio_buffer[MOSHI_FRAME_SIZE:]

                        opus_data = opus_writer.append_pcm(chunk)
                        if len(opus_data) > 0:
                            await ws_moshi.send_bytes(b'\x01' + opus_data)
                            forward_count += 1

                elif msg.type == WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        if data.get("type") == "interrupt":
                            logger.info("Interrupt requested")
                    except json.JSONDecodeError:
                        pass

                elif msg.type in (WSMsgType.CLOSE, WSMsgType.ERROR):
                    break

        except Exception as e:
            logger.error(f"Error forwarding to moshi: {e}")
            import traceback
            traceback.print_exc()
            raise

    async def _forward_moshi_to_app(self, ws_moshi, ws_app, opus_reader, state: ConversationState, connection_id):
        """Forward responses from moshi to app with smart routing."""
        text_buffer = ""
        sentence_buffer = ""  # For routing decisions
        audio_count = 0
        text_count = 0
        last_text_time = 0
        routing_pending = False

        logger.info(f"Starting moshi->app forwarding for {connection_id}")

        try:
            async for msg in ws_moshi:
                if msg.type == WSMsgType.BINARY:
                    data = msg.data
                    if len(data) < 1:
                        continue

                    kind = data[0]
                    payload = data[1:]

                    if kind == 1:  # Audio
                        audio_count += 1
                        current_time = time.time()

                        if audio_count == 1:
                            logger.info("First audio response from moshi!")
                            state.assistant_speaking = True
                            await ws_app.send_json({
                                "type": "state",
                                "state": "assistant_speaking",
                                "detail": "Responding..."
                            })

                        state.last_assistant_audio_time = current_time

                        if len(payload) > 0:
                            pcm = opus_reader.append_bytes(payload)
                            if pcm.shape[-1] > 0:
                                resampled = sphn.resample(pcm, MOSHI_SAMPLE_RATE, APP_SAMPLE_RATE)
                                await ws_app.send_bytes(resampled.astype(np.float32).tobytes())

                        # Detect end of speech (silence)
                        if audio_count > 10 and (current_time - state.last_assistant_audio_time) > 0.3:
                            state.assistant_speaking = False

                    elif kind == 2:  # Text
                        text = payload.decode('utf-8', errors='ignore')
                        current_time = time.time()

                        if text and text != '\x00':
                            text_buffer += text
                            sentence_buffer += text
                            text_count += 1
                            last_text_time = current_time

                            # Send partial response
                            await ws_app.send_json({
                                "type": "response",
                                "text": text,
                                "partial": True,
                                "source": "moshi"
                            })

                            # Check for sentence completion (for routing)
                            if text.rstrip().endswith(('.', '?', '!', '\n')):
                                # Complete sentence - check if we should route to Ollama
                                complete_sentence = sentence_buffer.strip()
                                logger.info(f"Complete sentence: '{complete_sentence[:50]}...'")

                                # Route decision (but don't wait - Moshi keeps going)
                                if self.router.ollama_available and not routing_pending:
                                    decision = self.router.classify_fast(complete_sentence)
                                    if decision.complexity == QueryComplexity.COMPLEX:
                                        logger.info(f"Routing to Ollama: {decision.reason}")
                                        routing_pending = True
                                        # Start Ollama query in background
                                        asyncio.create_task(
                                            self._handle_ollama_query(ws_app, complete_sentence, state)
                                        )

                                # Send complete response marker
                                await ws_app.send_json({
                                    "type": "response",
                                    "text": text_buffer.strip(),
                                    "partial": False,
                                    "source": "moshi"
                                })
                                text_buffer = ""
                                sentence_buffer = ""

                    elif kind == 0:
                        pass  # Handshake

                elif msg.type in (WSMsgType.CLOSE, WSMsgType.ERROR):
                    logger.info(f"Moshi connection closed: {msg.type}")
                    break

        except Exception as e:
            logger.error(f"Error forwarding from moshi: {e}")
            import traceback
            traceback.print_exc()
            raise

    async def _handle_ollama_query(self, ws_app, query: str, state: ConversationState):
        """Handle a query that was routed to Ollama."""
        logger.info(f"Querying Ollama with: {query[:100]}...")

        # Notify app that we're using Ollama
        await ws_app.send_json({
            "type": "state",
            "state": "thinking",
            "detail": "Thinking deeply...",
            "source": "ollama"
        })

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"http://{OLLAMA_HOST}:{OLLAMA_PORT}/api/generate",
                    json={
                        "model": self.ollama_model,
                        "prompt": query,
                        "stream": True
                    },
                    timeout=aiohttp.ClientTimeout(total=120)
                ) as resp:
                    full_response = ""
                    async for line in resp.content:
                        if line:
                            try:
                                data = json.loads(line)
                                token = data.get("response", "")
                                if token:
                                    full_response += token
                                    # Send streaming response from Ollama
                                    await ws_app.send_json({
                                        "type": "response",
                                        "text": token,
                                        "partial": True,
                                        "source": "ollama"
                                    })
                                if data.get("done", False):
                                    break
                            except json.JSONDecodeError:
                                continue

                    # Send complete response
                    if full_response:
                        await ws_app.send_json({
                            "type": "response",
                            "text": full_response,
                            "partial": False,
                            "source": "ollama"
                        })

                        # TODO: Send to TTS for speech output
                        logger.info(f"Ollama response complete: {len(full_response)} chars")

        except Exception as e:
            logger.error(f"Ollama query failed: {e}")
            await ws_app.send_json({
                "type": "error",
                "message": f"Ollama error: {e}"
            })

        state.current_query_routed = False


async def main():
    """Start the proxy server."""
    if not SPHN_AVAILABLE:
        logger.error("sphn library not available! Install moshi_mlx package.")
        return

    proxy = MoshiMLXProxy()

    # Check Ollama on startup
    ollama_ok = await proxy.router.check_ollama()
    logger.info(f"Ollama status: {'available' if ollama_ok else 'not available'}")

    app = web.Application()
    app.router.add_get('/ws', proxy.handle_websocket)
    app.router.add_get('/health', lambda r: web.Response(text='OK'))

    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner, '0.0.0.0', PROXY_PORT)
    await site.start()

    logger.info(f"Smart Proxy running on port {PROXY_PORT}")
    logger.info(f"  → Moshi MLX at {MOSHI_HOST}:{MOSHI_PORT}")
    logger.info(f"  → Ollama at {OLLAMA_HOST}:{OLLAMA_PORT} ({'available' if ollama_ok else 'unavailable'})")
    logger.info(f"  → Using sphn for OGG/Opus: {SPHN_AVAILABLE}")

    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    asyncio.run(main())
