import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from data_store import UserDataStore, UserPreferences
from localization import get_localized_message
from weather_api import WeatherAPI
from utils import format_weather_message, format_forecast_message, get_weather_emoji
from config import MAX_FAVORITES, MAX_COMPARE_CITIES

logger = logging.getLogger(__name__)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    user_id = update.effective_user.id
    user_data_store: UserDataStore = context.bot_data['user_data_store']
    prefs = user_data_store.get_user_prefs(user_id)
    
    keyboard = [
        [InlineKeyboardButton(get_localized_message(prefs.language, "current_weather_button"), callback_data="help_weather")],
        [InlineKeyboardButton(get_localized_message(prefs.language, "five_day_forecast_button"), callback_data="help_forecast")],
        [InlineKeyboardButton(get_localized_message(prefs.language, "search_cities_button"), callback_data="help_search")],
        [InlineKeyboardButton(get_localized_message(prefs.language, "favorites_button"), callback_data="help_favorites")],
        [InlineKeyboardButton(get_localized_message(prefs.language, "settings_button"), callback_data="help_settings")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_message = get_localized_message(prefs.language, "welcome")
    await update.message.reply_text(welcome_message, parse_mode='HTML', reply_markup=reply_markup)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    user_id = update.effective_user.id
    user_data_store: UserDataStore = context.bot_data['user_data_store']
    prefs = user_data_store.get_user_prefs(user_id)
    help_message = get_localized_message(prefs.language, "help")
    await update.message.reply_text(help_message, parse_mode='HTML')

async def weather_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /weather command."""
    user_id = update.effective_user.id
    user_data_store: UserDataStore = context.bot_data['user_data_store']
    weather_api_client: WeatherAPI = context.bot_data['weather_api_client']
    prefs = user_data_store.get_user_prefs(user_id)
    
    city = None
    if context.args:
        city = " ".join(context.args)
    elif prefs.default_city:
        city = prefs.default_city
    
    if not city:
        await update.message.reply_text(get_localized_message(prefs.language, "specify_city_weather"), parse_mode='HTML')
        return

    await send_current_weather(update, city, prefs, weather_api_client)

async def forecast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /forecast command."""
    user_id = update.effective_user.id
    user_data_store: UserDataStore = context.bot_data['user_data_store']
    weather_api_client: WeatherAPI = context.bot_data['weather_api_client']
    prefs = user_data_store.get_user_prefs(user_id)
    
    city = None
    if context.args:
        city = " ".join(context.args)
    elif prefs.default_city:
        city = prefs.default_city
    
    if not city:
        await update.message.reply_text(get_localized_message(prefs.language, "specify_city_forecast"), parse_mode='HTML')
        return
    
    await send_five_day_forecast(update, city, prefs, weather_api_client)

async def search_cities(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Search for cities."""
    user_id = update.effective_user.id
    user_data_store: UserDataStore = context.bot_data['user_data_store']
    weather_api_client: WeatherAPI = context.bot_data['weather_api_client']
    prefs = user_data_store.get_user_prefs(user_id)

    if not context.args:
        await update.message.reply_text(get_localized_message(prefs.language, "specify_query_search"), parse_mode='HTML')
        return
    
    query = " ".join(context.args)
    await update.message.reply_chat_action(action="typing")
    
    city_data = await weather_api_client.get_city_coordinates(query)
    
    if not city_data:
        await update.message.reply_text(get_localized_message(prefs.language, "error_searching_cities"))
        return
    
    if not city_data:
        await update.message.reply_text(get_localized_message(prefs.language, "no_cities_found_search", query=query))
        return
    
    keyboard = []
    city_list_str = ""
    
    for i, city_info in enumerate(city_data[:8], 1): # Limit to 8 results
        name = city_info['name']
        country = city_info.get('country', '')
        state = city_info.get('state', '')
        
        full_name = f"{name}, {country}"
        if state and state != name:
            full_name = f"{name}, {state}, {country}"
        
        city_list_str += f"{i}. {full_name}\n"
        keyboard.append([InlineKeyboardButton(f"🌤️ {full_name}", callback_data=f"weather_{name}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    message = get_localized_message(prefs.language, "cities_matching_search", query=query, city_list=city_list_str)
    await update.message.reply_text(message, parse_mode='HTML', reply_markup=reply_markup)

async def favorites_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show favorite cities."""
    user_id = update.effective_user.id
    user_data_store: UserDataStore = context.bot_data['user_data_store']
    prefs = user_data_store.get_user_prefs(user_id)
    
    if not prefs.favorites:
        await update.message.reply_text(get_localized_message(prefs.language, "no_favorites"), parse_mode='HTML')
        return
    
    keyboard = []
    for city in prefs.favorites[:MAX_FAVORITES]:
        keyboard.append([InlineKeyboardButton(f"🌤️ {city}", callback_data=f"weather_{city}")])
    
    keyboard.append([InlineKeyboardButton(get_localized_message(prefs.language, "manage_favorites_button"), callback_data="manage_favorites")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message = get_localized_message(prefs.language, "favorites_list", count=len(prefs.favorites))
    await update.message.reply_text(message, parse_mode='HTML', reply_markup=reply_markup)

async def add_favorite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add city to favorites."""
    user_id = update.effective_user.id
    user_data_store: UserDataStore = context.bot_data['user_data_store']
    weather_api_client: WeatherAPI = context.bot_data['weather_api_client']
    prefs = user_data_store.get_user_prefs(user_id)

    if not context.args:
        await update.message.reply_text(get_localized_message(prefs.language, "specify_city_addfav"), parse_mode='HTML')
        return
    
    city = " ".join(context.args)
    
    if not await weather_api_client.verify_city_exists(city, prefs.language):
        await update.message.reply_text(get_localized_message(prefs.language, "city_not_found", city=city))
        return
    
    if city.lower() not in [fav.lower() for fav in prefs.favorites]:
        prefs.favorites.append(city)
        user_data_store.save_user_data()
        await update.message.reply_text(get_localized_message(prefs.language, "added_favorite", city=city))
    else:
        await update.message.reply_text(get_localized_message(prefs.language, "already_favorite", city=city))

async def remove_favorite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove city from favorites."""
    user_id = update.effective_user.id
    user_data_store: UserDataStore = context.bot_data['user_data_store']
    prefs = user_data_store.get_user_prefs(user_id)

    if not context.args:
        await update.message.reply_text(get_localized_message(prefs.language, "specify_city_removefav"), parse_mode='HTML')
        return
    
    city_to_remove = " ".join(context.args)
    
    found = False
    for fav in prefs.favorites[:]: # Iterate over a copy
        if fav.lower() == city_to_remove.lower():
            prefs.favorites.remove(fav)
            user_data_store.save_user_data()
            await update.message.reply_text(get_localized_message(prefs.language, "removed_favorite", city=fav))
            found = True
            break
    
    if not found:
        await update.message.reply_text(get_localized_message(prefs.language, "not_in_favorites", city=city_to_remove))

async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show settings menu."""
    user_id = update.effective_user.id
    user_data_store: UserDataStore = context.bot_data['user_data_store']
    prefs = user_data_store.get_user_prefs(user_id)
    
    unit_name = get_localized_message(prefs.language, "units_celsius") if prefs.unit == "metric" else get_localized_message(prefs.language, "units_fahrenheit")
    language_name = get_localized_message(prefs.language, prefs.language)
    default_city_name = prefs.default_city or get_localized_message(prefs.language, "default_city_not_set")

    keyboard = [
        [InlineKeyboardButton(get_localized_message(prefs.language, "units_toggle_button", unit_name=unit_name), callback_data="toggle_units")],
        [InlineKeyboardButton(get_localized_message(prefs.language, "language_toggle_button", language_name=language_name), callback_data="choose_language")],
        [InlineKeyboardButton(get_localized_message(prefs.language, "default_city_button", city_name=default_city_name), callback_data="set_default_city")],
        [InlineKeyboardButton(get_localized_message(prefs.language, "manage_favorites_button"), callback_data="manage_favorites")],
        [InlineKeyboardButton(get_localized_message(prefs.language, "reset_settings_button"), callback_data="reset_settings")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message = get_localized_message(
        prefs.language, 
        "settings_menu", 
        unit=unit_name, 
        language=language_name, 
        default_city=default_city_name, 
        fav_count=len(prefs.favorites)
    )
    if update.callback_query: # If triggered by a callback, edit message
        await update.callback_query.edit_message_text(message, parse_mode='HTML', reply_markup=reply_markup)
    else: # If triggered by command
        await update.message.reply_text(message, parse_mode='HTML', reply_markup=reply_markup)

async def weather_alerts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show weather alerts for a city."""
    user_id = update.effective_user.id
    user_data_store: UserDataStore = context.bot_data['user_data_store']
    weather_api_client: WeatherAPI = context.bot_data['weather_api_client']
    prefs = user_data_store.get_user_prefs(user_id)
    
    city = None
    if context.args:
        city = " ".join(context.args)
    elif prefs.default_city:
        city = prefs.default_city
    
    if not city:
        await update.message.reply_text(get_localized_message(prefs.language, "specify_city_alerts"), parse_mode='HTML')
        return
    
    await update.message.reply_chat_action(action="typing")
    weather_data = await weather_api_client.get_current_weather(city, prefs.unit, prefs.language)

    if not weather_data:
        if weather_data and weather_data.get("error") == "city_not_found":
            await update.message.reply_text(get_localized_message(prefs.language, "city_not_found", city=city))
        else:
            await update.message.reply_text(get_localized_message(prefs.language, "error_fetching_alerts"))
        return
    
    alerts = []
    
    temp = weather_data['main']['temp']
    humidity = weather_data['main']['humidity']
    wind_speed = weather_data.get('wind', {}).get('speed', 0)
    weather_id = weather_data['weather'][0]['id']
    
    if prefs.unit == 'metric':
        if temp > 35:
            alerts.append(get_localized_message(prefs.language, "extreme_heat_warning"))
        elif temp < -10:
            alerts.append(get_localized_message(prefs.language, "extreme_cold_warning"))
        if wind_speed > 10:
            alerts.append(get_localized_message(prefs.language, "high_wind_alert"))
    else: # imperial
        if temp > 95:
            alerts.append(get_localized_message(prefs.language, "extreme_heat_warning"))
        elif temp < 14:
            alerts.append(get_localized_message(prefs.language, "extreme_cold_warning"))
        if wind_speed > 22:
            alerts.append(get_localized_message(prefs.language, "high_wind_alert"))
    
    if humidity > 85:
        alerts.append(get_localized_message(prefs.language, "high_humidity_alert"))
    
    if weather_id < 300:
        alerts.append(get_localized_message(prefs.language, "thunderstorm_alert"))
    elif weather_id < 600 and weather_id >= 500:
        alerts.append(get_localized_message(prefs.language, "heavy_rain_alert"))
    elif weather_id < 700 and weather_id >= 600:
        alerts.append(get_localized_message(prefs.language, "snow_alert"))
    
    city_name = f"{weather_data['name']}, {weather_data['sys']['country']}"
    
    if alerts:
        alerts_list_str = "\n".join(f"• {alert}" for alert in alerts)
        message = get_localized_message(prefs.language, "alerts_for_city", city=city_name, alerts_list=alerts_list_str, temp=f"{temp}°{'C' if prefs.unit == 'metric' else 'F'}")
    else:
        message = get_localized_message(prefs.language, "no_alerts", city=city_name)
    
    await update.message.reply_text(message, parse_mode='HTML')

async def compare_cities(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Compare weather between cities."""
    user_id = update.effective_user.id
    user_data_store: UserDataStore = context.bot_data['user_data_store']
    weather_api_client: WeatherAPI = context.bot_data['weather_api_client']
    prefs = user_data_store.get_user_prefs(user_id)

    if not context.args:
        await update.message.reply_text(get_localized_message(prefs.language, "specify_cities_compare"), parse_mode='HTML')
        return
    
    cities_input = " ".join(context.args)
    cities = [city.strip() for city in cities_input.split(',')]
    
    if len(cities) < 2:
        await update.message.reply_text(get_localized_message(prefs.language, "not_enough_cities"), parse_mode='HTML')
        return
    
    if len(cities) > MAX_COMPARE_CITIES:
        await update.message.reply_text(get_localized_message(prefs.language, "too_many_cities"))
        cities = cities[:MAX_COMPARE_CITIES]
    
    await update.message.reply_chat_action(action="typing")
    
    weather_data_list = []
    for city in cities:
        data = await weather_api_client.get_current_weather(city, prefs.unit, prefs.language)
        if data and not data.get("error"):
            weather_data_list.append(data)
        else:
            await update.message.reply_text(get_localized_message(prefs.language, "city_not_found", city=city))
            return # Stop comparison if any city is not found
    
    if not weather_data_list:
        await update.message.reply_text(get_localized_message(prefs.language, "error_fetching_data_any_cities"))
        return
    
    unit_symbol = "°C" if prefs.unit == "metric" else "°F"
    
    message = get_localized_message(prefs.language, "weather_comparison_title")
    
    # Temperature comparison
    temps = [(data['name'], data['main']['temp']) for data in weather_data_list]
    temps.sort(key=lambda x: x[1], reverse=True)
    
    message += get_localized_message(prefs.language, "temperature_comparison", unit_symbol=unit_symbol)
    for i, (name, temp) in enumerate(temps, 1):
        emoji = "🔥" if i == 1 else "🧊" if i == len(temps) else "🌡️"
        message += f"{i}. {emoji} {name}: {temp:.1f}{unit_symbol}\n"
    
    message += "\n"
    
    # Humidity comparison
    humidities = [(data['name'], data['main']['humidity']) for data in weather_data_list]
    humidities.sort(key=lambda x: x[1], reverse=True)
    
    message += get_localized_message(prefs.language, "humidity_comparison")
    for i, (name, humidity) in enumerate(humidities, 1):
        emoji = "💧" if i == 1 else "🏜️" if i == len(humidities) else "💨"
        message += f"{i}. {emoji} {name}: {humidity}%\n"
    
    message += "\n"
    
    # Weather conditions
    message += get_localized_message(prefs.language, "current_conditions_comparison")
    for data_item in weather_data_list:
        name = data_item['name']
        condition = data_item['weather'][0]['description'].title()
        emoji = get_weather_emoji(data_item['weather'][0]['id'])
        message += f"{emoji} {name}: {condition}\n"
    
    # Find extremes
    message += get_localized_message(prefs.language, "highlights_comparison")
    hottest = max(weather_data_list, key=lambda x: x['main']['temp'])
    coldest = min(weather_data_list, key=lambda x: x['main']['temp'])
    most_humid = max(weather_data_list, key=lambda x: x['main']['humidity'])
    
    message += get_localized_message(prefs.language, "hottest", city=hottest['name'], temp=hottest['main']['temp'], unit_symbol=unit_symbol) + "\n"
    message += get_localized_message(prefs.language, "coldest", city=coldest['name'], temp=coldest['main']['temp'], unit_symbol=unit_symbol) + "\n"
    message += get_localized_message(prefs.language, "most_humid", city=most_humid['name'], humidity=most_humid['main']['humidity'])
    
    await update.message.reply_text(message, parse_mode='HTML')

async def weather_map(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Provide weather map link."""
    user_id = update.effective_user.id
    user_data_store: UserDataStore = context.bot_data['user_data_store']
    weather_api_client: WeatherAPI = context.bot_data['weather_api_client']
    prefs = user_data_store.get_user_prefs(user_id)

    if not context.args:
        await update.message.reply_text(get_localized_message(prefs.language, "specify_city_map"), parse_mode='HTML')
        return
    
    city = " ".join(context.args)
    
    await update.message.reply_chat_action(action="typing")
    geo_data = await weather_api_client.get_city_coordinates(city)
    
    if not geo_data:
        await update.message.reply_text(get_localized_message(prefs.language, "error_generating_map"))
        return
    
    if not geo_data:
        await update.message.reply_text(get_localized_message(prefs.language, "city_not_found", city=city))
        return
    
    lat = geo_data[0]['lat']
    lon = geo_data[0]['lon']
    name = geo_data[0]['name']
    country = geo_data[0].get('country', '')
    
    openweather_map = f"https://openweathermap.org/weathermap?basemap=map&cities=true&layer=temperature&lat={lat}&lon={lon}&zoom=10"
    Maps = f"https://www.google.com/maps/@{lat},{lon},10z"
    
    keyboard = [
        [InlineKeyboardButton(get_localized_message(prefs.language, "openweather_map_button"), url=openweather_map)],
        [InlineKeyboardButton(get_localized_message(prefs.language, "Maps_button"), url=Maps)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message = get_localized_message(prefs.language, "map_links", city=f"{name}, {country}")
    await update.message.reply_text(message, parse_mode='HTML', reply_markup=reply_markup)

async def handle_city_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle direct city name messages (non-command)."""
    city = update.message.text.strip().strip('"\'')
    user_id = update.effective_user.id
    user_data_store: UserDataStore = context.bot_data['user_data_store']
    weather_api_client: WeatherAPI = context.bot_data['weather_api_client']
    prefs = user_data_store.get_user_prefs(user_id)
    
    # Auto-add frequently searched cities to favorites
    if city.lower() not in [fav.lower() for fav in prefs.favorites] and len(prefs.favorites) < MAX_FAVORITES:
        if await weather_api_client.verify_city_exists(city, prefs.language):
            keyboard = [[InlineKeyboardButton(get_localized_message(prefs.language, "add_to_favorites_button"), callback_data=f"addfav_{city}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await send_current_weather(update, city, prefs, weather_api_client, suggest_favorite=reply_markup)
        else:
            await send_current_weather(update, city, prefs, weather_api_client)
    else:
        await send_current_weather(update, city, prefs, weather_api_client)

# Helper functions that interact with API and send messages
async def send_current_weather(update: Update, city: str, prefs: UserPreferences, weather_api_client: WeatherAPI, edit_message: bool = False, suggest_favorite=None):
    """Fetches and sends current weather data."""
    if not edit_message:
        await update.message.reply_chat_action(action="typing")
    
    weather_data = await weather_api_client.get_current_weather(city, prefs.unit, prefs.language)

    if not weather_data:
        message = get_localized_message(prefs.language, "api_request_failed")
        if weather_data and weather_data.get("error") == "city_not_found":
            message = get_localized_message(prefs.language, "city_not_found_weather", city=city)
        
        if edit_message:
            await update.callback_query.edit_message_text(message)
        else:
            await update.message.reply_text(message)
        return

    weather_message = format_weather_message(weather_data, prefs.language, prefs.unit)
    
    if edit_message:
        await update.callback_query.edit_message_text(weather_message, parse_mode='HTML')
    else:
        await update.message.reply_text(weather_message, parse_mode='HTML', reply_markup=suggest_favorite)

async def send_five_day_forecast(update: Update, city: str, prefs: UserPreferences, weather_api_client: WeatherAPI):
    """Fetches and sends 5-day weather forecast."""
    await update.message.reply_chat_action(action="typing")
    
    forecast_data = await weather_api_client.get_five_day_forecast(city, prefs.unit, prefs.language)

    if not forecast_data:
        message = get_localized_message(prefs.language, "error_fetching_forecast")
        if forecast_data and forecast_data.get("error") == "city_not_found":
            message = get_localized_message(prefs.language, "city_not_found", city=city)
        
        await update.message.reply_text(message)
        return

    forecast_message = format_forecast_message(forecast_data, prefs.language, prefs.unit)
    await update.message.reply_text(forecast_message, parse_mode='HTML')