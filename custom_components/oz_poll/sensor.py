"""Platform for sensor integration."""
from __future__ import annotations
from homeassistant.components.sensor import SensorEntity
from homeassistant.const import STATE_UNKNOWN, CONF_URL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from homeassistant.helpers import config_validation as cv
import voluptuous as vol

SCAN_INTERVAL = timedelta(minutes=63)

PLATFORM_SCHEMA = cv.PLATFORM_SCHEMA.extend(
    {
        vol.Required("url_website"): cv.url,
        vol.Required("url_api"): cv.url,
    }
)


def setup_platform(
    hass: HomeAssistant,
    config: dict,
    add_entities: AddEntitiesCallback,
    discovery_info: dict | None = None,
) -> None:
    """Set up the sensor platform."""
    url_website = config.get("url_website")
    url_api = config.get("url_api")
    add_entities([OzPollSensor(url_website, url_api)])


class OzPollSensor(SensorEntity):
    def __init__(self, url_website, url_api):
        """Initialize the sensor."""
        self._url_website = url_website  # Assign the website URL to the instance
        self._url_api = url_api  # Assign the API URL to the instance
        self._attr_name = "Oz Poll Allergy Forecast"
        self._attr_native_value = STATE_UNKNOWN
        self._attr_extra_state_attributes = {}

    @property
    def forecast_description_7d(self):
        """Generate the 7 day forecast description."""
        description = f"The 7 day pollen outlook level is {self._attr_extra_state_attributes['pollen_forecast']['forecast_summary_7d']['summary_level']}. "
        description += f"There are {self._attr_extra_state_attributes['pollen_forecast']['forecast_summary_7d']['moderate_pollen_count']} moderate days, "
        description += f"{self._attr_extra_state_attributes['pollen_forecast']['forecast_summary_7d']['high_pollen_count']} high days, and "
        description += f"{self._attr_extra_state_attributes['pollen_forecast']['forecast_summary_7d']['extreme_pollen_count']} extreme days. "
        description += f"Tomorrow is {self._attr_extra_state_attributes['pollen_forecast']['forecast_days'][1]['summary_stats']['summary_level']}. "

        for day in self._attr_extra_state_attributes["pollen_forecast"][
            "forecast_days"
        ]:
            if day["weekday"] == "Sat":
                description += f"Saturday is {day['summary_stats']['summary_level']}. "
                break

        for day in self._attr_extra_state_attributes["pollen_forecast"][
            "forecast_days"
        ]:
            if day["weekday"] == "Sun":
                description += f"Sunday is {day['summary_stats']['summary_level']}."

        return description

    @property
    def today_summary_description(self):
        """Generate the summary description for today's pollen forecast."""
        data_list = self._attr_extra_state_attributes["pollen_forecast"][
            "forecast_days"
        ]
        today_data = data_list[0]

        summary_level = today_data["summary_stats"]["summary_level"]
        pollen_data = today_data["pollen_data"]

        extreme_pollen = [
            pollen["pollen_type"]
            for pollen in pollen_data
            if pollen["pollen_level"] == "Extreme"
        ]
        high_pollen = [
            pollen["pollen_type"]
            for pollen in pollen_data
            if pollen["pollen_level"] == "High"
        ]
        moderate_pollen = [
            pollen["pollen_type"]
            for pollen in pollen_data
            if pollen["pollen_level"] == "Moderate"
        ]

        description = f"Today's pollen forecast is {summary_level}. "

        if extreme_pollen:
            description += f"The following pollen types have extreme levels: {', '.join(extreme_pollen)}. "

        if high_pollen:
            description += f"The following pollen types have high levels: {', '.join(high_pollen)}. "

        if moderate_pollen:
            description += f"The following pollen types have moderate levels: {', '.join(moderate_pollen)}."

        return description

    @property
    def asthma_data_regional_today(self):
        """Return the Thunderstorm Asthma forecast data."""
        return self._attr_extra_state_attributes.get("asthma_data_regional_today", [])

    @property
    def pollen_data_regional_today(self):
        """Return the Regional Pollen forecast data."""
        return self._attr_extra_state_attributes.get("pollen_data_regional_today", [])

    def update(self) -> None:
        try:
            # Website scrape section
            # Send an HTTP GET request to the website
            website_response = requests.get(self._url_website, timeout=10)
            website_soup = BeautifulSoup(website_response.text, "html.parser")

            # Select pollen by region table (forecast-card )
            website_pollen_selector = "div.forecast-card .uk-grid-match.uk-child-width-1-2.uk-text-center.ta-forecast-cell.uk-grid"
            div_pollen_elements = website_soup.select(website_pollen_selector)

            # Select Thunderstorm Asthma by region table (tae)
            website_asthma_selector = "#tae-div div.uk-grid-match.uk-child-width-1-2 "
            div_asthma_elements = website_soup.select(website_asthma_selector)

            # Initialize empty lists to store the extracted values
            pollen_data_regional_today = []
            asthma_data_regional_today = []

            # Define CSS selectors for both pollen and asthma data
            selectors = {
                "pollen": "div.forecast-card .uk-grid-match.uk-child-width-1-2.uk-text-center.ta-forecast-cell.uk-grid",
                "asthma": "#tae-div div.uk-grid-match.uk-child-width-1-2",
            }
            # Iterate through the selected elements for pollen and asthma data
            for data_type, selector in selectors.items():
                elements = website_soup.select(selector)

                for div_element in elements:
                    # Find and extract the text from the 'forecast-day' and 'forecast-value' elements
                    day_element = div_element.find("div", class_="forecast-day")
                    value_element = div_element.find("div", class_="forecast-value")

                    data_list = (
                        pollen_data_regional_today
                        if data_type == "pollen"
                        else asthma_data_regional_today
                    )

                    data_list.append(
                        {
                            "region": day_element.text.strip(),
                            "value": value_element.text.strip(),
                        }
                    )

            # Rest of the code for retrieving and processing main API data
            url = self._url_api
            response = requests.get(url, timeout=10)

            # Check if the request was successful
            if response.status_code == 200:
                forecast_result_node = response.json()["forecast_result"]
                forecast_result_bs = BeautifulSoup(forecast_result_node, "html.parser")
                pro_feature_div = forecast_result_bs.find(
                    "div", id="pro_feature", class_="pro_feature"
                )

                allergy_forecast_location_div = pro_feature_div.find(
                    "div", text=lambda text: text and "Allergy Forecast" in text
                )
                if allergy_forecast_location_div:
                    # Do something with the selected div, for example, print its text
                    allergy_forecast_location = (
                        allergy_forecast_location_div.text.strip()
                    )

                data_list = []
                forecast_day = 1
                first_forecast_summary_level = None
                saturday_summary_level = None
                sunday_summary_level = None
                for li in pro_feature_div.find_all("li"):
                    date_and_weekday = {
                        "date": li.find("p").get_text(strip=True),  # Date in "p"
                        "weekday": li.find("h3").get_text(strip=True)[
                            :3
                        ],  # Weekday in "h3". Truncate to three letters
                    }
                    pollen_data = [
                        {"pollen_type": a.get_text(strip=True)}
                        for a in li.find_all("a")  # Pollen type in "a"
                    ]

                    # Pollen severity needs extracting and mapping from grid background colour
                    background_value_map = {
                        "var(--pollen-low-color)": "Low",
                        "var(--pollen-moderate-color)": "Moderate",
                        "var(--pollen-high-color)": "High",
                        "var(--pollen-extreme-color)": "Extreme",
                        "red": "Extreme",  # Workaround mapping for apparent API exception
                        # Add more mappings as needed
                    }

                    for pollen, div in zip(
                        pollen_data,
                        li.find_all("div", class_="uk-first-column"),
                    ):
                        style = div.get("style")
                        if style:
                            # Split the style attribute by semicolon and get the parts
                            style_parts = [part.strip() for part in style.split(";")]
                            # Find the part that starts with "background:"
                            background_part = next(
                                (
                                    part
                                    for part in style_parts
                                    if part.startswith("background:")
                                ),
                                None,
                            )

                            if background_part:
                                # Extract the value after "background: "
                                background_value = background_part.split(
                                    "background: "
                                )[1]
                                # Clean the background value using the map
                                background_value_cleaned = background_value_map.get(
                                    background_value, "NeedsMapping"
                                )

                                pollen["pollen_level"] = background_value_cleaned

                    # Calculate summary statistics for different pollen levels
                    summary_stats = {
                        "low_pollen_count": sum(
                            1
                            for pollen in pollen_data
                            if pollen["pollen_level"] == "Low"
                        ),
                        "moderate_pollen_count": sum(
                            1
                            for pollen in pollen_data
                            if pollen["pollen_level"] == "Moderate"
                        ),
                        "high_pollen_count": sum(
                            1
                            for pollen in pollen_data
                            if pollen["pollen_level"] == "High"
                        ),
                        "extreme_pollen_count": sum(
                            1
                            for pollen in pollen_data
                            if pollen["pollen_level"] == "Extreme"
                        ),
                    }
                    # Determine the overall summary level based on the counts
                    if summary_stats["extreme_pollen_count"] > 0:
                        summary_level = "Extreme"
                    elif summary_stats["high_pollen_count"] > 0:
                        summary_level = "High"
                    elif summary_stats["moderate_pollen_count"] > 0:
                        summary_level = "Moderate"
                    else:
                        summary_level = "Low"
                    summary_stats["summary_level"] = summary_level

                    # Check if Saturday or Sunday and update summary levels accordingly
                    if (
                        saturday_summary_level is None
                        and date_and_weekday["weekday"] == "Sat"
                    ):
                        saturday_summary_level = summary_level
                    if (
                        sunday_summary_level is None
                        and date_and_weekday["weekday"] == "Sun"
                    ):
                        sunday_summary_level = summary_level

                    # Append data for the current forecast day
                    data_list.append(
                        {
                            "forecast_day": str(forecast_day),
                            "date": date_and_weekday["date"],
                            "weekday": date_and_weekday["weekday"],
                            "summary_stats": summary_stats,
                            "pollen_data": pollen_data,
                        }
                    )
                    # Set the first forecast summary level if it's the first day
                    if forecast_day == 1:
                        first_forecast_summary_level = summary_level
                    forecast_day += 1

                # Count the summary levels for the next 7 days
                moderate_pollen_count = sum(
                    1
                    for day in data_list[:7]
                    if day["summary_stats"]["summary_level"] == "Moderate"
                )
                high_pollen_count = sum(
                    1
                    for day in data_list[:7]
                    if day["summary_stats"]["summary_level"] == "High"
                )
                extreme_pollen_count = sum(
                    1
                    for day in data_list[:7]
                    if day["summary_stats"]["summary_level"] == "Extreme"
                )

                # Calculate the overall summary level based on the counts
                overall_summary_level = (
                    "Extreme"
                    if extreme_pollen_count > 0
                    else "High"
                    if high_pollen_count > 0
                    else "Moderate"
                    if moderate_pollen_count > 0
                    else "Low"
                )

                # Create the forecast summary dictionary
                forecast_summary_7d = {
                    "moderate_pollen_count": moderate_pollen_count,
                    "high_pollen_count": high_pollen_count,
                    "extreme_pollen_count": extreme_pollen_count,
                    "summary_level": overall_summary_level,
                    "saturday_summary_level": saturday_summary_level,
                    "sunday_summary_level": sunday_summary_level,
                }

                current_time = datetime.now().strftime(
                    "%d-%m-%Y %H:%M:%S"
                )  # Updated time

                data = {
                    "pollen_forecast": {
                        "last_updated": current_time,
                        "allergy_forecast_location": allergy_forecast_location,
                        "forecast_summary_7d": forecast_summary_7d,
                        "forecast_days": data_list,
                        "asthma_data_regional_today": asthma_data_regional_today,
                        "pollen_data_regional_today": pollen_data_regional_today,
                    }
                }

                # Merge the storm_asthma_forecast_today into self._attr_extra_state_attributes
                self._attr_extra_state_attributes = data
                self._attr_native_value = first_forecast_summary_level
                self._attr_extra_state_attributes[
                    "forecast_description_7d"
                ] = self.forecast_description_7d
                self._attr_extra_state_attributes[
                    "today_summary_description"
                ] = self.today_summary_description
            else:
                self._attr_native_value = STATE_UNKNOWN
        except requests.RequestException:
            self._attr_native_value = STATE_UNKNOWN

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        await self.async_update()

    async def async_update(self):
        await self.hass.async_add_executor_job(self.update)
