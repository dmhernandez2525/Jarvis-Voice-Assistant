"""
Pytest configuration and fixtures for Jarvis Voice Assistant tests.
"""

import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_whisper():
    """Mock the Whisper speech recognition model."""
    with patch("whisper.load_model") as mock_load:
        mock_model = MagicMock()
        mock_model.transcribe.return_value = {
            "text": "Hello, how can I help you?",
            "segments": [],
            "language": "en",
        }
        mock_load.return_value = mock_model
        yield mock_model


@pytest.fixture
def mock_ollama():
    """Mock the Ollama LLM client."""
    with patch("ollama.chat") as mock_chat:
        mock_chat.return_value = {
            "message": {
                "content": "I'm doing well, thank you for asking!",
                "role": "assistant",
            }
        }
        yield mock_chat


@pytest.fixture
def mock_pyttsx3():
    """Mock the pyttsx3 TTS engine."""
    with patch("pyttsx3.init") as mock_init:
        mock_engine = MagicMock()
        mock_engine.getProperty.return_value = 175
        mock_init.return_value = mock_engine
        yield mock_engine


@pytest.fixture
def mock_audio():
    """Mock audio input/output devices."""
    with patch("sounddevice.rec") as mock_rec, patch(
        "sounddevice.wait"
    ) as mock_wait:
        import numpy as np

        mock_rec.return_value = np.zeros((16000 * 5, 1), dtype=np.float32)
        yield {"rec": mock_rec, "wait": mock_wait}


@pytest.fixture
def sample_audio_data():
    """Generate sample audio data for testing."""
    import numpy as np

    # 5 seconds of silence at 16kHz
    return np.zeros((16000 * 5, 1), dtype=np.float32)


@pytest.fixture
def sample_transcription():
    """Sample transcription result."""
    return {
        "text": "What is the weather like today?",
        "segments": [
            {
                "id": 0,
                "seek": 0,
                "start": 0.0,
                "end": 2.5,
                "text": " What is the weather like today?",
                "tokens": [50364, 708, 307, 264, 5765, 411, 965, 30, 50489],
                "temperature": 0.0,
                "avg_logprob": -0.25,
                "compression_ratio": 1.0,
                "no_speech_prob": 0.1,
            }
        ],
        "language": "en",
    }


@pytest.fixture
def sample_llm_response():
    """Sample LLM response."""
    return {
        "message": {
            "content": "I don't have access to real-time weather data, but you can check a weather app or website for the current conditions in your area.",
            "role": "assistant",
        },
        "done": True,
        "total_duration": 1500000000,
        "load_duration": 100000000,
        "prompt_eval_count": 15,
        "prompt_eval_duration": 200000000,
        "eval_count": 30,
        "eval_duration": 1200000000,
    }
