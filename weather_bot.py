from dotenv import load_dotenv
load_dotenv()
import os
import requests
import logging
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from dataclasses import dataclass

# Load environment variables
load_dotenv()

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")

# Validate environment variables
if not TELEGRAM_BOT_TOKEN or not WEATHER_API_KEY:
    logger.error("Missing required environment variables!")
    logger.error("Please set TELEGRAM_BOT_TOKEN and WEATHER_API_KEY")
    exit(1)

# API URLs
WEATHER_API_URL = "https://api.openweathermap.org/data/2.5/weather"
FORECAST_API_URL = "https://api.openweathermap.org/data/2.5/forecast"
GEOCODING_API_URL = "https://api.openweathermap.org/geo/1.0/direct"

@dataclass
class UserPreferences:
    """User preferences data class"""
    unit: str = "metric"  # metric, imperial
    language: str = "en"
    favorites: List[str] = None
    default_city: str = None
    
    def __post_init__(self):
        if self.favorites is None:
            self.favorites = []

class WeatherBot:
    def __init__(self):
        self.application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        self.user_preferences: Dict[int, UserPreferences] = {}
        self.setup_handlers()
        self.load_user_data()
    
    def setup_handlers(self):
        """Set up command and message handlers"""
        # Command handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("weather", self.weather_command))
        self.application.add_handler(CommandHandler("forecast", self.forecast_command))
        self.application.add_handler(CommandHandler("search", self.search_cities))
        self.application.add_handler(CommandHandler("favorites", self.favorites_command))
        self.application.add_handler(CommandHandler("addfav", self.add_favorite))
        self.application.add_handler(CommandHandler("removefav", self.remove_favorite))
        self.application.add_handler(CommandHandler("settings", self.settings_command))
        self.application.add_handler(CommandHandler("alerts", self.weather_alerts))
        self.application.add_handler(CommandHandler("compare", self.compare_cities))
        self.application.add_handler(CommandHandler("map", self.weather_map))
        
        # Callback query handler for inline keyboards
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))
        
        # Message handler for city names
        self.application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND, 
            self.handle_city_message
        ))
    
    def load_user_data(self):
        """Load user preferences from file"""
        try:
            if os.path.exists('user_preferences.json'):
                with open('user_preferences.json', 'r') as f:
                    data = json.load(f)
                    for user_id, prefs in data.items():
                        self.user_preferences[int(user_id)] = UserPreferences(**prefs)
        except Exception as e:
            logger.error(f"Error loading user data: {e}")
    
    def save_user_data(self):
        """Save user preferences to file"""
        try:
            data = {}
            for user_id, prefs in self.user_preferences.items():
                data[str(user_id)] = {
                    'unit': prefs.unit,
                    'language': prefs.language,
                    'favorites': prefs.favorites,
                    'default_city': prefs.default_city
                }
            with open('user_preferences.json', 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving user data: {e}")
    
    def get_user_prefs(self, user_id: int) -> UserPreferences:
        """Get user preferences or create default"""
        if user_id not in self.user_preferences:
            self.user_preferences[user_id] = UserPreferences()
        return self.user_preferences[user_id]
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        keyboard = [
            [InlineKeyboardButton("🌤️ Current Weather", callback_data="help_weather")],
            [InlineKeyboardButton("📊 5-Day Forecast", callback_data="help_forecast")],
            [InlineKeyboardButton("🔍 Search Cities", callback_data="help_search")],
            [InlineKeyboardButton("⭐ Favorites", callback_data="help_favorites")],
            [InlineKeyboardButton("⚙️ Settings", callback_data="help_settings")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        welcome_message = (
            "🌤️ <b>Welcome to Advanced Weather Bot!</b> 🌤️\n\n"
            "I'm your comprehensive weather assistant with many features:\n\n"
            "🔹 Current weather for any city\n"
            "🔹 5-day detailed forecasts\n"
            "🔹 City search and suggestions\n"
            "🔹 Favorite locations\n"
            "🔹 Weather alerts\n"
            "🔹 City comparisons\n"
            "🔹 Customizable units & settings\n\n"
            "Choose a category below or type a city name to get started!"
        )
        await update.message.reply_text(welcome_message, parse_mode='HTML', reply_markup=reply_markup)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_message = (
            "🆘 <b>Weather Bot Commands</b>\n\n"
            "📍 <b>Weather Commands:</b>\n"
            "• <code>/weather [city]</code> - Current weather\n"
            "• <code>/forecast [city]</code> - 5-day forecast\n"
            "• <code>/alerts [city]</code> - Weather alerts\n\n"
            "🔍 <b>Search & Discovery:</b>\n"
            "• <code>/search [query]</code> - Find cities\n"
            "• <code>/map [city]</code> - Weather map link\n"
            "• <code>/compare city1,city2</code> - Compare cities\n\n"
            "⭐ <b>Favorites:</b>\n"
            "• <code>/favorites</code> - Show favorite cities\n"
            "• <code>/addfav [city]</code> - Add to favorites\n"
            "• <code>/removefav [city]</code> - Remove favorite\n\n"
            "⚙️ <b>Settings:</b>\n"
            "• <code>/settings</code> - Change preferences\n\n"
            "💡 <b>Tips:</b>\n"
            "• Just type a city name for quick weather\n"
            "• Use quotes for cities with spaces: 'New York'\n"
            "• Set a default city in settings"
        )
        await update.message.reply_text(help_message, parse_mode='HTML')
    
    async def weather_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /weather command"""
        user_id = update.effective_user.id
        prefs = self.get_user_prefs(user_id)
        
        if not context.args:
            if prefs.default_city:
                city = prefs.default_city
            else:
                await update.message.reply_text(
                    "Please specify a city! Usage: <code>/weather [city]</code>\n"
                    "Example: <code>/weather London</code>\n"
                    "Or set a default city in /settings", parse_mode='HTML'
                )
                return
        else:
            city = " ".join(context.args)
        
        await self.get_and_send_weather(update, city, prefs)
    
    async def forecast_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /forecast command"""
        user_id = update.effective_user.id
        prefs = self.get_user_prefs(user_id)
        
        if not context.args:
            if prefs.default_city:
                city = prefs.default_city
            else:
                await update.message.reply_text(
                    "Please specify a city! Usage: <code>/forecast [city]</code>\n"
                    "Example: <code>/forecast Tokyo</code>", parse_mode='HTML'
                )
                return
        else:
            city = " ".join(context.args)
        
        await self.get_and_send_forecast(update, city, prefs)
    
    async def search_cities(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Search for cities"""
        if not context.args:
            await update.message.reply_text(
                "Please provide a search query! Usage: <code>/search [query]</code>\n"
                "Example: <code>/search paris</code>", parse_mode='HTML'
            )
            return
        
        query = " ".join(context.args)
        await self.search_and_show_cities(update, query)
    
    async def favorites_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show favorite cities"""
        user_id = update.effective_user.id
        prefs = self.get_user_prefs(user_id)
        
        if not prefs.favorites:
            await update.message.reply_text(
                "You don't have any favorite cities yet!\n"
                "Add some using <code>/addfav [city]</code>", parse_mode='HTML'
            )
            return
        
        keyboard = []
        for city in prefs.favorites[:10]:  # Limit to 10 favorites
            keyboard.append([InlineKeyboardButton(f"🌤️ {city}", callback_data=f"weather_{city}")])
        
        keyboard.append([InlineKeyboardButton("⚙️ Manage Favorites", callback_data="manage_favorites")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = f"⭐ <b>Your Favorite Cities ({len(prefs.favorites)})</b>\n\nClick on any city to get current weather:"
        await update.message.reply_text(message, parse_mode='HTML', reply_markup=reply_markup)
    
    async def add_favorite(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Add city to favorites"""
        if not context.args:
            await update.message.reply_text(
                "Please specify a city! Usage: <code>/addfav [city]</code>", parse_mode='HTML'
            )
            return
        
        city = " ".join(context.args)
        user_id = update.effective_user.id
        prefs = self.get_user_prefs(user_id)
        
        # Verify city exists
        if not await self.verify_city_exists(city):
            await update.message.reply_text(f"🚫 City '{city}' not found. Please check the spelling.")
            return
        
        if city.lower() not in [fav.lower() for fav in prefs.favorites]:
            prefs.favorites.append(city)
            self.save_user_data()
            await update.message.reply_text(f"⭐ Added '{city}' to your favorites!")
        else:
            await update.message.reply_text(f"'{city}' is already in your favorites!")
    
    async def remove_favorite(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Remove city from favorites"""
        if not context.args:
            await update.message.reply_text(
                "Please specify a city! Usage: <code>/removefav [city]</code>", parse_mode='HTML'
            )
            return
        
        city = " ".join(context.args)
        user_id = update.effective_user.id
        prefs = self.get_user_prefs(user_id)
        
        # Find and remove city (case insensitive)
        for fav in prefs.favorites[:]:
            if fav.lower() == city.lower():
                prefs.favorites.remove(fav)
                self.save_user_data()
                await update.message.reply_text(f"🗑️ Removed '{fav}' from favorites!")
                return
        
        await update.message.reply_text(f"'{city}' is not in your favorites!")
    
    async def settings_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show settings menu"""
        user_id = update.effective_user.id
        prefs = self.get_user_prefs(user_id)
        
        keyboard = [
            [InlineKeyboardButton(f"🌡️ Units: {'Celsius' if prefs.unit == 'metric' else 'Fahrenheit'}", callback_data="toggle_units")],
            [InlineKeyboardButton(f"🏠 Default City: {prefs.default_city or 'None'}", callback_data="set_default_city")],
            [InlineKeyboardButton("⭐ Manage Favorites", callback_data="manage_favorites")],
            [InlineKeyboardButton("🗑️ Reset All Settings", callback_data="reset_settings")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = (
            "⚙️ <b>Settings</b>\n\n"
            f"🌡️ Temperature Unit: {'Celsius (°C)' if prefs.unit == 'metric' else 'Fahrenheit (°F)'}\n"
            f"🏠 Default City: {prefs.default_city or 'Not set'}\n"
            f"⭐ Favorite Cities: {len(prefs.favorites)}\n\n"
            "Click the buttons below to change settings:"
        )
        await update.message.reply_text(message, parse_mode='HTML', reply_markup=reply_markup)
    
    async def weather_alerts(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show weather alerts for a city"""
        user_id = update.effective_user.id
        prefs = self.get_user_prefs(user_id)
        
        if not context.args:
            if prefs.default_city:
                city = prefs.default_city
            else:
                await update.message.reply_text(
                    "Please specify a city! Usage: <code>/alerts [city]</code>", parse_mode='HTML'
                )
                return
        else:
            city = " ".join(context.args)
        
        try:
            # Get weather data to check for alerts
            params = {
                'q': city,
                'appid': WEATHER_API_KEY,
                'units': prefs.unit
            }
            
            response = requests.get(WEATHER_API_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            alerts = []
            
            # Check for extreme conditions
            temp = data['main']['temp']
            humidity = data['main']['humidity']
            wind_speed = data.get('wind', {}).get('speed', 0)
            weather_id = data['weather'][0]['id']
            
            if prefs.unit == 'metric':
                if temp > 35:
                    alerts.append("🔥 Extreme Heat Warning")
                elif temp < -10:
                    alerts.append("🧊 Extreme Cold Warning")
                if wind_speed > 10:
                    alerts.append("💨 High Wind Alert")
            else:
                if temp > 95:
                    alerts.append("🔥 Extreme Heat Warning")
                elif temp < 14:
                    alerts.append("🧊 Extreme Cold Warning")
                if wind_speed > 22:
                    alerts.append("💨 High Wind Alert")
            
            if humidity > 85:
                alerts.append("💧 High Humidity Alert")
            
            if weather_id < 300:
                alerts.append("⛈️ Thunderstorm Alert")
            elif weather_id < 600 and weather_id >= 500:
                alerts.append("🌧️ Heavy Rain Alert")
            elif weather_id < 700 and weather_id >= 600:
                alerts.append("❄️ Snow Alert")
            
            city_name = f"{data['name']}, {data['sys']['country']}"
            
            if alerts:
                message = f"⚠️ <b>Weather Alerts for {city_name}</b>\n\n"
                message += "\n".join(f"• {alert}" for alert in alerts)
                message += f"\n\n🌡️ Current temp: {temp}°{'C' if prefs.unit == 'metric' else 'F'}"
            else:
                message = f"✅ <b>No Weather Alerts for {city_name}</b>\n\nCurrent conditions are normal."
            
            await update.message.reply_text(message, parse_mode='HTML')
            
        except Exception as e:
            logger.error(f"Error getting alerts: {e}")
            await update.message.reply_text("❌ Could not fetch weather alerts. Please try again later.")
    
    async def compare_cities(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Compare weather between cities"""
        if not context.args:
            await update.message.reply_text(
                "Please specify cities to compare!\n"
                "Usage: <code>/compare city1,city2</code>\n"
                "Example: <code>/compare London,Paris</code>", parse_mode='HTML'
            )
            return
        
        cities_input = " ".join(context.args)
        cities = [city.strip() for city in cities_input.split(',')]
        
        if len(cities) < 2:
            await update.message.reply_text(
                "Please specify at least 2 cities separated by commas!\n"
                "Example: <code>/compare London,Paris</code>", parse_mode='HTML'
            )
            return
        
        if len(cities) > 4:
            await update.message.reply_text("You can compare up to 4 cities at once!")
            cities = cities[:4]
        
        user_id = update.effective_user.id
        prefs = self.get_user_prefs(user_id)
        
        await self.compare_weather(update, cities, prefs)
    
    async def weather_map(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Provide weather map link"""
        if not context.args:
            await update.message.reply_text(
                "Please specify a city! Usage: <code>/map [city]</code>", parse_mode='HTML'
            )
            return
        
        city = " ".join(context.args)
        
        # Get city coordinates
        try:
            params = {
                'q': city,
                'appid': WEATHER_API_KEY,
                'limit': 1
            }
            
            response = requests.get(GEOCODING_API_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if not data:
                await update.message.reply_text(f"🚫 City '{city}' not found.")
                return
            
            lat = data[0]['lat']
            lon = data[0]['lon']
            name = data[0]['name']
            country = data[0].get('country', '')
            
            # Create map links
            openweather_map = f"https://openweathermap.org/weathermap?basemap=map&cities=true&layer=temperature&lat={lat}&lon={lon}&zoom=10"
            google_maps = f"https://www.google.com/maps/@{lat},{lon},10z"
            
            keyboard = [
                [InlineKeyboardButton("🗺️ OpenWeather Map", url=openweather_map)],
                [InlineKeyboardButton("📍 Google Maps", url=google_maps)]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            message = f"🗺️ <b>Weather Maps for {name}, {country}</b>\n\nClick the links below to view interactive weather maps:"
            await update.message.reply_text(message, parse_mode='HTML', reply_markup=reply_markup)
            
        except Exception as e:
            logger.error(f"Error getting map: {e}")
            await update.message.reply_text("❌ Could not generate map links. Please try again later.")
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline keyboard callbacks"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        user_id = update.effective_user.id
        prefs = self.get_user_prefs(user_id)
        
        if data.startswith("weather_"):
            city = data.replace("weather_", "")
            await self.get_and_send_weather(update, city, prefs, edit_message=True)
        
        elif data == "toggle_units":
            prefs.unit = "imperial" if prefs.unit == "metric" else "metric"
            self.save_user_data()
            await self.settings_command(update, context)
        
        elif data == "set_default_city":
            await query.edit_message_text(
                "🏠 To set a default city, use the command:\n"
                "<code>/addfav [city]</code> then come back to settings.\n\n"
                "Or just type a city name and I'll remember it!",
                parse_mode='HTML'
            )
        
        elif data == "manage_favorites":
            if not prefs.favorites:
                await query.edit_message_text(
                    "You don't have any favorite cities yet!\n"
                    "Add some using <code>/addfav [city]</code>",
                    parse_mode='HTML'
                )
                return
            
            keyboard = []
            for city in prefs.favorites:
                keyboard.append([InlineKeyboardButton(f"🗑️ Remove {city}", callback_data=f"removefav_{city}")])
            
            keyboard.append([InlineKeyboardButton("⬅️ Back to Settings", callback_data="back_to_settings")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "⭐ <b>Manage Favorite Cities</b>\n\nClick to remove a city:",
                parse_mode='HTML',
                reply_markup=reply_markup
            )
        
        elif data.startswith("removefav_"):
            city = data.replace("removefav_", "")
            if city in prefs.favorites:
                prefs.favorites.remove(city)
                self.save_user_data()
            await self.handle_callback(update, context)  # Refresh the list
        
        elif data == "back_to_settings":
            await self.settings_command(update, context)
        
        elif data == "reset_settings":
            self.user_preferences[user_id] = UserPreferences()
            self.save_user_data()
            await query.edit_message_text("✅ All settings have been reset to default!")
    
    async def handle_city_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle direct city name messages"""
        city = update.message.text.strip().strip('"\'')
        user_id = update.effective_user.id
        prefs = self.get_user_prefs(user_id)
        
        # Auto-add frequently searched cities to favorites
        if city.lower() not in [fav.lower() for fav in prefs.favorites] and len(prefs.favorites) < 5:
            if await self.verify_city_exists(city):
                keyboard = [[InlineKeyboardButton("⭐ Add to Favorites", callback_data=f"addfav_{city}")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await self.get_and_send_weather(update, city, prefs, suggest_favorite=reply_markup)
            else:
                await self.get_and_send_weather(update, city, prefs)
        else:
            await self.get_and_send_weather(update, city, prefs)
    
    async def verify_city_exists(self, city: str) -> bool:
        """Verify if a city exists"""
        try:
            params = {
                'q': city,
                'appid': WEATHER_API_KEY,
                'units': 'metric'
            }
            response = requests.get(WEATHER_API_URL, params=params, timeout=5)
            return response.status_code == 200
        except:
            return False
    
    async def search_and_show_cities(self, update: Update, query: str):
        """Search for cities and show results"""
        try:
            await update.message.reply_chat_action(action="typing")
            
            params = {
                'q': query,
                'appid': WEATHER_API_KEY,
                'limit': 10
            }
            
            response = requests.get(GEOCODING_API_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if not data:
                await update.message.reply_text(f"🚫 No cities found matching '{query}'")
                return
            
            keyboard = []
            message = f"🔍 <b>Cities matching '{query}':</b>\n\n"
            
            for i, city in enumerate(data[:8], 1):
                name = city['name']
                country = city.get('country', '')
                state = city.get('state', '')
                
                full_name = f"{name}, {country}"
                if state and state != name:
                    full_name = f"{name}, {state}, {country}"
                
                message += f"{i}. {full_name}\n"
                keyboard.append([InlineKeyboardButton(f"🌤️ {full_name}", callback_data=f"weather_{name}")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(message, parse_mode='HTML', reply_markup=reply_markup)
            
        except Exception as e:
            logger.error(f"Error searching cities: {e}")
            await update.message.reply_text("❌ Could not search for cities. Please try again later.")
    
    async def get_and_send_weather(self, update: Update, city: str, prefs: UserPreferences, edit_message: bool = False, suggest_favorite=None):
        """Fetch weather data and send response"""
        try:
            if not edit_message:
                await update.message.reply_chat_action(action="typing")
            
            # Make API request
            params = {
                'q': city,
                'appid': WEATHER_API_KEY,
                'units': prefs.unit
            }
            
            response = requests.get(WEATHER_API_URL, params=params, timeout=10)
            
            if response.status_code == 404:
                message = f"🚫 City '{city}' not found. Please check the spelling and try again."
                if edit_message:
                    await update.callback_query.edit_message_text(message)
                else:
                    await update.message.reply_text(message)
                return
            
            response.raise_for_status()
            data = response.json()
            
            # Format weather information
            weather_message = self.format_weather_message(data, prefs)
            
            if edit_message:
                await update.callback_query.edit_message_text(weather_message, parse_mode='HTML')
            else:
                await update.message.reply_text(weather_message, parse_mode='HTML', reply_markup=suggest_favorite)
            
        except requests.exceptions.Timeout:
            message = "⏰ Request timeout. Please try again later."
            if edit_message:
                await update.callback_query.edit_message_text(message)
            else:
                await update.message.reply_text(message)
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            message = "❌ Sorry, I couldn't fetch weather data right now. Please try again later."
            if edit_message:
                await update.callback_query.edit_message_text(message)
            else:
                await update.message.reply_text(message)
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            message = "❌ An unexpected error occurred. Please try again."
            if edit_message:
                await update.callback_query.edit_message_text(message)
            else:
                await update.message.reply_text(message)
    
    async def get_and_send_forecast(self, update: Update, city: str, prefs: UserPreferences):
        """Fetch and send 5-day weather forecast"""
        try:
            await update.message.reply_chat_action(action="typing")
            
            params = {
                'q': city,
                'appid': WEATHER_API_KEY,
                'units': prefs.unit
            }
            
            response = requests.get(FORECAST_API_URL, params=params, timeout=10)
            
            if response.status_code == 404:
                await update.message.reply_text(f"🚫 City '{city}' not found.")
                return
            
            response.raise_for_status()
            data = response.json()
            
            forecast_message = self.format_forecast_message(data, prefs)
            await update.message.reply_text(forecast_message, parse_mode='HTML')
            
        except Exception as e:
            logger.error(f"Error getting forecast: {e}")
            await update.message.reply_text("❌ Could not fetch forecast data. Please try again later.")
    
    async def compare_weather(self, update: Update, cities: List[str], prefs: UserPreferences):
        """Compare weather between multiple cities"""
        try:
            await update.message.reply_chat_action(action="typing")
            
            weather_data = []
            
            for city in cities:
                params = {
                    'q': city,
                    'appid': WEATHER_API_KEY,
                    'units': prefs.unit
                }
                
                response = requests.get(WEATHER_API_URL, params=params, timeout=10)
                if response.status_code == 200:
                    weather_data.append(response.json())
                else:
                    await update.message.reply_text(f"🚫 City '{city}' not found.")
                    return
            
            if not weather_data:
                await update.message.reply_text("❌ Could not fetch data for any cities.")
                return
            
            # Format comparison message
            unit_symbol = "°C" if prefs.unit == "metric" else "°F"
            speed_unit = "m/s" if prefs.unit == "metric" else "mph"
            
            message = "🏆 <b>Weather Comparison</b>\n\n"
            
            # Temperature comparison
            temps = [(data['name'], data['main']['temp']) for data in weather_data]
            temps.sort(key=lambda x: x[1], reverse=True)
            
            message += f"🌡️ <b>Temperature ({unit_symbol})</b>\n"
            for i, (name, temp) in enumerate(temps, 1):
                emoji = "🔥" if i == 1 else "🧊" if i == len(temps) else "🌡️"
                message += f"{i}. {emoji} {name}: {temp:.1f}{unit_symbol}\n"
            
            message += "\n"
            
            # Humidity comparison
            humidities = [(data['name'], data['main']['humidity']) for data in weather_data]
            humidities.sort(key=lambda x: x[1], reverse=True)
            
            message += "💧 <b>Humidity (%)</b>\n"
            for i, (name, humidity) in enumerate(humidities, 1):
                emoji = "💧" if i == 1 else "🏜️" if i == len(humidities) else "💨"
                message += f"{i}. {emoji} {name}: {humidity}%\n"
            
            message += "\n"
            
            # Weather conditions
            message += "☁️ <b>Current Conditions</b>\n"
            for data in weather_data:
                name = data['name']
                condition = data['weather'][0]['description'].title()
                emoji = self.get_weather_emoji(data['weather'][0]['id'])
                message += f"{emoji} {name}: {condition}\n"
            
            # Find extremes
            message += "\n🏅 <b>Highlights</b>\n"
            hottest = max(weather_data, key=lambda x: x['main']['temp'])
            coldest = min(weather_data, key=lambda x: x['main']['temp'])
            most_humid = max(weather_data, key=lambda x: x['main']['humidity'])
            
            message += f"🔥 Hottest: {hottest['name']} ({hottest['main']['temp']:.1f}{unit_symbol})\n"
            message += f"🧊 Coldest: {coldest['name']} ({coldest['main']['temp']:.1f}{unit_symbol})\n"
            message += f"💧 Most Humid: {most_humid['name']} ({most_humid['main']['humidity']}%)"
            
            await update.message.reply_text(message, parse_mode='HTML')
            
        except Exception as e:
            logger.error(f"Error comparing weather: {e}")
            await update.message.reply_text("❌ Could not compare weather data. Please try again later.")
    
    def format_weather_message(self, data, prefs: UserPreferences):
        """Format weather data into a nice message"""
        city = data['name']
        country = data['sys']['country']
        temp = data['main']['temp']
        feels_like = data['main']['feels_like']
        humidity = data['main']['humidity']
        pressure = data['main']['pressure']
        description = data['weather'][0]['description'].title()
        
        # Get additional data
        wind_speed = data.get('wind', {}).get('speed', 0)
        wind_deg = data.get('wind', {}).get('deg', 0)
        visibility = data.get('visibility', 0) / 1000 if data.get('visibility') else None
        clouds = data.get('clouds', {}).get('all', 0)
        
        # Sunrise/sunset
        sunrise = datetime.fromtimestamp(data['sys']['sunrise']).strftime('%H:%M')
        sunset = datetime.fromtimestamp(data['sys']['sunset']).strftime('%H:%M')
        
        # Get weather emoji
        weather_id = data['weather'][0]['id']
        emoji = self.get_weather_emoji(weather_id)
        
        # Format units
        if prefs.unit == 'metric':
            temp_unit = "°C"
            speed_unit = "m/s"
            temp = round(temp)
            feels_like = round(feels_like)
        else:
            temp_unit = "°F"
            speed_unit = "mph"
            temp = round(temp)
            feels_like = round(feels_like)
        
        # Wind direction
        wind_directions = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                          "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
        wind_dir = wind_directions[round(wind_deg / 22.5) % 16] if wind_deg else "N"
        
        message = (
            f"{emoji} <b>Weather in {city}, {country}</b>\n\n"
            f"🌡️ Temperature: {temp}{temp_unit}\n"
            f"🤔 Feels like: {feels_like}{temp_unit}\n"
            f"💧 Humidity: {humidity}%\n"
            f"📊 Pressure: {pressure} hPa\n"
            f"💨 Wind: {wind_speed:.1f} {speed_unit} {wind_dir}\n"
            f"☁️ Cloudiness: {clouds}%\n"
        )
        
        if visibility:
            message += f"👁️ Visibility: {visibility:.1f} km\n"
        
        message += (
            f"📝 Conditions: {description}\n\n"
            f"🌅 Sunrise: {sunrise}\n"
            f"🌇 Sunset: {sunset}"
        )
        
        return message
    
    def format_forecast_message(self, data, prefs: UserPreferences):
        """Format 5-day forecast data"""
        city = data['city']['name']
        country = data['city']['country']
        
        unit_symbol = "°C" if prefs.unit == "metric" else "°F"
        
        message = f"📊 <b>5-Day Forecast for {city}, {country}</b>\n\n"
        
        # Group forecasts by day
        daily_forecasts = {}
        for item in data['list']:
            date = datetime.fromtimestamp(item['dt']).date()
            if date not in daily_forecasts:
                daily_forecasts[date] = []
            daily_forecasts[date].append(item)
        
        # Process up to 5 days
        for i, (date, forecasts) in enumerate(list(daily_forecasts.items())[:5]):
            day_name = date.strftime('%A')
            date_str = date.strftime('%m/%d')
            
            # Get min/max temperatures for the day
            temps = [f['main']['temp'] for f in forecasts]
            min_temp = min(temps)
            max_temp = max(temps)
            
            # Get most common weather condition
            conditions = [f['weather'][0] for f in forecasts]
            main_condition = max(set(c['main'] for c in conditions), 
                               key=[c['main'] for c in conditions].count)
            
            # Find representative weather ID for emoji
            weather_ids = [c['id'] for c in conditions if c['main'] == main_condition]
            representative_id = weather_ids[0] if weather_ids else conditions[0]['id']
            
            emoji = self.get_weather_emoji(representative_id)
            
            # Get precipitation probability if available
            pop = max([f.get('pop', 0) for f in forecasts]) * 100
            
            message += f"{emoji} <b>{day_name} ({date_str})</b>\n"
            message += f"   🌡️ {min_temp:.0f}{unit_symbol} - {max_temp:.0f}{unit_symbol}"
            
            if pop > 20:
                message += f" | 🌧️ {pop:.0f}%"
            
            message += f"\n   📝 {main_condition}\n\n"
        
        return message
    
    def get_weather_emoji(self, weather_id):
        """Get appropriate emoji for weather condition"""
        if weather_id < 300:
            return "⛈️"  # Thunderstorm
        elif weather_id < 400:
            return "🌦️"  # Drizzle
        elif weather_id < 600:
            return "🌧️"  # Rain
        elif weather_id < 700:
            return "❄️"  # Snow
        elif weather_id < 800:
            return "🌫️"  # Atmosphere (fog, mist, etc.)
        elif weather_id == 800:
            return "☀️"  # Clear sky
        else:
            return "☁️"  # Clouds
    
    def run(self):
        """Start the bot"""
        print("🚀 Starting Enhanced Weather Bot...")
        print(f"📊 Loaded preferences for {len(self.user_preferences)} users")
        self.application.run_polling()

# Error handler
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors"""
    logger.warning(f'Update "{update}" caused error "{context.error}"')

if __name__ == '__main__':
    try:
        # Create and run the bot
        bot = WeatherBot()
        bot.application.add_error_handler(error_handler)
        bot.run()
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        print(f"❌ Error: {e}")