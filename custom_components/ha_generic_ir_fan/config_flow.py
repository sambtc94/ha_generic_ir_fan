from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries

from . import DOMAIN

DEFAULT_NAME = "Generic IR Fan"
SPEED_OPTIONS = ["speed_1", "speed_2", "speed_3"]


class GenericIRFanConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial config step."""
        errors = {}

        if user_input is not None:
            preset_modes = [
                mode.strip()
                for mode in user_input.get("preset_modes", "").split(",")
                if mode.strip()
            ]
            user_input["preset_modes"] = preset_modes

            return self.async_create_entry(
                title=user_input.get("name") or DEFAULT_NAME,
                data=user_input,
            )

        data_schema = vol.Schema(
            {
                vol.Required("remote_entity"): str,
                vol.Optional("name", default=DEFAULT_NAME): str,
                vol.Optional("has_on_command", default=True): bool,
                vol.Optional("default_speed", default="speed_1"): vol.In(SPEED_OPTIONS),
                vol.Optional("preset_modes", default=""): str,
            }
        )
        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )