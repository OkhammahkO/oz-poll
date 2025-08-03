"""API client for Oz Poll integration."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp
from bs4 import BeautifulSoup

from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

_LOGGER = logging.getLogger(__name__)


class OzPollApiError(HomeAssistantError):
    """Error to indicate something went wrong with the API."""


class OzPollApiClient:
    """API client for Oz Poll."""

    def __init__(
        self,
        website_url: str | None = None,
        api_url: str | None = None,
        i_subscribe_and_support: bool = False,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        """Initialize the API client."""
        self._website_url = website_url
        self._api_url = api_url
        self._i_subscribe_and_support = i_subscribe_and_support
        self._session = session

    async def async_get_data(self) -> dict[str, Any]:
        """Get data from the website and optionally API."""
        if not self._session:
            raise OzPollApiError("No session available")

        data = {}
        
        # Always get website data
        if self._website_url:
            try:
                website_data = await self.async_get_website_data(self._website_url)
                data.update(website_data)
                
                # Extract the main sensor value from website gauge data
                gauge_data = website_data.get("allergy_forecast_web", {}).get("site_gauge_data", {})
                if gauge_data:
                    data["current_level"] = gauge_data.get("gauge_value", "Unknown")
                    data["location"] = gauge_data.get("gauge_site", "Unknown")
                    data["date"] = gauge_data.get("gauge_date", "Unknown")
            except OzPollApiError:
                # Re-raise API errors to fail coordinator update
                raise
            except Exception as err:
                # Catch any unexpected errors and convert to API error
                raise OzPollApiError(f"Unexpected error getting website data: {err}") from err
        
        # Get API data if premium mode is enabled
        if self._i_subscribe_and_support and self._api_url:
            try:
                api_data = await self.async_get_api_data(self._api_url)
                data.update(api_data)
                
                # Override sensor value with API data if available
                api_forecast = api_data.get("allergy_forecast_api", {})
                if api_forecast.get("forecast_days"):
                    first_day = api_forecast["forecast_days"][0]
                    data["current_level"] = first_day.get("summary_stats", {}).get("summary_level", data.get("current_level", "Unknown"))
                    
            except OzPollApiError as err:
                _LOGGER.warning("Failed to get API data, using website data only: %s", err)
        
        return data

    async def async_get_website_data(self, url: str) -> dict[str, Any]:
        """Get data from the website."""
        if not self._session:
            raise OzPollApiError("No session available")

        try:
            async with self._session.get(url, timeout=10) as response:
                if response.status != 200:
                    raise OzPollApiError(f"Website returned status {response.status}")
                
                html_content = await response.text()
                soup = BeautifulSoup(html_content, "html.parser")
                
                # Extract data from the header gauge
                gauge_data = {}
                try:
                    gauge_date_elem = soup.select_one("#pdate.pollen-date")
                    gauge_site_elem = soup.select_one("#psite")
                    gauge_value_elem = soup.select_one("#plevel")
                    
                    if gauge_date_elem and gauge_site_elem and gauge_value_elem:
                        gauge_data = {
                            "gauge_date": gauge_date_elem.get_text(strip=True),
                            "gauge_site": gauge_site_elem.get_text(strip=True),
                            "gauge_value": gauge_value_elem.get_text(strip=True),
                        }
                except Exception as err:
                    _LOGGER.warning("Failed to extract gauge data: %s", err)
                
                data_web = {
                    "allergy_forecast_web": {
                        "site_gauge_data": gauge_data,
                    }
                }
                
                # Extract Melbourne specific data if applicable
                if gauge_data.get("gauge_site") == "Melbourne":
                    melbourne_data = self._extract_melbourne_data(soup, gauge_data)
                    data_web["allergy_forecast_web"].update(melbourne_data)
                
                return data_web
                
        except asyncio.TimeoutError as err:
            raise OzPollApiError("Timeout connecting to website") from err
        except aiohttp.ClientError as err:
            raise OzPollApiError(f"Error connecting to website: {err}") from err

    async def async_get_api_data(self, url: str) -> dict[str, Any]:
        """Get data from the API."""
        if not self._session:
            raise OzPollApiError("No session available")

        try:
            async with self._session.get(url, timeout=10) as response:
                if response.status != 200:
                    raise OzPollApiError(f"API returned status {response.status}")
                
                json_data = await response.json()
                
                # Parse the API response
                forecast_result = json_data.get("forecast_result", "")
                grass_gauge = json_data.get("grass_gauge", "")
                disclaimer = json_data.get("disclaimer", "")
                
                from datetime import datetime
                current_time = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
                
                data = {
                    "allergy_forecast_api": {
                        "grass_gauge": grass_gauge,
                        "disclaimer": disclaimer,
                        "last_updated": current_time,
                    }
                }
                
                # Parse the HTML content in forecast_result if available
                if forecast_result:
                    try:
                        soup = BeautifulSoup(forecast_result, "html.parser")
                        forecast_data = self._parse_api_forecast(soup)
                        data["allergy_forecast_api"].update(forecast_data)
                    except Exception as err:
                        _LOGGER.warning("Failed to parse API forecast data: %s", err)
                
                return data
                
        except asyncio.TimeoutError as err:
            raise OzPollApiError("Timeout connecting to API") from err
        except aiohttp.ClientError as err:
            raise OzPollApiError(f"Error connecting to API: {err}") from err

    def _parse_api_forecast(self, soup: BeautifulSoup) -> dict[str, Any]:
        """Parse the forecast data from API HTML content."""
        forecast_days = []
        
        # Find the pro_feature div which contains the forecast data
        pro_feature_div = soup.find("div", id="pro_feature", class_="pro_feature")
        if not pro_feature_div:
            return {"forecast_days": []}
            
        # Extract forecast location description
        location_description = "Unknown location"
        description_div = pro_feature_div.find(
            "div", text=lambda text: text and "Allergy Forecast" in text
        )
        if description_div:
            location_description = description_div.text.strip()
        
        # Parse each day's forecast
        forecast_day = 1
        for li in pro_feature_div.find_all("li"):
            day_data = self._parse_forecast_day(li, forecast_day)
            if day_data:
                forecast_days.append(day_data)
                forecast_day += 1
                
        # Calculate summary statistics
        today_level = "Unknown"
        if forecast_days:
            today_level = forecast_days[0].get("summary_stats", {}).get("summary_level", "Unknown")
        
        # Generate descriptions and summary for card compatibility
        today_summary_description = self._generate_today_description(forecast_days)
        forecast_7d_description = self._generate_7day_description(forecast_days)
        forecast_7d_summary = self._generate_7day_summary(forecast_days)
        
        return {
            "forecast_location_description": location_description,
            "forecast_days": forecast_days,
            "today_level": today_level,
            "today_summary_description": today_summary_description,
            "forecast_7d_description": forecast_7d_description,
            "forecast_7d_summary": forecast_7d_summary,
        }
        
    def _parse_forecast_day(self, li_element, forecast_day: int) -> dict[str, Any] | None:
        """Parse a single forecast day from API data."""
        try:
            date_element = li_element.find("p")
            weekday_element = li_element.find("h3")
            
            if not date_element or not weekday_element:
                return None
                
            date_text = date_element.get_text(strip=True)
            weekday_text = weekday_element.get_text(strip=True)[:3]
            
            # Get pollen types
            pollen_data = []
            for a in li_element.find_all("a"):
                pollen_type = a.get_text(strip=True)
                pollen_data.append({"pollen_type": pollen_type})
            
            # Map background colors to pollen levels
            background_map = {
                "var(--pollen-low-color)": "Low",
                "var(--pollen-moderate-color)": "Moderate", 
                "var(--pollen-high-color)": "High",
                "var(--pollen-extreme-color)": "Extreme",
                "red": "Extreme",
            }
            
            # Extract pollen levels from div styles
            for i, div in enumerate(li_element.find_all("div", class_="uk-first-column")):
                if i < len(pollen_data):
                    style = div.get("style", "")
                    level = "Unknown"
                    for color, mapped_level in background_map.items():
                        if color in style:
                            level = mapped_level
                            break
                    pollen_data[i]["pollen_level"] = level
            
            # Calculate summary statistics
            summary_stats = self._calculate_day_summary(pollen_data)
            
            return {
                "forecast_day": str(forecast_day),
                "date": date_text,
                "weekday": weekday_text,
                "pollen_data": pollen_data,
                "summary_stats": summary_stats,
            }
            
        except Exception as err:
            _LOGGER.warning("Failed to parse forecast day %s: %s", forecast_day, err)
            return None
            
    def _calculate_day_summary(self, pollen_data: list[dict[str, Any]]) -> dict[str, Any]:
        """Calculate summary statistics for a day's pollen data."""
        counts = {
            "low_count": 0,
            "moderate_count": 0, 
            "high_count": 0,
            "extreme_count": 0,
        }
        
        for pollen in pollen_data:
            level = pollen.get("pollen_level", "").lower()
            if level == "low":
                counts["low_count"] += 1
            elif level == "moderate":
                counts["moderate_count"] += 1
            elif level == "high":
                counts["high_count"] += 1
            elif level == "extreme":
                counts["extreme_count"] += 1
                
        # Determine overall level
        if counts["extreme_count"] > 0:
            summary_level = "Extreme"
        elif counts["high_count"] > 0:
            summary_level = "High"
        elif counts["moderate_count"] > 0:
            summary_level = "Moderate"
        else:
            summary_level = "Low"
            
        return {
            **counts,
            "summary_level": summary_level,
        }
        
    def _generate_today_description(self, forecast_days: list[dict[str, Any]]) -> str:
        """Generate human-readable today's forecast description."""
        if not forecast_days:
            return "No forecast data available."

        today_data = forecast_days[0]
        summary_level = today_data.get("summary_stats", {}).get("summary_level", "Unknown")
        pollen_data = today_data.get("pollen_data", [])

        extreme_pollen = [
            pollen["pollen_type"] for pollen in pollen_data
            if pollen.get("pollen_level") == "Extreme"
        ]
        high_pollen = [
            pollen["pollen_type"] for pollen in pollen_data
            if pollen.get("pollen_level") == "High"
        ]
        moderate_pollen = [
            pollen["pollen_type"] for pollen in pollen_data
            if pollen.get("pollen_level") == "Moderate"
        ]

        description = f"Today's pollen forecast is {summary_level}. "

        if extreme_pollen:
            description += f"The following pollen types have extreme levels: {', '.join(extreme_pollen)}. "

        if high_pollen:
            description += f"The following pollen types have high levels: {', '.join(high_pollen)}. "

        if moderate_pollen:
            description += f"The following pollen types have moderate levels: {', '.join(moderate_pollen)}."

        return description
        
    def _generate_7day_description(self, forecast_days: list[dict[str, Any]]) -> str:
        """Generate human-readable 7-day forecast description."""
        if not forecast_days:
            return "No forecast data available."
            
        # Take first 7 days
        days_7 = forecast_days[:7]
        
        moderate_count = sum(
            1 for day in days_7
            if day.get("summary_stats", {}).get("summary_level") == "Moderate"
        )
        high_count = sum(
            1 for day in days_7
            if day.get("summary_stats", {}).get("summary_level") == "High"
        )
        extreme_count = sum(
            1 for day in days_7
            if day.get("summary_stats", {}).get("summary_level") == "Extreme"
        )

        overall_summary = (
            "Extreme" if extreme_count > 0
            else "High" if high_count > 0
            else "Moderate" if moderate_count > 0
            else "Low"
        )
        
        description = f"The 7 day pollen outlook level is {overall_summary}. "
        description += f"There are {moderate_count} moderate days, "
        description += f"{high_count} high days, and "
        description += f"{extreme_count} extreme days. "

        if len(forecast_days) > 1:
            description += f"Tomorrow is {forecast_days[1].get('summary_stats', {}).get('summary_level', 'Unknown')}. "

        # Find weekend levels
        for day in days_7:
            if day.get("weekday") == "Sat":
                description += f"Saturday is {day.get('summary_stats', {}).get('summary_level', 'Unknown')}. "
                break
                
        for day in days_7:
            if day.get("weekday") == "Sun":
                description += f"Sunday is {day.get('summary_stats', {}).get('summary_level', 'Unknown')}."
                break

        return description
        
    def _generate_7day_summary(self, forecast_days: list[dict[str, Any]]) -> dict[str, Any]:
        """Generate 7-day summary statistics for compatibility with original sensor."""
        if not forecast_days:
            return {}
            
        # Take first 7 days
        days_7 = forecast_days[:7]
        
        moderate_count = sum(
            1 for day in days_7
            if day.get("summary_stats", {}).get("summary_level") == "Moderate"
        )
        high_count = sum(
            1 for day in days_7
            if day.get("summary_stats", {}).get("summary_level") == "High"
        )
        extreme_count = sum(
            1 for day in days_7
            if day.get("summary_stats", {}).get("summary_level") == "Extreme"
        )

        overall_summary = (
            "Extreme" if extreme_count > 0
            else "High" if high_count > 0
            else "Moderate" if moderate_count > 0
            else "Low"
        )

        # Find weekend levels
        saturday_level = next(
            (day.get("summary_stats", {}).get("summary_level")
             for day in days_7 if day.get("weekday") == "Sat"),
            None
        )
        sunday_level = next(
            (day.get("summary_stats", {}).get("summary_level")
             for day in days_7 if day.get("weekday") == "Sun"),
            None
        )

        return {
            "moderate_pollen_count": moderate_count,
            "high_pollen_count": high_count,
            "extreme_pollen_count": extreme_count,
            "summary_level": overall_summary,
            "saturday_summary_level": saturday_level,
            "sunday_summary_level": sunday_level,
        }
        
    def _extract_melbourne_data(self, soup: BeautifulSoup, gauge_data: dict[str, str]) -> dict[str, Any]:
        """Extract Melbourne-specific regional data."""
        try:
            # Get last updated values
            pollen_notice = soup.select_one("#district-pollen-div .ta-notice")
            asthma_notices = soup.select("#tae-div .ta-notice")

            pollen_data_regional_today = {
                "last_updated_message": (
                    pollen_notice.get_text(strip=True) if pollen_notice else "Not found"
                ),
                "regional_data": [],
            }

            asthma_data_regional_today = {
                "last_updated_message": (
                    asthma_notices[1].get_text(strip=True)
                    if len(asthma_notices) >= 2
                    else "Updated time not found."
                ),
                "regional_data": [],
            }

            # Define CSS selectors for data tables
            selectors = {
                "pollen": "div.forecast-card .uk-grid-match.uk-child-width-1-2.uk-text-center.ta-forecast-cell.uk-grid",
                "asthma": "#tae-div div.uk-grid-match.uk-child-width-1-2",
            }

            # Extract regional data
            for data_type, selector in selectors.items():
                elements = soup.select(selector)
                for div_element in elements:
                    day_element = div_element.find("div", class_="forecast-day")
                    value_element = div_element.find("div", class_="forecast-value")

                    if day_element and value_element:
                        data_dict = {
                            "region": day_element.text.strip(),
                            "value": value_element.text.strip(),
                        }

                        if data_type == "pollen":
                            pollen_data_regional_today["regional_data"].append(data_dict)
                        else:
                            asthma_data_regional_today["regional_data"].append(data_dict)

            # Add gauge data to regional pollen data
            pollen_data_regional_today["regional_data"].append({
                "region": gauge_data.get("gauge_site", "Melbourne"),
                "value": gauge_data.get("gauge_value", "Unknown"),
            })

            return {
                "asthma_data_regional_today": asthma_data_regional_today,
                "pollen_data_regional_today": pollen_data_regional_today,
            }
            
        except Exception as err:
            _LOGGER.warning("Error extracting Melbourne data: %s", err)
            return {}