"""Adds config flow for Oz Poll."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import OzPollApiClient, OzPollApiError
from .const import (
    CONF_URL_WEBSITE,
    CONF_URL_API, 
    CONF_I_SUBSCRIBE_AND_SUPPORT,
    DOMAIN,
)


class OzPollFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for oz_poll."""

    VERSION = 1
    MINOR_VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle a flow initialized by the user."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validate URLs
            website_url = user_input.get(CONF_URL_WEBSITE, "").strip()
            api_url = user_input.get(CONF_URL_API, "").strip()
            premium_mode = user_input.get(CONF_I_SUBSCRIBE_AND_SUPPORT, False)
            
            # Validate website URL
            if not website_url:
                errors[CONF_URL_WEBSITE] = "url_required"
            elif not website_url.startswith(('http://', 'https://')):
                errors[CONF_URL_WEBSITE] = "invalid_url"
            
            # Validate API URL if premium mode is enabled
            if premium_mode:
                if not api_url:
                    errors[CONF_URL_API] = "url_required"
                elif not api_url.startswith(('http://', 'https://')):
                    errors[CONF_URL_API] = "invalid_url"
            
            # If no validation errors, test connection and create entry
            if not errors:
                try:
                    await self._test_website_connection(website_url)
                    
                    data = {
                        CONF_URL_WEBSITE: website_url,
                        CONF_I_SUBSCRIBE_AND_SUPPORT: premium_mode,
                    }
                    
                    if premium_mode and api_url:
                        data[CONF_URL_API] = api_url
                        title = "Oz Poll (Premium)"
                    else:
                        title = "Oz Poll"
                        
                    return self.async_create_entry(title=title, data=data)
                    
                except OzPollApiError:
                    errors["base"] = "cannot_connect"
                except Exception:
                    errors["base"] = "unknown"

        # Build schema with logical field ordering
        schema_dict = {
            vol.Required(CONF_URL_WEBSITE): str,
            vol.Optional(CONF_I_SUBSCRIBE_AND_SUPPORT, default=False): bool,
        }
        
        # Add API URL field if premium mode is selected
        if user_input and user_input.get(CONF_I_SUBSCRIBE_AND_SUPPORT):
            schema_dict[vol.Required(CONF_URL_API)] = str

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(schema_dict),
            errors=errors,
        )

    async def _test_website_connection(self, website_url: str) -> None:
        """Test if we can connect to the website."""
        session = async_get_clientsession(self.hass)
        client = OzPollApiClient(website_url=website_url, session=session)
        
        # Test connection by attempting to fetch data
        await client.async_get_data()

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> OzPollOptionsFlowHandler:
        """Create the options flow."""
        return OzPollOptionsFlowHandler(config_entry)


class OzPollOptionsFlowHandler(config_entries.OptionsFlow):
    """Options flow for oz_poll."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize HACS options flow."""
        self.config_entry = config_entry
        self.options = dict(config_entry.options)

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Manage the options."""
        return await self.async_step_user()

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle a flow initialized by the user."""
        if user_input is not None:
            self.options.update(user_input)
            return self.async_create_entry(data=self.options)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        "sensor", default=self.options.get("sensor", True)
                    ): bool
                }
            ),
        )