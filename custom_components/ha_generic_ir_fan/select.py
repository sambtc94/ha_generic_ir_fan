from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.helpers.device_registry import DeviceInfo

from . import DATA_ENTRIES, DOMAIN
from .fan import DEFAULT_SPEED_COUNT, _normalize_preset_modes, build_available_actions, build_speed_list


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the IR action select entity."""
    data = config_entry.data
    speeds = build_speed_list(data.get("speed_count", DEFAULT_SPEED_COUNT))
    options = build_available_actions(
        data.get("has_on_command", True),
        speeds,
        _normalize_preset_modes(data.get("preset_modes")),
    )
    async_add_entities([GenericIRFanActionSelect(hass, config_entry, data.get("name", "Generic IR Fan"), options)])


class GenericIRFanActionSelect(SelectEntity):
    """Select the IR action to learn or clear from the GUI."""

    _attr_has_entity_name = True

    def __init__(self, hass, config_entry, fan_name: str, options: list[str]):
        self._hass = hass
        self._config_entry = config_entry
        self._fan_name = fan_name
        self._attr_name = "IR action"
        self._attr_unique_id = f"{config_entry.entry_id}_ir_action"
        self._attr_options = options

        entry_data = self._get_entry_data()
        selected_action = entry_data.get("selected_action", options[0] if options else "off")
        if selected_action not in options and options:
            selected_action = options[0]
        self._attr_current_option = selected_action
        entry_data["selected_action"] = selected_action

    @property
    def device_info(self):
        return DeviceInfo(
            identifiers={(DOMAIN, self._config_entry.entry_id)},
            name=self._fan_name,
            manufacturer="Generic IR Fan",
            model="IR Fan",
        )

    def _get_entry_data(self):
        return self._hass.data.setdefault(DOMAIN, {}).setdefault(DATA_ENTRIES, {}).setdefault(
            self._config_entry.entry_id,
            {},
        )

    async def async_select_option(self, option: str):
        """Select the current IR action for GUI learning/clearing."""
        if option not in self.options:
            return

        self._attr_current_option = option
        self._get_entry_data()["selected_action"] = option
        self.async_write_ha_state()