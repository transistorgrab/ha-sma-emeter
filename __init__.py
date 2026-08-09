"""
Support for SMA Energy Meter.
Copyright (c) 2026 transistorgrab@github.com 
Licensed under the MIT License
"""

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform

from .emeter import SMAEmeterListener

DOMAIN    = 'sma_emeter'
PLATFORMS = [Platform.SENSOR]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    listener = SMAEmeterListener(hass, entry)
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = listener
    hass.data.setdefault('sma_emeter_entities', [])

    hass.async_create_task(listener.start())

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(update_listener)) ## if user changes settings
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        listener = hass.data[DOMAIN].pop(entry.entry_id)
        if hasattr(listener, 'transport'):
            listener.async_stop() # close UDP socket
    return unload_ok

async def update_listener(hass: HomeAssistant, entry: ConfigEntry):
    ''' reload integration when options change '''
    await hass.config_entries.async_reload(entry.entry_id)