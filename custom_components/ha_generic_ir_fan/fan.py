from __future__ import annotations

import logging
import re
from typing import Any

import voluptuous as vol

try:
    from homeassistant.components.fan import FanEntity, FanEntityFeature

    SUPPORT_SET_SPEED = FanEntityFeature.SET_SPEED
    SUPPORT_OSCILLATE = FanEntityFeature.OSCILLATE
    SUPPORT_PRESET_MODE = FanEntityFeature.PRESET_MODE
except ImportError:
    from homeassistant.components.fan import (  # type: ignore[attr-defined]
        FanEntity,
        SUPPORT_OSCILLATE,
        SUPPORT_PRESET_MODE,
        SUPPORT_SET_SPEED,
    )

from homeassistant.helpers import entity_platform

from . import DOMAIN

_LOGGER = logging.getLogger(__name__)
SPEEDS = ["speed_1", "speed_2", "speed_3"]
PERCENTAGE_BY_SPEED = {
    "off": 0,
    "speed_1": 33,
    "speed_2": 66,
    "speed_3": 100,
}


def _normalize_preset_modes(raw_modes: Any) -> list[str]:
    """Normalize preset modes from config-entry data."""
    if not raw_modes:
        return []

    if isinstance(raw_modes, str):
        raw_modes = raw_modes.split(",")

    modes: list[str] = []
    for mode in raw_modes:
        cleaned = str(mode).strip()
        if cleaned and cleaned not in modes:
            modes.append(cleaned)
    return modes


def _preset_to_action(preset_mode: str) -> str:
    """Convert a preset mode name to a learn/send action string."""
    slug = re.sub(r"[^a-z0-9]+", "_", preset_mode.strip().lower()).strip("_")
    return f"mode_{slug}"


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the generic IR fan entity from a config entry."""
    data = config_entry.data

    entity = GenericIRFan(
        hass=hass,
        config_entry=config_entry,
        name=data.get("name", "Generic IR Fan"),
        remote_entity=data["remote_entity"],
        has_on_command=data.get("has_on_command", True),
        default_speed=data.get("default_speed", "speed_1"),
        preset_modes=_normalize_preset_modes(data.get("preset_modes")),
        commands=data.get("commands", {}),
    )
    async_add_entities([entity])

    domain_data = hass.data.setdefault(DOMAIN, {})
    if not domain_data.get("entity_services_registered"):
        platform = entity_platform.async_get_current_platform()
        service_schema = {vol.Required("action"): str}

        platform.async_register_entity_service(
            "learn_command",
            service_schema,
            "async_learn_command",
        )
        platform.async_register_entity_service(
            "clear_learned",
            service_schema,
            "async_clear_learned",
        )
        domain_data["entity_services_registered"] = True


class GenericIRFan(FanEntity):
    """Representation of a generic IR-controlled fan."""

    def __init__(
        self,
        hass,
        config_entry,
        name: str,
        remote_entity: str,
        has_on_command: bool,
        default_speed: str,
        preset_modes: list[str],
        commands: dict[str, str],
    ):
        self._hass = hass
        self._config_entry = config_entry
        self._attr_name = name
        self._attr_unique_id = config_entry.entry_id
        self._attr_should_poll = False

        self._remote_entity = remote_entity
        self._has_on_command = has_on_command
        self._default_speed = default_speed if default_speed in SPEEDS else "speed_1"
        self._preset_modes = preset_modes

        self._state = False
        self._speed = "off"
        self._percentage = 0
        self._oscillating = False
        self._preset_mode = None
        self._commands = dict(commands or {})

    @property
    def supported_features(self):
        features = SUPPORT_SET_SPEED | SUPPORT_OSCILLATE
        if self._preset_modes:
            features |= SUPPORT_PRESET_MODE
        return features

    @property
    def is_on(self):
        return self._state

    @property
    def speed(self):
        return self._speed

    @property
    def speed_list(self):
        return ["off", *SPEEDS]

    @property
    def percentage(self):
        return self._percentage

    @property
    def percentage_step(self):
        return int(100 / len(SPEEDS))

    @property
    def oscillating(self):
        return self._oscillating

    @property
    def preset_mode(self):
        return self._preset_mode

    @property
    def preset_modes(self):
        return self._preset_modes

    @property
    def extra_state_attributes(self):
        return {
            "remote_entity": self._remote_entity,
            "has_on_command": self._has_on_command,
            "default_speed": self._default_speed,
            "learned_actions": sorted(self._commands),
            "learnable_actions": self._available_actions(),
        }

    async def async_turn_on(self, percentage=None, preset_mode=None, **kwargs):
        if preset_mode is not None:
            await self.async_set_preset_mode(preset_mode)
            return

        if percentage is not None:
            await self.async_set_percentage(percentage)
            return

        if self._has_on_command and await self._send_command("on"):
            self._state = True
            if self._speed == "off":
                self._set_speed_state(self._default_speed)
            self.async_write_ha_state()
            return

        await self.async_set_speed(self._default_speed)

    async def async_turn_off(self, **kwargs):
        result = await self._send_command("off")
        if result:
            self._state = False
            self._set_speed_state("off")
            self.async_write_ha_state()

    async def async_set_speed(self, speed: str):
        if speed == "off":
            await self.async_turn_off()
            return

        if speed not in SPEEDS:
            _LOGGER.warning("Unsupported fan speed '%s'", speed)
            return

        result = await self._send_command(speed)
        if result:
            self._state = True
            self._set_speed_state(speed)
            self.async_write_ha_state()

    async def async_set_percentage(self, percentage):
        if not percentage:
            await self.async_turn_off()
            return

        if percentage <= 33:
            speed = "speed_1"
        elif percentage <= 66:
            speed = "speed_2"
        else:
            speed = "speed_3"

        await self.async_set_speed(speed)

    async def async_set_preset_mode(self, preset_mode: str):
        if preset_mode not in self._preset_modes:
            _LOGGER.warning(
                "Unknown preset mode '%s'. Available modes: %s",
                preset_mode,
                self._preset_modes,
            )
            return

        result = await self._send_command(_preset_to_action(preset_mode))
        if result:
            self._preset_mode = preset_mode
            self._state = True
            self.async_write_ha_state()

    async def async_oscillate(self, oscillating: bool):
        result = await self._send_command("oscillate")
        if result:
            self._oscillating = oscillating
            self.async_write_ha_state()

    async def async_learn_command(self, action: str):
        if action not in self._available_actions():
            _LOGGER.warning(
                "Unknown action '%s'. Valid actions: %s",
                action,
                ", ".join(self._available_actions()),
            )
            return

        _LOGGER.info("Learning IR command for action: %s", action)
        await self._hass.services.async_call(
            "remote",
            "learn_command",
            {
                "entity_id": self._remote_entity,
                "device": self.name,
                "command": [action],
            },
            blocking=True,
        )
        self._commands[action] = action
        self._save_commands()
        self.async_write_ha_state()

    async def async_clear_learned(self, action: str):
        self._commands.pop(action, None)
        self._save_commands()
        self.async_write_ha_state()

    def _available_actions(self) -> list[str]:
        actions = ["off", *SPEEDS, "oscillate"]
        if self._has_on_command:
            actions.insert(0, "on")
        actions.extend(_preset_to_action(mode) for mode in self._preset_modes)
        return actions

    def _save_commands(self) -> None:
        updated_data = dict(self._config_entry.data)
        updated_data["commands"] = self._commands
        self._hass.config_entries.async_update_entry(self._config_entry, data=updated_data)

    def _set_speed_state(self, speed: str) -> None:
        self._speed = speed
        self._percentage = PERCENTAGE_BY_SPEED.get(speed, 0)

    async def _send_command(self, action: str) -> bool:
        if action not in self._commands:
            _LOGGER.warning("No IR command assigned for action '%s'", action)
            return False

        await self._hass.services.async_call(
            "remote",
            "send_command",
            {
                "entity_id": self._remote_entity,
                "device": self.name,
                "command": [self._commands[action]],
            },
            blocking=True,
        )
        return True