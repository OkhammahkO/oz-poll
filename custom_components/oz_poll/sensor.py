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
        vol.Optional("url_api"): cv.url,
        vol.Required("i_subscribe_and_support", default=False): bool,
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
    i_subscribe_and_support = config.get("i_subscribe_and_support", False)

    if i_subscribe_and_support:
        url_api = config.get("url_api")
    else:
        url_api = None

    add_entities([OzPollSensor(url_website, url_api, i_subscribe_and_support)])


class OzPollSensor(SensorEntity):
    def __init__(self, url_website, url_api, i_subscribe_and_support):
        """Initialize the sensor."""
        self._url_website = url_website  # Assign the website URL to the instance
        self._url_api = url_api  # Assign the API URL to the instance
        self._i_subscribe_and_support = i_subscribe_and_support
        self._attr_name = "Oz Poll Allergy Forecast"
        self._attr_native_value = STATE_UNKNOWN
        self._attr_extra_state_attributes = {}
        self.update()

    def update(self) -> None:
        self._attr_native_value = STATE_UNKNOWN
        try:
            # Website scrape section
            # Send an HTTP GET request to the website
            website_response = requests.get(self._url_website, timeout=10)
            website_soup = BeautifulSoup(website_response.text, "html.parser")

            # Extract Forecast Date, Website Last Updated, and Pollen Forecast Today Melbourne Grass
            website_value_date = website_soup.select_one("#pdate.pollen-date").get_text(
                strip=True
            )
            website_last_updated = website_soup.select_one(
                "#district-pollen-div .ta-notice"
            ).get_text(strip=True)
            website_value_melbourne = website_soup.select_one("#plevel").get_text(
                strip=True
            )

            # Initialize empty lists to store the extracted values
            pollen_data_regional_today = []
            asthma_data_regional_today = []

            # Define CSS selectors for both pollen and asthma data tables
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

            # Append Melbourne's pollen data to the list (since that's not in the tables)
            pollen_data_regional_today.append(
                {
                    "region": "Melbourne",  # Set the region to Melbourne
                    "value": website_value_melbourne,  # Use website_value_melbourne as the value
                }
            )

            data_web = {
                "allergy_forecast_web": {
                    "last_updated_description": website_last_updated,
                    "date": website_value_date,
                    "asthma_data_regional_today": asthma_data_regional_today,
                    "pollen_data_regional_today": pollen_data_regional_today,
                }
            }
            self._attr_extra_state_attributes = {**data_web}

            # Rest of the code for retrieving and processing main API data
            if self._i_subscribe_and_support:
                try:
                    url = self._url_api
                    response = requests.get(url, timeout=10)

                    # Check if the request was successful
                    if response.status_code == 200:
                        forecast_result_node = response.json()["forecast_result"]
                        forecast_result_bs = BeautifulSoup(
                            forecast_result_node, "html.parser"
                        )
                        pro_feature_div = forecast_result_bs.find(
                            "div", id="pro_feature", class_="pro_feature"
                        )

                        forecast_location_description_div = pro_feature_div.find(
                            "div", text=lambda text: text and "Allergy Forecast" in text
                        )
                        if forecast_location_description_div:
                            # Do something with the selected div, for example, print its text
                            forecast_location_description = (
                                forecast_location_description_div.text.strip()
                            )

                        data_list = []
                        forecast_day = 1
                        first_forecast_summary_level = None
                        saturday_summary_level = None
                        sunday_summary_level = None
                        for li in pro_feature_div.find_all("li"):
                            date_and_weekday = {
                                "date": li.find("p").get_text(
                                    strip=True
                                ),  # Date in "p"
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
                                    style_parts = [
                                        part.strip() for part in style.split(";")
                                    ]
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
                                        background_value_cleaned = (
                                            background_value_map.get(
                                                background_value, "NeedsMapping"
                                            )
                                        )

                                        pollen[
                                            "pollen_level"
                                        ] = background_value_cleaned

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
                        forecast_7d_summary = {
                            "moderate_pollen_count": moderate_pollen_count,
                            "high_pollen_count": high_pollen_count,
                            "extreme_pollen_count": extreme_pollen_count,
                            "summary_level": overall_summary_level,
                            "saturday_summary_level": saturday_summary_level,
                            "sunday_summary_level": sunday_summary_level,
                        }

                        # Create the forecast description for the 7-day forecast
                        forecast_7d_description = f"The 7 day pollen outlook level is {forecast_7d_summary['summary_level']}. "
                        forecast_7d_description += f"There are {forecast_7d_summary['moderate_pollen_count']} moderate days, "
                        forecast_7d_description += f"{forecast_7d_summary['high_pollen_count']} high days, and "
                        forecast_7d_description += f"{forecast_7d_summary['extreme_pollen_count']} extreme days. "
                        forecast_7d_description += f"Tomorrow is {data_list[1]['summary_stats']['summary_level']}. "

                        for day in data_list:
                            if day["weekday"] == "Sat":
                                forecast_7d_description += f"Saturday is {day['summary_stats']['summary_level']}. "
                                break

                        for day in data_list:
                            if day["weekday"] == "Sun":
                                forecast_7d_description += f"Sunday is {day['summary_stats']['summary_level']}."

                        current_time = datetime.now().strftime(
                            "%d-%m-%Y %H:%M:%S"
                        )  # Updated time

                        # Create the summary description for today's pollen forecast
                        # data_list = data_list  # Assuming you already have data_list
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

                        today_summary_description = (
                            f"Today's pollen forecast is {summary_level}. "
                        )

                        if extreme_pollen:
                            today_summary_description += f"The following pollen types have extreme levels: {', '.join(extreme_pollen)}. "

                        if high_pollen:
                            today_summary_description += f"The following pollen types have high levels: {', '.join(high_pollen)}. "

                        if moderate_pollen:
                            today_summary_description += f"The following pollen types have moderate levels: {', '.join(moderate_pollen)}."

                        data_api = {
                            "allergy_forecast_api": {
                                "last_updated": current_time,
                                "forecast_location_description": forecast_location_description,
                                "today_summary_description": today_summary_description,
                                "forecast_7d_description": forecast_7d_description,
                                "forecast_7d_summary": forecast_7d_summary,
                                "forecast_days": data_list,
                            }
                        }

                        self._attr_extra_state_attributes = {**data_api, **data_web}
                        # Sensor value is today's summary level.
                        self._attr_native_value = first_forecast_summary_level

                except requests.RequestException:
                    self._attr_native_value = STATE_UNKNOWN

            if self._i_subscribe_and_support:
                # Sensor value is today's summary level when _i_subscribe_and_support is True.
                self._attr_native_value = first_forecast_summary_level
            else:
                # Sensor value is website_value_melbourne when _i_subscribe_and_support is False.
                self._attr_native_value = website_value_melbourne

        except requests.RequestException:
            self._attr_native_value = STATE_UNKNOWN

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        await self.async_update()

    async def async_update(self):
        await self.hass.async_add_executor_job(self.update)
