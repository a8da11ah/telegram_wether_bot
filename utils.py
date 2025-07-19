from datetime import datetime
from localization import get_localized_message
from typing import Dict, Any

def get_weather_emoji(weather_id: int) -> str:
    """Get appropriate emoji for weather condition based on OpenWeatherMap weather ID."""
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

def format_weather_message(data: Dict[str, Any], prefs_lang: str, unit: str) -> str:
    """Format current weather data into a readable message."""
    city = data['name']
    country = data['sys']['country']
    temp = data['main']['temp']
    feels_like = data['main']['feels_like']
    humidity = data['main']['humidity']
    pressure = data['main']['pressure']
    description = data['weather'][0]['description'].title()
    
    wind_speed = data.get('wind', {}).get('speed', 0)
    wind_deg = data.get('wind', {}).get('deg', 0)
    visibility = data.get('visibility', 0) / 1000 if data.get('visibility') else None
    clouds = data.get('clouds', {}).get('all', 0)
    
    sunrise = datetime.fromtimestamp(data['sys']['sunrise']).strftime('%H:%M')
    sunset = datetime.fromtimestamp(data['sys']['sunset']).strftime('%H:%M')
    
    weather_id = data['weather'][0]['id']
    emoji = get_weather_emoji(weather_id)
    
    if unit == 'metric':
        temp_unit = "°C"
        speed_unit = get_localized_message(prefs_lang, "meters_per_second")
    else:
        temp_unit = "°F"
        speed_unit = get_localized_message(prefs_lang, "miles_per_hour")
    
    temp = round(temp)
    feels_like = round(feels_like)

    # Simplified wind direction logic
    wind_directions = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                      "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    wind_dir = wind_directions[round(wind_deg / 22.5) % 16] if wind_deg is not None else "N/A"
    
    message = (
        f"{emoji} <b>{get_localized_message(prefs_lang, 'weather_in_city', city=city, country=country)}</b>\n\n"
        f"🌡️ {get_localized_message(prefs_lang, 'temperature')}: {temp}{temp_unit}\n"
        f"🤔 {get_localized_message(prefs_lang, 'feels_like')}: {feels_like}{temp_unit}\n"
        f"💧 {get_localized_message(prefs_lang, 'humidity')}: {humidity}%\n"
        f"📊 {get_localized_message(prefs_lang, 'pressure')}: {pressure} hPa\n"
        f"💨 {get_localized_message(prefs_lang, 'wind')}: {wind_speed:.1f} {speed_unit} {wind_dir}\n"
        f"☁️ {get_localized_message(prefs_lang, 'cloudiness')}: {clouds}%\n"
    )
    
    if visibility is not None:
        message += f"👁️ {get_localized_message(prefs_lang, 'visibility')}: {visibility:.1f} km\n"
    
    message += (
        f"📝 {get_localized_message(prefs_lang, 'conditions')}: {description}\n\n"
        f"🌅 {get_localized_message(prefs_lang, 'sunrise')}: {sunrise}\n"
        f"🌇 {get_localized_message(prefs_lang, 'sunset')}: {sunset}"
    )
    
    return message

def format_forecast_message(data: Dict[str, Any], prefs_lang: str, unit: str) -> str:
    """Format 5-day forecast data into a readable message."""
    city = data['city']['name']
    country = data['city']['country']
    
    unit_symbol = "°C" if unit == "metric" else "°F"
    
    message = get_localized_message(prefs_lang, "forecast_for_city", city=city, country=country) + "\n\n"
    
    daily_forecasts = {}
    for item in data['list']:
        date = datetime.fromtimestamp(item['dt']).date()
        if date not in daily_forecasts:
            daily_forecasts[date] = []
        daily_forecasts[date].append(item)
    
    for i, (date, forecasts) in enumerate(list(daily_forecasts.items())[:5]):
        day_name = date.strftime('%A')
        date_str = date.strftime('%m/%d')
        
        temps = [f['main']['temp'] for f in forecasts]
        min_temp = min(temps)
        max_temp = max(temps)
        
        conditions = [f['weather'][0] for f in forecasts]
        main_condition_group = max(set(c['main'] for c in conditions), 
                                   key=[c['main'] for c in conditions].count)
        
        # Get a representative description, prefer one matching the main condition group
        representative_description = next((c['description'].title() for c in conditions if c['main'] == main_condition_group), conditions[0]['description'].title())
        
        weather_ids = [c['id'] for c in conditions if c['main'] == main_condition_group]
        representative_id = weather_ids[0] if weather_ids else conditions[0]['id']
        
        emoji = get_weather_emoji(representative_id)
        
        pop = max([f.get('pop', 0) for f in forecasts]) * 100
        
        message += f"{emoji} <b>{day_name} ({date_str})</b>\n"
        message += f"   🌡️ {min_temp:.0f}{unit_symbol} - {max_temp:.0f}{unit_symbol}"
        
        if pop > 20:
            message += f" | 🌧️ {pop:.0f}%"
        
        message += f"\n   📝 {representative_description}\n\n"
        
    return message