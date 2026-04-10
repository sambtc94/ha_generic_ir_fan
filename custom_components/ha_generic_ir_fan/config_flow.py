from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import selector

from . import DOMAIN

DEFAULT_NAME = "Generic IR Fan"
DEFAULT_SPEED_COUNT = 3
MAX_SPEED_COUNT = 6


def _parse_preset_modes(raw_modes: str) -> list[str]:
    """Parse preset modes from the config flow input."""
    return [mode.strip() for mode in str(raw_modes or "").split(",") if mode.strip()]


def _parse_power_values(raw_values: str) -> list[float]:
    """Parse optional per-speed power values from the config flow input."""
    values: list[float] = []
    for item in str(raw_values or "").split(","):
        cleaned = item.strip()
        if cleaned:
            values.append(float(cleaned))
    return values


class GenericIRFanConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial config step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            speed_count = max(
                1,
                min(int(user_input.get("speed_count", DEFAULT_SPEED_COUNT)), MAX_SPEED_COUNT),
            )
            default_speed_number = int(user_input.get("default_speed", 1))

            try:
                power_values = _parse_power_values(user_input.get("speed_power_values", ""))
            except ValueError:
                errors["speed_power_values"] = "invalid_speed_power_values"
            else:
                if default_speed_number > speed_count:
                    errors["default_speed"] = "invalid_default_speed"
                elif power_values and len(power_values) != speed_count:
                    errors["speed_power_values"] = "invalid_speed_power_values"
                else:
                    user_input["preset_modes"] = _parse_preset_modes(user_input.get("preset_modes", ""))
                    user_input["speed_count"] = speed_count
                    user_input["default_speed"] = f"speed_{default_speed_number}"
                    user_input["power_sensor"] = user_input.get("power_sensor") or None
                    user_input["power_on_threshold"] = float(user_input.get("power_on_threshold", 1.0) or 0)
                    user_input["speed_power_values"] = power_values

                    return self.async_create_entry(
                        title=user_input.get("name") or DEFAULT_NAME,
                        data=user_input,
                    )

        data_schema = vol.Schema(
            {
                vol.Required("remote_entity"): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="remote")
                ),
                vol.Optional("name", default=DEFAULT_NAME): str,
                vol.Optional("has_on_command", default=True): bool,
                vol.Optional("speed_count", default=DEFAULT_SPEED_COUNT): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1,
                        max=MAX_SPEED_COUNT,
                        step=1,
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Optional("default_speed", default=1): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1,
                        max=MAX_SPEED_COUNT,
                        step=1,
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Optional("preset_modes", default=""): str,
                vol.Optional("power_sensor"): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Optional("power_on_threshold", default=1.0): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0,
                        max=5000,
                        step=0.1,
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Optional("speed_power_values", default=""): str,
            }
        )
        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )