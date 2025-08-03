"""Platform for sensor integration."""
from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from . import OzPollConfigEntry
from .api import OzPollApiClient, OzPollApiError
from .const import (
    CONF_URL_WEBSITE,
    CONF_URL_API,
    CONF_I_SUBSCRIBE_AND_SUPPORT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(minutes=DEFAULT_SCAN_INTERVAL)

# YAML platform schema
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_URL_WEBSITE): cv.url,
    vol.Optional(CONF_URL_API): cv.url,
    vol.Optional(CONF_I_SUBSCRIBE_AND_SUPPORT, default=False): cv.boolean,
})


async def setup_platform(
    hass: HomeAssistant,
    config: dict[str, Any],
    async_add_entities: AddEntitiesCallback,
    discovery_info: dict[str, Any] | None = None,
) -> None:
    """Set up the sensor platform from YAML configuration."""
    session = async_get_clientsession(hass)
    
    client = OzPollApiClient(
        website_url=config[CONF_URL_WEBSITE],
        api_url=config.get(CONF_URL_API),
        i_subscribe_and_support=config[CONF_I_SUBSCRIBE_AND_SUPPORT],
        session=session,
    )
    
    # Create a coordinator for YAML configuration (without config_entry)
    coordinator = OzPollDataUpdateCoordinator(hass, client, None)
    await coordinator.async_config_entry_first_refresh()
    
    async_add_entities([OzPollSensor(coordinator, None)])


async def async_setup_entry(
    hass: HomeAssistant,
    entry: OzPollConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    coordinator = OzPollDataUpdateCoordinator(hass, entry.runtime_data, entry)
    await coordinator.async_config_entry_first_refresh()
    
    async_add_entities([OzPollSensor(coordinator, entry)])


class OzPollDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage fetching data from the API."""

    def __init__(self, hass: HomeAssistant, client: OzPollApiClient, config_entry: ConfigEntry | None) -> None:
        """Initialize."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
            config_entry=config_entry,
        )
        self.client = client

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data via library."""
        try:
            # For now, just get basic data - expand this with actual website scraping
            data = await self.client.async_get_data()
            return data
        except OzPollApiError as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err


class OzPollSensor(CoordinatorEntity[OzPollDataUpdateCoordinator], SensorEntity):
    """Implementation of the Oz Poll sensor."""

    _attr_has_entity_name = True
    _attr_name = "Allergy forecast"

    def __init__(
        self,
        coordinator: OzPollDataUpdateCoordinator,
        entry: ConfigEntry | None,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        
        if entry:
            # Config entry setup
            self._attr_unique_id = f"{entry.entry_id}_allergy_forecast"
            self._attr_device_info = {
                "identifiers": {(DOMAIN, entry.entry_id)},
                "name": "Oz Poll",
                "manufacturer": "Oz Poll",
                "model": "Allergy Forecast",
                "entry_type": "service",
            }
        else:
            # YAML platform setup
            self._attr_unique_id = f"{DOMAIN}_allergy_forecast"
            self._attr_device_info = {
                "identifiers": {(DOMAIN, "yaml_platform")},
                "name": "Oz Poll",
                "manufacturer": "Oz Poll",
                "model": "Allergy Forecast (YAML)",
                "entry_type": "service",
            }

    @property
    def native_value(self) -> str | None:
        """Return the state of the sensor."""
        if not self.coordinator.data:
            return STATE_UNKNOWN
        
        # Get the current pollen level
        return self.coordinator.data.get("current_level", STATE_UNKNOWN)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return the state attributes."""
        if not self.coordinator.data:
            return None
        
        data = self.coordinator.data
        attributes = {
            "last_updated": self.coordinator.last_update_success,
            "location": data.get("location", "Unknown"),
            "date": data.get("date", "Unknown"),
        }
        
        # Add website data directly to attributes (for card compatibility)
        web_data = data.get("allergy_forecast_web", {})
        if web_data:
            attributes["allergy_forecast_web"] = web_data
            
        # Add API data directly to attributes (for card compatibility)
        api_data = data.get("allergy_forecast_api", {})
        if api_data:
            attributes["allergy_forecast_api"] = api_data
            # Add today's detailed forecast if available
            if api_data.get("forecast_days"):
                today = api_data["forecast_days"][0]
                attributes["today_pollen_types"] = today.get("pollen_data", [])
                attributes["today_summary"] = today.get("summary_stats", {})
                
        return attributes