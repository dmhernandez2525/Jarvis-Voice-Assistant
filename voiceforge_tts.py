#!/usr/bin/env python3
"""
VoiceForge TTS Client
Provides text-to-speech using VoiceForge server with voice cloning support.

Features:
- Custom preset voices (Ryan, Aiden, etc.)
- Voice cloning from reference audio
- Voice design from text description
- Multiple language support
"""

import os
import json
import logging
import base64
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
import httpx

logger = logging.getLogger(__name__)

# Security: Allowed directories for voice profile audio files
# Can be overridden via VOICEFORGE_ALLOWED_DIRS environment variable
DEFAULT_ALLOWED_DIRS = [
    Path.home() / "voice_profiles",
    Path.home() / "Desktop" / "Projects" / "PersonalProjects" / "jarvis-voice-assistant" / "voice_profiles",
]

def get_allowed_dirs() -> List[Path]:
    """Get list of allowed directories for voice profile audio files."""
    env_dirs = os.environ.get("VOICEFORGE_ALLOWED_DIRS")
    if env_dirs:
        return [Path(d.strip()).resolve() for d in env_dirs.split(":") if d.strip()]
    return [d.resolve() for d in DEFAULT_ALLOWED_DIRS]

def validate_audio_path(path: str) -> Path:
    """
    Validate that an audio file path is within allowed directories.
    Raises ValueError if path is outside allowed directories.
    """
    resolved_path = Path(path).resolve()
    allowed_dirs = get_allowed_dirs()

    for allowed_dir in allowed_dirs:
        try:
            resolved_path.relative_to(allowed_dir)
            return resolved_path
        except ValueError:
            continue

    raise ValueError(
        f"Audio file path '{path}' is not within allowed directories. "
        f"Allowed: {[str(d) for d in allowed_dirs]}"
    )


@dataclass
class VoiceProfile:
    """Voice profile for cloning"""
    name: str
    reference_audio_path: str
    reference_text: str
    language: str = "English"


class VoiceForgeTTS:
    """
    Client for VoiceForge TTS server.

    Usage:
        client = VoiceForgeTTS()

        # Using preset voice
        output = client.generate_custom("Hello world", speaker="Ryan")

        # Using voice cloning
        profile = VoiceProfile(
            name="daniel",
            reference_audio_path="/path/to/sample.wav",
            reference_text="This is a sample of my voice."
        )
        output = client.generate_cloned("Hello world", profile=profile)

        # Using voice design
        output = client.generate_designed(
            "Hello world",
            description="A friendly male voice with a slight British accent"
        )
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 8765,
        timeout: float = 60.0
    ):
        self.host = host
        self.port = port
        self.timeout = timeout
        self._profiles: Dict[str, VoiceProfile] = {}

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    def check_health(self) -> Dict[str, Any]:
        """Check VoiceForge server health"""
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(f"{self.base_url}/health")
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {"status": "error", "message": str(e)}

    def is_available(self) -> bool:
        """Check if VoiceForge server is available"""
        health = self.check_health()
        return health.get("status") == "ok"

    def get_speakers(self) -> List[Dict[str, str]]:
        """Get list of available preset speakers"""
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(f"{self.base_url}/speakers")
                response.raise_for_status()
                return response.json().get("speakers", [])
        except Exception as e:
            logger.error(f"Failed to get speakers: {e}")
            return []

    def get_languages(self) -> List[str]:
        """Get list of supported languages"""
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(f"{self.base_url}/languages")
                response.raise_for_status()
                return response.json().get("languages", [])
        except Exception as e:
            logger.error(f"Failed to get languages: {e}")
            return []

    def load_model(self, model_type: str = "clone") -> bool:
        """
        Preload a model.

        Args:
            model_type: 'clone', 'custom', or 'design'

        Returns:
            True if successful
        """
        try:
            with httpx.Client(timeout=120.0) as client:
                response = client.post(
                    f"{self.base_url}/load",
                    json={"model": model_type}
                )
                response.raise_for_status()
                logger.info(f"Loaded model: {model_type}")
                return True
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            return False

    def generate_custom(
        self,
        text: str,
        speaker: str = "Ryan",
        language: str = "English",
        instruct: Optional[str] = None
    ) -> str:
        """
        Generate speech using a preset voice.

        Args:
            text: Text to speak
            speaker: Preset speaker name (Ryan, Aiden, etc.)
            language: Language for speech
            instruct: Optional style instructions

        Returns:
            Path to generated audio file
        """
        logger.info(f"Generating custom voice: {speaker}")

        body = {
            "text": text,
            "speaker": speaker,
            "language": language
        }
        if instruct:
            body["instruct"] = instruct

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.base_url}/generate/custom",
                    json=body
                )
                response.raise_for_status()
                result = response.json()

                if result.get("status") == "success":
                    output_path = result.get("output_path")
                    logger.info(f"Generated: {output_path}")
                    return output_path
                else:
                    raise Exception(result.get("error", "Generation failed"))

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            raise

    def generate_cloned(
        self,
        text: str,
        profile: Optional[VoiceProfile] = None,
        profile_name: Optional[str] = None,
        profile_path: Optional[str] = None,
        reference_text: Optional[str] = None,
        language: str = "English"
    ) -> str:
        """
        Generate speech using voice cloning.

        Args:
            text: Text to speak
            profile: VoiceProfile object
            profile_name: Name of saved profile
            profile_path: Direct path to reference audio
            reference_text: Text spoken in reference audio
            language: Language for speech

        Returns:
            Path to generated audio file
        """
        # Resolve profile
        if profile_name and profile_name in self._profiles:
            profile = self._profiles[profile_name]

        if profile:
            ref_audio = profile.reference_audio_path
            ref_text = profile.reference_text
            language = profile.language
        elif profile_path:
            ref_audio = profile_path
            ref_text = reference_text or ""
        else:
            raise ValueError("Must provide profile, profile_name, or profile_path")

        logger.info(f"Generating cloned voice from: {ref_audio}")

        # Security: Validate path is within allowed directories
        ref_audio_path = validate_audio_path(ref_audio)
        if not ref_audio_path.exists():
            raise FileNotFoundError(f"Reference audio not found: {ref_audio}")

        body = {
            "text": text,
            "language": language,
            "ref_audio_path": str(ref_audio_path.absolute()),
            "ref_text": ref_text
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.base_url}/generate/clone",
                    json=body
                )
                response.raise_for_status()
                result = response.json()

                if result.get("status") == "success":
                    output_path = result.get("output_path")
                    logger.info(f"Generated: {output_path}")
                    return output_path
                else:
                    raise Exception(result.get("error", "Generation failed"))

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            raise

    def generate_designed(
        self,
        text: str,
        description: str,
        language: str = "English"
    ) -> str:
        """
        Generate speech with a designed voice from text description.

        Args:
            text: Text to speak
            description: Description of desired voice
            language: Language for speech

        Returns:
            Path to generated audio file
        """
        logger.info(f"Generating designed voice: {description[:50]}...")

        body = {
            "text": text,
            "language": language,
            "instruct": description
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.base_url}/generate/design",
                    json=body
                )
                response.raise_for_status()
                result = response.json()

                if result.get("status") == "success":
                    output_path = result.get("output_path")
                    logger.info(f"Generated: {output_path}")
                    return output_path
                else:
                    raise Exception(result.get("error", "Generation failed"))

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            raise

    # Voice Profile Management

    def register_profile(self, profile: VoiceProfile):
        """Register a voice profile for easy reuse"""
        self._profiles[profile.name] = profile
        logger.info(f"Registered voice profile: {profile.name}")

    def load_profiles_from_directory(self, directory: str):
        """
        Load voice profiles from a directory.
        Expects JSON files with profile configuration.
        """
        profile_dir = Path(directory)
        if not profile_dir.exists():
            logger.warning(f"Profile directory not found: {directory}")
            return

        for profile_file in profile_dir.glob("*.json"):
            try:
                with open(profile_file) as f:
                    data = json.load(f)

                    # Security: Validate the audio path is within allowed directories
                    audio_path = data.get("reference_audio_path", "")
                    try:
                        validate_audio_path(audio_path)
                    except ValueError as ve:
                        logger.warning(f"Skipping profile {profile_file}: {ve}")
                        continue

                    profile = VoiceProfile(
                        name=data["name"],
                        reference_audio_path=audio_path,
                        reference_text=data.get("reference_text", ""),
                        language=data.get("language", "English")
                    )
                    self.register_profile(profile)
            except Exception as e:
                logger.error(f"Failed to load profile {profile_file}: {e}")

    def save_profile(self, profile: VoiceProfile, directory: str):
        """Save a voice profile to file"""
        profile_dir = Path(directory)
        profile_dir.mkdir(parents=True, exist_ok=True)

        profile_file = profile_dir / f"{profile.name}.json"
        data = {
            "name": profile.name,
            "reference_audio_path": profile.reference_audio_path,
            "reference_text": profile.reference_text,
            "language": profile.language
        }

        with open(profile_file, "w") as f:
            json.dump(data, f, indent=2)

        logger.info(f"Saved profile: {profile_file}")

    def list_profiles(self) -> List[str]:
        """List registered profile names"""
        return list(self._profiles.keys())

    def get_profile(self, name: str) -> Optional[VoiceProfile]:
        """Get a profile by name"""
        return self._profiles.get(name)


# Test function
def _test():
    """Test VoiceForge connection"""
    client = VoiceForgeTTS()

    print("Checking health...")
    health = client.check_health()
    print(f"Health: {health}")

    if health.get("status") == "ok":
        print("\nAvailable speakers:")
        speakers = client.get_speakers()
        for s in speakers:
            print(f"  - {s.get('id', s)}: {s.get('desc', '')}")

        print("\nSupported languages:")
        languages = client.get_languages()
        for lang in languages:
            print(f"  - {lang}")

        print("\nGenerating test speech...")
        try:
            output = client.generate_custom(
                "Hello, I am Jarvis, your personal AI assistant.",
                speaker="Ryan"
            )
            print(f"Generated: {output}")
        except Exception as e:
            print(f"Error: {e}")
    else:
        print("VoiceForge server is not available")


if __name__ == "__main__":
    _test()
