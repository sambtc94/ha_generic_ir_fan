from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.helpers.device_registry import DeviceInfo

from . import DATA_ENTRIES, DOMAIN


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the GUI buttons for learning and clearing commands."""
    fan_name = config_entry.data.get("name", "Generic IR Fan")
    async_add_entities(
        [
            GenericIRFanLearnButton(hass, config_entry, fan_name),
            GenericIRFanClearButton(hass, config_entry, fan_name),
        ]
    )


class _BaseIRFanButton(ButtonEntity):
    """Shared button behavior for the IR fan GUI buttons."""

    _attr_has_entity_name = True

    def __init__(self, hass, config_entry, fan_name: str):
        self._hass = hass
        self._config_entry = config_entry
        self._fan_name = fan_name

    @property
    def device_info(self):
        return DeviceInfo(
            identifiers={(DOMAIN, self._config_entry.entry_id)},
            name=self._fan_name,
            manufacturer="Generic IR Fan",
            model="IR Fan",
        )

    @property
    def extra_state_attributes(self):
        return {"selected_action": self._get_entry_data().get("selected_action", "off")}

    def _get_entry_data(self):
        return self._hass.data.setdefault(DOMAIN, {}).setdefault(DATA_ENTRIES, {}).setdefault(
            self._config_entry.entry_id,
            {},
        )


class GenericIRFanLearnButton(_BaseIRFanButton):
    """Button to learn the selected IR action from the GUI."""

    def __init__(self, hass, config_entry, fan_name: str):
        super().__init__(hass, config_entry, fan_name)
        self._attr_name = "Learn selected command"
        self._attr_unique_id = f"{config_entry.entry_id}_learn_selected"
        self._attr_icon = "mdi:remote-plus"

    async def async_press(self):
        """Learn the currently selected IR action."""
        entry_data = self._get_entry_data()
        fan_entity = entry_data.get("fan_entity")
        selected_action = entry_data.get("selected_action", "off")
        if fan_entity is not None:
            await fan_entity.async_learn_command(selected_action)


class GenericIRFanClearButton(_BaseIRFanButton):
    """Button to clear the selected IR action from the GUI."""

    def __init__(self, hass, config_entry, fan_name: str):
        super().__init__(hass, config_entry, fan_name)
        self._attr_name = "Clear selected command"
        self._attr_unique_id = f"{config_entry.entry_id}_clear_selected"
        self._attr_icon = "mdi:remote-off"

    async def async_press(self):
        """Clear the currently selected IR action."""
        entry_data = self._get_entry_data()
        fan_entity = entry_data.get("fan_entity")
        selected_action = entry_data.get("selected_action", "off")
        if fan_entity is not None:
            await fan_entity.async_clear_learned(selected_action)