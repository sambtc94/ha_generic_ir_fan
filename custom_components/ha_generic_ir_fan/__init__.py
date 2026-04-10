from __future__ import annotations

DOMAIN = "ha_generic_ir_fan"
DATA_ENTRIES = "entries"
PLATFORMS = ["fan", "button", "select"]


async def async_setup(hass, config) -> bool:
    """Set up the Generic IR Fan integration."""
    hass.data.setdefault(
        DOMAIN,
        {DATA_ENTRIES: {}, "entity_services_registered": False},
    )
    return True


async def async_setup_entry(hass, entry) -> bool:
    """Set up Generic IR Fan from a config entry."""
    domain_data = hass.data.setdefault(
        DOMAIN,
        {DATA_ENTRIES: {}, "entity_services_registered": False},
    )
    domain_data[DATA_ENTRIES].setdefault(entry.entry_id, {})
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass, entry) -> bool:
    """Unload a Generic IR Fan config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data.get(DOMAIN, {}).get(DATA_ENTRIES, {}).pop(entry.entry_id, None)
    return unload_ok