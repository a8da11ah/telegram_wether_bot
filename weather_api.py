import requests
import logging
from typing import Dict, Any, Optional
from config import WEATHER_API_KEY, WEATHER_API_URL, FORECAST_API_URL, GEOCODING_API_URL, REQUEST_TIMEOUT

logger = logging.getLogger(__name__)

class WeatherAPI:
    def __init__(self, api_key: str):
        self.api_key = api_key

    async def get_current_weather(self, city: str, unit: str, lang: str) -> Optional[Dict[str, Any]]:
        """Fetches current weather data for a given city."""
        params = {
            'q': city,
            'appid': self.api_key,
            'units': unit,
            'lang': lang
        }
        try:
            response = requests.get(WEATHER_API_URL, params=params, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            logger.error(f"Weather API request timed out for {city}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching current weather for {city}: {e}")
            if response.status_code == 404:
                return {"error": "city_not_found"}
            return None

    async def get_five_day_forecast(self, city: str, unit: str, lang: str) -> Optional[Dict[str, Any]]:
        """Fetches 5-day weather forecast data for a given city."""
        params = {
            'q': city,
            'appid': self.api_key,
            'units': unit,
            'lang': lang
        }
        try:
            response = requests.get(FORECAST_API_URL, params=params, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            logger.error(f"Forecast API request timed out for {city}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching forecast for {city}: {e}")
            if response.status_code == 404:
                return {"error": "city_not_found"}
            return None

    async def get_city_coordinates(self, query: str) -> Optional[list]:
        """Fetches geographical coordinates for a city query."""
        params = {
            'q': query,
            'appid': self.api_key,
            'limit': 10
        }
        try:
            response = requests.get(GEOCODING_API_URL, params=params, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            logger.error(f"Geocoding API request timed out for {query}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching coordinates for {query}: {e}")
            return None

    async def verify_city_exists(self, city: str, lang: str) -> bool:
        """Verifies if a city exists by trying to fetch its current weather."""
        params = {
            'q': city,
            'appid': self.api_key,
            'units': 'metric', # Unit doesn't matter for existence check
            'lang': lang
        }
        try:
            response = requests.get(WEATHER_API_URL, params=params, timeout=5)
            return response.status_code == 200
        except requests.exceptions.RequestException as e:
            logger.error(f"Error verifying city {city}: {e}")
            return False