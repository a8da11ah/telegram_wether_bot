import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")

if not TELEGRAM_BOT_TOKEN or not WEATHER_API_KEY:
    raise ValueError("Missing required environment variables! Please set TELEGRAM_BOT_TOKEN and WEATHER_API_KEY in your .env file.")

# API URLs
WEATHER_API_URL = "https://api.openweathermap.org/data/2.5/weather"
FORECAST_API_URL = "https://api.openweathermap.org/data/2.5/forecast"
GEOCODING_API_URL = "https://api.openweathermap.org/geo/1.0/direct"

# Other configurations
DEFAULT_UNIT = "metric"
DEFAULT_LANGUAGE = "en"
MAX_FAVORITES = 10
MAX_COMPARE_CITIES = 4
REQUEST_TIMEOUT = 10