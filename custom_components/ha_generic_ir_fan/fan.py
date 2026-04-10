from __future__ import annotations

import logging
import math
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

from homeassistant.core import callback
from homeassistant.helpers import entity_platform
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.event import async_track_state_change_event

from . import DATA_ENTRIES, DOMAIN

_LOGGER = logging.getLogger(__name__)
DEFAULT_SPEED_COUNT = 3


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


def build_speed_list(speed_count: int) -> list[str]:
    """Build the available fan speed names."""
    count = max(1, int(speed_count or DEFAULT_SPEED_COUNT))
    return [f"speed_{index}" for index in range(1, count + 1)]


def build_available_actions(
    has_on_command: bool,
    speeds: list[str],
    preset_modes: list[str],
) -> list[str]:
    """Build all learnable IR actions for the fan."""
    actions = ["off", *speeds, "speed_toggle", "oscillate"]
    if has_on_command:
        actions.insert(0, "on")
    actions.extend(_preset_to_action(mode) for mode in preset_modes)
    return actions


def _normalize_speed_name(raw_speed: Any, speeds: list[str]) -> str:
    """Normalize a speed value from config-entry data."""
    if isinstance(raw_speed, int):
        candidate = f"speed_{raw_speed}"
    else:
        candidate = str(raw_speed or speeds[0])
    return candidate if candidate in speeds else speeds[0]


def _speed_to_percentage(speed: str, speeds: list[str]) -> int:
    """Convert a speed name to a percentage."""
    if speed == "off" or speed not in speeds:
        return 0
    return round(((speeds.index(speed) + 1) / len(speeds)) * 100)


def _parse_power_value(state_value: Any) -> float | None:
    """Parse a power sensor state into a float value."""
    try:
        return float(state_value)
    except (TypeError, ValueError):
        return None


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the generic IR fan entity from a config entry."""
    data = config_entry.data
    entry_data = hass.data.setdefault(DOMAIN, {}).setdefault(DATA_ENTRIES, {}).setdefault(
        config_entry.entry_id,
        {},
    )

    entity = GenericIRFan(
        hass=hass,
        config_entry=config_entry,
        name=data.get("name", "Generic IR Fan"),
        remote_entity=data["remote_entity"],
        has_on_command=data.get("has_on_command", True),
        speed_count=data.get("speed_count", DEFAULT_SPEED_COUNT),
        default_speed=data.get("default_speed", "speed_1"),
        preset_modes=_normalize_preset_modes(data.get("preset_modes")),
        commands=data.get("commands", {}),
        power_sensor=data.get("power_sensor"),
        power_on_threshold=data.get("power_on_threshold", 1.0),
        speed_power_values=data.get("speed_power_values", []),
        entry_data=entry_data,
    )
    entry_data["fan_entity"] = entity
    entry_data.setdefault("selected_action", entity.available_actions[0] if entity.available_actions else "off")
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
        speed_count: int,
        default_speed: str,
        preset_modes: list[str],
        commands: dict[str, str],
        power_sensor: str | None,
        power_on_threshold: float,
        speed_power_values: list[float],
        entry_data: dict[str, Any],
    ):
        self._hass = hass
        self._config_entry = config_entry
        self._entry_data = entry_data
        self._attr_name = name
        self._attr_unique_id = config_entry.entry_id
        self._attr_should_poll = False

        self._remote_entity = remote_entity
        self._has_on_command = has_on_command
        self._speed_count = max(1, int(speed_count or DEFAULT_SPEED_COUNT))
        self._speeds = build_speed_list(self._speed_count)
        self._default_speed = _normalize_speed_name(default_speed, self._speeds)
        self._preset_modes = preset_modes
        self._available_actions = build_available_actions(
            self._has_on_command,
            self._speeds,
            self._preset_modes,
        )

        self._power_sensor = power_sensor or None
        self._power_on_threshold = float(power_on_threshold or 0)
        self._speed_power_values = [float(value) for value in speed_power_values or []]
        self._last_power = None

        self._state = False
        self._speed = "off"
        self._percentage = 0
        self._oscillating = False
        self._preset_mode = None
        self._commands = dict(commands or {})

    @property
    def device_info(self):
        return DeviceInfo(
            identifiers={(DOMAIN, self._config_entry.entry_id)},
            name=self._attr_name,
            manufacturer="Generic IR Fan",
            model="IR Fan",
        )

    @property
    def available_actions(self) -> list[str]:
        return self._available_actions

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
        return ["off", *self._speeds]

    @property
    def percentage(self):
        return self._percentage

    @property
    def percentage_step(self):
        return max(1, round(100 / len(self._speeds)))

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
            "speed_count": self._speed_count,
            "default_speed": self._default_speed,
            "power_sensor": self._power_sensor,
            "power_on_threshold": self._power_on_threshold,
            "speed_power_values": self._speed_power_values,
            "last_power": self._last_power,
            "learned_actions": sorted(self._commands),
            "learnable_actions": self.available_actions,
        }

    async def async_added_to_hass(self):
        """Set up listeners when the entity is added."""
        await super().async_added_to_hass()
        self._entry_data["fan_entity"] = self
        self._entry_data.setdefault("selected_action", self.available_actions[0] if self.available_actions else "off")

        if self._power_sensor:
            self.async_on_remove(
                async_track_state_change_event(
                    self._hass,
                    [self._power_sensor],
                    self._async_handle_power_sensor_event,
                )
            )
            self._update_state_from_power(self._hass.states.get(self._power_sensor))

    @callback
    def _async_handle_power_sensor_event(self, event):
        """Handle updates from the linked power sensor."""
        self._update_state_from_power(event.data.get("new_state"))

    @callback
    def _update_state_from_power(self, state) -> None:
        """Update fan state based on the linked power monitor."""
        if state is None:
            return

        power_value = _parse_power_value(getattr(state, "state", None))
        if power_value is None:
            return

        self._last_power = power_value
        if power_value <= self._power_on_threshold:
            self._state = False
            self._set_speed_state("off")
        else:
            self._state = True
            inferred_speed = self._infer_speed_from_power(power_value)
            if inferred_speed is not None:
                self._set_speed_state(inferred_speed)

        self.async_write_ha_state()

    def _infer_speed_from_power(self, power_value: float) -> str | None:
        """Infer the current fan speed from the linked power sensor."""
        if len(self._speed_power_values) == len(self._speeds):
            index = min(
                range(len(self._speed_power_values)),
                key=lambda item: abs(power_value - self._speed_power_values[item]),
            )
            return self._speeds[index]

        if self._speed in self._speeds:
            return self._speed

        return self._default_speed

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

        if speed not in self._speeds:
            _LOGGER.warning("Unsupported fan speed '%s'", speed)
            return

        if speed in self._commands:
            result = await self._send_command(speed)
        elif "speed_toggle" in self._commands:
            result = await self._async_cycle_speed_to(speed)
        else:
            _LOGGER.warning(
                "No direct or toggle speed command assigned for '%s'",
                speed,
            )
            return

        if result:
            self._state = True
            self._set_speed_state(speed)
            self.async_write_ha_state()

    async def async_set_percentage(self, percentage):
        if not percentage:
            await self.async_turn_off()
            return

        index = min(
            len(self._speeds),
            max(1, math.ceil((percentage / 100) * len(self._speeds))),
        )
        await self.async_set_speed(self._speeds[index - 1])

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
            self._state = True
            self._preset_mode = preset_mode
            if self._speed == "off":
                self._set_speed_state(self._default_speed)
            self.async_write_ha_state()

    async def async_oscillate(self, oscillating: bool):
        result = await self._send_command("oscillate")
        if result:
            self._oscillating = oscillating
            self.async_write_ha_state()

    async def async_learn_command(self, action: str):
        if action not in self.available_actions:
            _LOGGER.warning(
                "Unknown action '%s'. Valid actions: %s",
                action,
                ", ".join(self.available_actions),
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

    def _save_commands(self) -> None:
        updated_data = dict(self._config_entry.data)
        updated_data["commands"] = self._commands
        self._hass.config_entries.async_update_entry(self._config_entry, data=updated_data)

    def _set_speed_state(self, speed: str) -> None:
        self._speed = speed
        self._percentage = _speed_to_percentage(speed, self._speeds)
        if speed != "off":
            self._preset_mode = None

    async def _async_cycle_speed_to(self, speed: str) -> bool:
        """Cycle through the available speeds using a single toggle button."""
        if speed not in self._speeds or "speed_toggle" not in self._commands:
            return False

        current_speed = self._speed if self._speed in self._speeds else None

        if not self._state or current_speed is None:
            if not await self._send_command("speed_toggle"):
                return False
            self._state = True
            current_speed = self._speeds[0]
            if speed == current_speed:
                return True

        current_index = self._speeds.index(current_speed)
        target_index = self._speeds.index(speed)
        steps = (target_index - current_index) % len(self._speeds)

        for _ in range(steps):
            if not await self._send_command("speed_toggle"):
                return False

        return True

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