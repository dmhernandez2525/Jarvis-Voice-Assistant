#!/usr/bin/env python3
"""
PersonaPlex WebSocket Client
Provides full-duplex communication with PersonaPlex server for
natural conversation with <500ms latency.

Features:
- Bidirectional audio streaming
- Real-time transcription
- Back-channeling support
- Persona configuration
"""

import asyncio
import json
import logging
from typing import Optional, Callable, Any
from dataclasses import dataclass
import websockets
from websockets.client import WebSocketClientProtocol

logger = logging.getLogger(__name__)


@dataclass
class PersonaPlexConfig:
    """Configuration for PersonaPlex connection"""
    persona: str = "jarvis"
    voice_style: str = "professional"
    language: str = "en"
    enable_backchannel: bool = True
    response_latency_ms: int = 500


class PersonaPlexClient:
    """
    WebSocket client for PersonaPlex full-duplex AI.

    Usage:
        client = PersonaPlexClient(host="localhost", port=8998)
        await client.connect()

        # For text queries
        response = await client.send_text("Hello, how are you?")

        # For audio streaming
        client.on_audio = lambda data: play_audio(data)
        client.on_transcription = lambda text: print(f"You: {text}")
        client.on_response = lambda text: print(f"AI: {text}")
        await client.send_audio(audio_bytes)

        await client.disconnect()
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 8998,
        path: str = "/ws",
        config: Optional[PersonaPlexConfig] = None
    ):
        self.host = host
        self.port = port
        self.path = path
        self.config = config or PersonaPlexConfig()

        self._ws: Optional[WebSocketClientProtocol] = None
        self._connected = False
        self._response_queue: asyncio.Queue = asyncio.Queue()

        # Callbacks
        self.on_audio: Optional[Callable[[bytes], None]] = None
        self.on_transcription: Optional[Callable[[str], None]] = None
        self.on_response: Optional[Callable[[str], None]] = None
        self.on_error: Optional[Callable[[Exception], None]] = None
        self.on_state_change: Optional[Callable[[str], None]] = None

    @property
    def url(self) -> str:
        return f"ws://{self.host}:{self.port}{self.path}"

    @property
    def is_connected(self) -> bool:
        return self._connected and self._ws is not None

    async def connect(self) -> bool:
        """Connect to PersonaPlex server"""
        if self._connected:
            return True

        try:
            logger.info(f"Connecting to PersonaPlex at {self.url}")
            self._ws = await websockets.connect(
                self.url,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=5
            )
            self._connected = True

            # Send initial configuration
            await self._send_config()

            # Start message handler
            asyncio.create_task(self._message_handler())

            logger.info("Connected to PersonaPlex")
            if self.on_state_change:
                self.on_state_change("connected")

            return True

        except Exception as e:
            logger.error(f"Failed to connect to PersonaPlex: {e}")
            self._connected = False
            if self.on_error:
                self.on_error(e)
            return False

    async def disconnect(self):
        """Disconnect from PersonaPlex server"""
        if self._ws:
            self._connected = False
            await self._ws.close()
            self._ws = None
            logger.info("Disconnected from PersonaPlex")
            if self.on_state_change:
                self.on_state_change("disconnected")

    async def _send_config(self):
        """Send configuration to PersonaPlex"""
        config_msg = {
            "type": "config",
            "persona": self.config.persona,
            "voice_style": self.config.voice_style,
            "language": self.config.language,
            "enable_backchannel": self.config.enable_backchannel,
            "response_latency_ms": self.config.response_latency_ms
        }
        await self._ws.send(json.dumps(config_msg))
        logger.debug(f"Sent config: {config_msg}")

    async def _message_handler(self):
        """Handle incoming messages from PersonaPlex"""
        try:
            async for message in self._ws:
                if isinstance(message, bytes):
                    # Binary message = audio data
                    if self.on_audio:
                        self.on_audio(message)
                else:
                    # Text message = JSON
                    await self._handle_text_message(message)

        except websockets.ConnectionClosed as e:
            logger.info(f"Connection closed: {e}")
            self._connected = False
            if self.on_state_change:
                self.on_state_change("disconnected")

        except Exception as e:
            logger.error(f"Message handler error: {e}")
            if self.on_error:
                self.on_error(e)

    async def _handle_text_message(self, text: str):
        """Handle text/JSON messages"""
        try:
            data = json.loads(text)
            msg_type = data.get("type", "")

            if msg_type == "transcription":
                # User's speech transcribed
                transcription = data.get("text", "")
                logger.debug(f"Transcription: {transcription}")
                if self.on_transcription:
                    self.on_transcription(transcription)

            elif msg_type == "response":
                # AI response text
                response = data.get("text", "")
                logger.debug(f"Response: {response}")
                if self.on_response:
                    self.on_response(response)
                # Also put in queue for send_text() callers
                await self._response_queue.put(response)

            elif msg_type == "state":
                # State change (listening, processing, speaking)
                state = data.get("state", "")
                logger.debug(f"State: {state}")
                if self.on_state_change:
                    self.on_state_change(state)

            elif msg_type == "error":
                # Error message
                error = data.get("message", "Unknown error")
                logger.error(f"PersonaPlex error: {error}")
                if self.on_error:
                    self.on_error(Exception(error))

            elif msg_type == "backchannel":
                # Back-channel response (uh-huh, hmm, etc.)
                backchannel = data.get("text", "")
                logger.debug(f"Backchannel: {backchannel}")

            else:
                logger.debug(f"Unknown message type: {msg_type}")

        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON received: {text[:100]}")

    async def send_audio(self, audio_data: bytes):
        """
        Send audio data to PersonaPlex for processing.
        Audio should be 16kHz mono PCM or WAV.
        """
        if not self.is_connected:
            raise ConnectionError("Not connected to PersonaPlex")

        await self._ws.send(audio_data)

    async def send_text(self, text: str, timeout: float = 30.0) -> str:
        """
        Send text query to PersonaPlex and wait for response.

        Args:
            text: The text query
            timeout: Maximum time to wait for response

        Returns:
            The response text from PersonaPlex
        """
        if not self.is_connected:
            # Try to connect
            if not await self.connect():
                raise ConnectionError("Cannot connect to PersonaPlex")

        # Clear any pending responses
        while not self._response_queue.empty():
            try:
                self._response_queue.get_nowait()
            except asyncio.QueueEmpty:
                break

        # Send text query
        query_msg = {
            "type": "text_query",
            "text": text
        }
        await self._ws.send(json.dumps(query_msg))
        logger.debug(f"Sent text query: {text}")

        # Wait for response
        try:
            response = await asyncio.wait_for(
                self._response_queue.get(),
                timeout=timeout
            )
            return response

        except asyncio.TimeoutError:
            raise TimeoutError(f"No response from PersonaPlex within {timeout}s")

    async def set_persona(self, persona: str):
        """Change the active persona"""
        self.config.persona = persona
        if self.is_connected:
            await self._send_config()

    async def interrupt(self):
        """Interrupt current speech/processing"""
        if self.is_connected:
            interrupt_msg = {"type": "interrupt"}
            await self._ws.send(json.dumps(interrupt_msg))
            logger.debug("Sent interrupt")


class PersonaPlexStream:
    """
    Context manager for streaming audio to PersonaPlex.

    Usage:
        async with PersonaPlexStream(client) as stream:
            while recording:
                stream.write(audio_chunk)
    """

    def __init__(self, client: PersonaPlexClient):
        self.client = client
        self._active = False

    async def __aenter__(self):
        if not self.client.is_connected:
            await self.client.connect()
        self._active = True

        # Notify start of stream
        start_msg = {"type": "stream_start"}
        await self.client._ws.send(json.dumps(start_msg))
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._active = False
        # Notify end of stream
        if self.client.is_connected:
            end_msg = {"type": "stream_end"}
            await self.client._ws.send(json.dumps(end_msg))

    async def write(self, audio_data: bytes):
        """Write audio chunk to stream"""
        if self._active and self.client.is_connected:
            await self.client.send_audio(audio_data)


# Synchronous wrapper for use in non-async code
class PersonaPlexClientSync:
    """
    Synchronous wrapper for PersonaPlexClient.
    Creates its own event loop for blocking operations.
    """

    def __init__(self, **kwargs):
        self._client = PersonaPlexClient(**kwargs)
        self._loop = asyncio.new_event_loop()

    def connect(self) -> bool:
        return self._loop.run_until_complete(self._client.connect())

    def disconnect(self):
        self._loop.run_until_complete(self._client.disconnect())

    def send_text(self, text: str, timeout: float = 30.0) -> str:
        return self._loop.run_until_complete(
            self._client.send_text(text, timeout)
        )

    def send_audio(self, audio_data: bytes):
        self._loop.run_until_complete(self._client.send_audio(audio_data))

    def set_persona(self, persona: str):
        self._loop.run_until_complete(self._client.set_persona(persona))

    def __del__(self):
        self._loop.close()


# Test function
async def _test():
    """Test PersonaPlex connection"""
    client = PersonaPlexClient()

    client.on_transcription = lambda t: print(f"You: {t}")
    client.on_response = lambda r: print(f"AI: {r}")
    client.on_state_change = lambda s: print(f"State: {s}")

    if await client.connect():
        try:
            response = await client.send_text("Hello, how are you?")
            print(f"\nFinal response: {response}")
        finally:
            await client.disconnect()
    else:
        print("Failed to connect")


if __name__ == "__main__":
    asyncio.run(_test())
