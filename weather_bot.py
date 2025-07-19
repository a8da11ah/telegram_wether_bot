from dotenv import load_dotenv
load_dotenv()
import os
import requests
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv

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
WEATHER_API_URL = "https://api.openweathermap.org/data/2.5/weather"

class WeatherBot:
    def __init__(self):
        self.application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        self.setup_handlers()
    
    def setup_handlers(self):
        """Set up command and message handlers"""
        # Command handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("weather", self.weather_command))
        
        # Message handler for city names
        self.application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND, 
            self.handle_city_message
        ))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        welcome_message = (
            "🌤️ Welcome to Weather Bot! 🌤️\n\n"
            "I can help you get current weather information for any city.\n\n"
            "Commands:\n"
            "• /weather <city> - Get weather for a specific city\n"
            "• /help - Show this help message\n\n"
            "You can also just send me a city name directly!"
        )
        await update.message.reply_text(welcome_message)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_message = (
            "🆘 Weather Bot Help\n\n"
            "How to use:\n"
            "• Type '/weather London' to get weather for London\n"
            "• Or simply type 'Tokyo' to get weather for Tokyo\n"
            "• Use city names in English\n"
            "• For cities with spaces, use quotes: 'New York'\n\n"
            "Examples:\n"
            "• /weather Paris\n"
            "• Berlin\n"
            "• 'Los Angeles'"
        )
        await update.message.reply_text(help_message)
    
    async def weather_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /weather command with city parameter"""
        if not context.args:
            await update.message.reply_text(
                "Please specify a city! Usage: /weather <city>\n"
                "Example: /weather London"
            )
            return
        
        city = " ".join(context.args)
        await self.get_and_send_weather(update, city)
    
    async def handle_city_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle direct city name messages"""
        city = update.message.text.strip()
        await self.get_and_send_weather(update, city)
    
    async def get_and_send_weather(self, update: Update, city: str):
        """Fetch weather data and send response"""
        try:
            # Send "typing..." indicator
            await update.message.reply_chat_action(action="typing")
            
            # Make API request
            params = {
                'q': city,
                'appid': WEATHER_API_KEY,
                'units': 'metric'  # Use Celsius
            }
            
            response = requests.get(WEATHER_API_URL, params=params, timeout=10)
            
            if response.status_code == 404:
                await update.message.reply_text(
                    f"🚫 City '{city}' not found. Please check the spelling and try again."
                )
                return
            
            response.raise_for_status()
            data = response.json()
            
            # Format weather information
            weather_message = self.format_weather_message(data)
            await update.message.reply_text(weather_message, parse_mode='HTML')
            
        except requests.exceptions.Timeout:
            await update.message.reply_text(
                "⏰ Request timeout. Please try again later."
            )
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            await update.message.reply_text(
                "❌ Sorry, I couldn't fetch weather data right now. Please try again later."
            )
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            await update.message.reply_text(
                "❌ An unexpected error occurred. Please try again."
            )
    
    def format_weather_message(self, data):
        """Format weather data into a nice message"""
        city = data['name']
        country = data['sys']['country']
        temp = round(data['main']['temp'])
        feels_like = round(data['main']['feels_like'])
        humidity = data['main']['humidity']
        description = data['weather'][0]['description'].title()
        
        # Get weather emoji
        weather_id = data['weather'][0]['id']
        emoji = self.get_weather_emoji(weather_id)
        
        message = (
            f"{emoji} <b>Weather in {city}, {country}</b>\n\n"
            f"🌡️ Temperature: {temp}°C\n"
            f"🤔 Feels like: {feels_like}°C\n"
            f"💧 Humidity: {humidity}%\n"
            f"📝 Conditions: {description}"
        )
        
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
        print("Starting Weather Bot...")
        self.application.run_polling()

# Error handler
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors"""
    logger.warning(f'Update "{update}" caused error "{context.error}"')

if __name__ == '__main__':
    # Create and run the bot
    bot = WeatherBot()
    bot.application.add_error_handler(error_handler)
    bot.run()