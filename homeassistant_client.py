#!/usr/bin/env python3
"""
Home Assistant Integration Client
Provides smart home control via Home Assistant REST API

Features:
- Device discovery and control
- Natural language command parsing
- Scene and automation triggering
- State monitoring
"""

import os
import re
import json
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
import httpx

logger = logging.getLogger(__name__)


@dataclass
class HADevice:
    """Represents a Home Assistant device/entity"""
    entity_id: str
    friendly_name: str
    domain: str
    state: str
    attributes: Dict[str, Any]

    @property
    def is_on(self) -> bool:
        return self.state in ['on', 'open', 'unlocked', 'playing']


class HomeAssistantClient:
    """
    Client for Home Assistant smart home integration.

    Usage:
        client = HomeAssistantClient(
            url="http://homeassistant.local:8123",
            token="your_long_lived_access_token"
        )

        # Get all devices
        devices = await client.get_devices()

        # Control a device
        await client.turn_on("light.living_room")
        await client.turn_off("switch.fan")

        # Natural language control
        result = await client.process_command("turn on the living room lights")
    """

    # Device domain keywords for natural language parsing
    DOMAIN_KEYWORDS = {
        'light': ['light', 'lights', 'lamp', 'lamps', 'bulb', 'bulbs'],
        'switch': ['switch', 'plug', 'outlet', 'socket'],
        'climate': ['temperature', 'thermostat', 'heating', 'cooling', 'ac', 'air conditioning'],
        'lock': ['lock', 'door lock'],
        'cover': ['blinds', 'curtains', 'shades', 'garage', 'cover'],
        'fan': ['fan', 'ceiling fan'],
        'media_player': ['tv', 'television', 'speaker', 'music', 'media'],
        'vacuum': ['vacuum', 'roomba', 'robot vacuum'],
        'scene': ['scene', 'mood'],
        'automation': ['automation', 'routine'],
    }

    # Action keywords
    ACTION_KEYWORDS = {
        'turn_on': ['turn on', 'switch on', 'enable', 'activate', 'open', 'unlock', 'start', 'play'],
        'turn_off': ['turn off', 'switch off', 'disable', 'deactivate', 'close', 'lock', 'stop', 'pause'],
        'toggle': ['toggle', 'flip'],
        'set': ['set', 'change', 'adjust'],
        'increase': ['increase', 'raise', 'brighten', 'louder', 'warmer', 'hotter'],
        'decrease': ['decrease', 'lower', 'dim', 'quieter', 'cooler', 'colder'],
    }

    def __init__(
        self,
        url: Optional[str] = None,
        token: Optional[str] = None,
        timeout: float = 10.0
    ):
        """
        Initialize Home Assistant client.

        Args:
            url: Home Assistant URL (default from HA_URL env var)
            token: Long-lived access token (default from HA_TOKEN env var)
            timeout: Request timeout in seconds
        """
        self.url = url or os.environ.get("HA_URL", "http://homeassistant.local:8123")
        self.token = token or os.environ.get("HA_TOKEN")
        self.timeout = timeout

        # Remove trailing slash from URL
        self.url = self.url.rstrip('/')

        if not self.token:
            logger.warning("No Home Assistant token configured. Set HA_TOKEN environment variable.")

        # Cache for devices
        self._devices_cache: Dict[str, HADevice] = {}
        self._rooms_cache: Dict[str, List[str]] = {}

    @property
    def headers(self) -> Dict[str, str]:
        """Get request headers with authentication"""
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    @property
    def is_configured(self) -> bool:
        """Check if Home Assistant is configured"""
        return bool(self.token)

    # MARK: - API Methods

    async def check_health(self) -> bool:
        """Check if Home Assistant is reachable"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.url}/api/",
                    headers=self.headers
                )
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Home Assistant health check failed: {e}")
            return False

    async def get_devices(self, domain: Optional[str] = None) -> List[HADevice]:
        """Get all devices or devices of a specific domain"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.url}/api/states",
                    headers=self.headers
                )
                response.raise_for_status()

                devices = []
                for state in response.json():
                    entity_id = state.get("entity_id", "")
                    entity_domain = entity_id.split(".")[0] if "." in entity_id else ""

                    if domain and entity_domain != domain:
                        continue

                    device = HADevice(
                        entity_id=entity_id,
                        friendly_name=state.get("attributes", {}).get("friendly_name", entity_id),
                        domain=entity_domain,
                        state=state.get("state", "unknown"),
                        attributes=state.get("attributes", {})
                    )
                    devices.append(device)
                    self._devices_cache[entity_id] = device

                return devices

        except Exception as e:
            logger.error(f"Failed to get devices: {e}")
            return []

    async def get_device(self, entity_id: str) -> Optional[HADevice]:
        """Get a specific device by entity ID"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.url}/api/states/{entity_id}",
                    headers=self.headers
                )
                response.raise_for_status()

                state = response.json()
                entity_domain = entity_id.split(".")[0] if "." in entity_id else ""

                device = HADevice(
                    entity_id=entity_id,
                    friendly_name=state.get("attributes", {}).get("friendly_name", entity_id),
                    domain=entity_domain,
                    state=state.get("state", "unknown"),
                    attributes=state.get("attributes", {})
                )
                self._devices_cache[entity_id] = device
                return device

        except Exception as e:
            logger.error(f"Failed to get device {entity_id}: {e}")
            return None

    async def call_service(
        self,
        domain: str,
        service: str,
        entity_id: Optional[str] = None,
        **kwargs
    ) -> bool:
        """Call a Home Assistant service"""
        try:
            data = kwargs.copy()
            if entity_id:
                data["entity_id"] = entity_id

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.url}/api/services/{domain}/{service}",
                    headers=self.headers,
                    json=data
                )
                response.raise_for_status()
                logger.info(f"Called service {domain}.{service} for {entity_id}")
                return True

        except Exception as e:
            logger.error(f"Failed to call service {domain}.{service}: {e}")
            return False

    # MARK: - Convenience Methods

    async def turn_on(self, entity_id: str, **kwargs) -> bool:
        """Turn on a device"""
        domain = entity_id.split(".")[0]
        return await self.call_service(domain, "turn_on", entity_id, **kwargs)

    async def turn_off(self, entity_id: str, **kwargs) -> bool:
        """Turn off a device"""
        domain = entity_id.split(".")[0]
        return await self.call_service(domain, "turn_off", entity_id, **kwargs)

    async def toggle(self, entity_id: str) -> bool:
        """Toggle a device"""
        domain = entity_id.split(".")[0]
        return await self.call_service(domain, "toggle", entity_id)

    async def set_brightness(self, entity_id: str, brightness: int) -> bool:
        """Set light brightness (0-255)"""
        return await self.call_service("light", "turn_on", entity_id, brightness=brightness)

    async def set_temperature(self, entity_id: str, temperature: float) -> bool:
        """Set thermostat temperature"""
        return await self.call_service("climate", "set_temperature", entity_id, temperature=temperature)

    async def activate_scene(self, scene_id: str) -> bool:
        """Activate a scene"""
        return await self.call_service("scene", "turn_on", scene_id)

    async def trigger_automation(self, automation_id: str) -> bool:
        """Trigger an automation"""
        return await self.call_service("automation", "trigger", automation_id)

    # MARK: - Natural Language Processing

    async def process_command(self, command: str) -> Dict[str, Any]:
        """
        Process a natural language command.

        Args:
            command: Natural language command like "turn on the living room lights"

        Returns:
            Dict with 'success', 'action', 'entities', and 'message' keys
        """
        command_lower = command.lower()

        # Determine if this is a smart home command
        if not self._is_smart_home_command(command_lower):
            return {
                "success": False,
                "is_smart_home": False,
                "message": "Not a smart home command"
            }

        # Parse action
        action = self._parse_action(command_lower)
        if not action:
            return {
                "success": False,
                "is_smart_home": True,
                "message": "Could not determine action"
            }

        # Parse target domain and location
        domain = self._parse_domain(command_lower)
        location = self._parse_location(command_lower)

        # Find matching entities
        entities = await self._find_matching_entities(domain, location, command_lower)

        if not entities:
            return {
                "success": False,
                "is_smart_home": True,
                "action": action,
                "message": f"No matching devices found for {domain or 'device'}" +
                          (f" in {location}" if location else "")
            }

        # Execute action
        results = []
        for entity in entities:
            if action == "turn_on":
                success = await self.turn_on(entity.entity_id)
            elif action == "turn_off":
                success = await self.turn_off(entity.entity_id)
            elif action == "toggle":
                success = await self.toggle(entity.entity_id)
            else:
                success = False

            results.append({
                "entity_id": entity.entity_id,
                "friendly_name": entity.friendly_name,
                "success": success
            })

        all_success = all(r["success"] for r in results)
        entity_names = [r["friendly_name"] for r in results]

        return {
            "success": all_success,
            "is_smart_home": True,
            "action": action,
            "entities": results,
            "message": f"{'Successfully' if all_success else 'Failed to'} {action.replace('_', ' ')} {', '.join(entity_names)}"
        }

    def _is_smart_home_command(self, text: str) -> bool:
        """Check if text is a smart home command"""
        # Check for domain keywords
        for keywords in self.DOMAIN_KEYWORDS.values():
            if any(kw in text for kw in keywords):
                return True

        # Check for action keywords
        for keywords in self.ACTION_KEYWORDS.values():
            if any(kw in text for kw in keywords):
                return True

        return False

    def _parse_action(self, text: str) -> Optional[str]:
        """Parse action from command text"""
        for action, keywords in self.ACTION_KEYWORDS.items():
            if any(kw in text for kw in keywords):
                return action
        return None

    def _parse_domain(self, text: str) -> Optional[str]:
        """Parse device domain from command text"""
        for domain, keywords in self.DOMAIN_KEYWORDS.items():
            if any(kw in text for kw in keywords):
                return domain
        return None

    def _parse_location(self, text: str) -> Optional[str]:
        """Parse location/room from command text"""
        # Common room names
        rooms = [
            'living room', 'bedroom', 'kitchen', 'bathroom', 'office',
            'garage', 'basement', 'attic', 'hallway', 'dining room',
            'guest room', 'master bedroom', 'kids room', 'nursery',
            'patio', 'backyard', 'front yard', 'porch', 'deck',
            'upstairs', 'downstairs', 'outside', 'inside'
        ]

        for room in rooms:
            if room in text:
                return room

        return None

    async def _find_matching_entities(
        self,
        domain: Optional[str],
        location: Optional[str],
        command: str
    ) -> List[HADevice]:
        """Find entities matching the domain and location"""
        # Refresh device cache if empty
        if not self._devices_cache:
            await self.get_devices()

        matches = []

        for entity_id, device in self._devices_cache.items():
            # Filter by domain
            if domain and device.domain != domain:
                continue

            # Check if friendly name matches location
            friendly_lower = device.friendly_name.lower()

            if location and location not in friendly_lower:
                continue

            matches.append(device)

        return matches


# Synchronous wrapper
class HomeAssistantClientSync:
    """Synchronous wrapper for HomeAssistantClient"""

    def __init__(self, **kwargs):
        import asyncio
        self._client = HomeAssistantClient(**kwargs)
        self._loop = asyncio.new_event_loop()

    def check_health(self) -> bool:
        return self._loop.run_until_complete(self._client.check_health())

    def get_devices(self, domain: Optional[str] = None) -> List[HADevice]:
        return self._loop.run_until_complete(self._client.get_devices(domain))

    def turn_on(self, entity_id: str, **kwargs) -> bool:
        return self._loop.run_until_complete(self._client.turn_on(entity_id, **kwargs))

    def turn_off(self, entity_id: str, **kwargs) -> bool:
        return self._loop.run_until_complete(self._client.turn_off(entity_id, **kwargs))

    def process_command(self, command: str) -> Dict[str, Any]:
        return self._loop.run_until_complete(self._client.process_command(command))

    def __del__(self):
        self._loop.close()


# Test function
async def _test():
    """Test Home Assistant connection"""
    client = HomeAssistantClient()

    print(f"URL: {client.url}")
    print(f"Configured: {client.is_configured}")

    if client.is_configured:
        health = await client.check_health()
        print(f"Health: {'OK' if health else 'FAILED'}")

        if health:
            devices = await client.get_devices()
            print(f"\nFound {len(devices)} devices:")
            for device in devices[:10]:
                print(f"  - {device.friendly_name} ({device.entity_id}): {device.state}")

            print("\nTesting command parsing:")
            result = await client.process_command("turn on the living room lights")
            print(f"  Result: {result}")
    else:
        print("Set HA_URL and HA_TOKEN environment variables to test")


if __name__ == "__main__":
    import asyncio
    asyncio.run(_test())
