from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import selector

from . import DOMAIN

DEFAULT_NAME = "Generic IR Fan"
DEFAULT_SPEED_COUNT = 3
MAX_SPEED_COUNT = 6


class GenericIRFanConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial config step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            speed_count = max(1, min(int(user_input.get("speed_count", DEFAULT_SPEED_COUNT)), MAX_SPEED_COUNT))
            default_speed_number = int(user_input.get("default_speed", 1))

            if default_speed_number > speed_count:
                errors["default_speed"] = "invalid_default_speed"
            else:
                preset_modes = [
                    mode.strip()
                    for mode in user_input.get("preset_modes", "").split(",")
                    if mode.strip()
                ]
                user_input["preset_modes"] = preset_modes
                user_input["speed_count"] = speed_count
                user_input["default_speed"] = f"speed_{default_speed_number}"

                return self.async_create_entry(
                    title=user_input.get("name") or DEFAULT_NAME,
                    data=user_input,
                )

        data_schema = vol.Schema(
            {
                vol.Required(
                    "remote_entity",
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="remote")
                ),
                vol.Optional("name", default=DEFAULT_NAME): str,
                vol.Optional("has_on_command", default=True): bool,
                vol.Optional(
                    "speed_count",
                    default=DEFAULT_SPEED_COUNT,
                ): selector.NumberSelector(
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
            }
        )
        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )