from __future__ import annotations

DOMAIN = "ha_generic_ir_fan"
PLATFORMS = ["fan"]


async def async_setup(hass, config) -> bool:
    """Set up the Generic IR Fan integration."""
    return True


async def async_setup_entry(hass, entry) -> bool:
    """Set up Generic IR Fan from a config entry."""
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass, entry) -> bool:
    """Unload a Generic IR Fan config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)