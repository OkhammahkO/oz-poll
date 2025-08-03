"""The Oz Poll integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    DOMAIN, 
    CONF_URL_WEBSITE,
    CONF_URL_API,
    CONF_I_SUBSCRIBE_AND_SUPPORT,
)
from .api import OzPollApiClient

type OzPollConfigEntry = ConfigEntry[OzPollApiClient]

PLATFORMS = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: OzPollConfigEntry) -> bool:
    """Set up Oz Poll from a config entry."""
    session = async_get_clientsession(hass)
    client = OzPollApiClient(
        website_url=entry.data.get(CONF_URL_WEBSITE),
        api_url=entry.data.get(CONF_URL_API),
        i_subscribe_and_support=entry.data.get(CONF_I_SUBSCRIBE_AND_SUPPORT, False),
        session=session,
    )
    
    entry.runtime_data = client
    
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: OzPollConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
