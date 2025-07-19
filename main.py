import logging
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# Import modules from your new structure
from telegram import Update
from config import TELEGRAM_BOT_TOKEN, WEATHER_API_KEY
from data_store import UserDataStore
from weather_api import WeatherAPI
from handlers import command_handlers, callback_handlers # Import the handler modules

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    """Starts the bot."""
    if not TELEGRAM_BOT_TOKEN or not WEATHER_API_KEY:
        logger.error("Bot cannot start: Missing required environment variables. Please check config.py or your .env file.")
        return

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Initialize shared resources and store them in bot_data
    user_data_store = UserDataStore()
    weather_api_client = WeatherAPI(WEATHER_API_KEY)
    
    application.bot_data['user_data_store'] = user_data_store
    application.bot_data['weather_api_client'] = weather_api_client

    # Command handlers
    application.add_handler(CommandHandler("start", command_handlers.start_command))
    application.add_handler(CommandHandler("help", command_handlers.help_command))
    application.add_handler(CommandHandler("weather", command_handlers.weather_command))
    application.add_handler(CommandHandler("forecast", command_handlers.forecast_command))
    application.add_handler(CommandHandler("search", command_handlers.search_cities))
    application.add_handler(CommandHandler("favorites", command_handlers.favorites_command))
    application.add_handler(CommandHandler("addfav", command_handlers.add_favorite))
    application.add_handler(CommandHandler("removefav", command_handlers.remove_favorite))
    application.add_handler(CommandHandler("settings", command_handlers.settings_command))
    application.add_handler(CommandHandler("alerts", command_handlers.weather_alerts))
    application.add_handler(CommandHandler("compare", command_handlers.compare_cities))
    application.add_handler(CommandHandler("map", command_handlers.weather_map))
    
    # Callback query handler for inline keyboards
    application.add_handler(CallbackQueryHandler(callback_handlers.handle_callback))
    
    # Message handler for city names
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, 
        command_handlers.handle_city_message
    ))

    # Error handler
    application.add_error_handler(error_handler)

    print("🚀 Starting Enhanced Weather Bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors."""
    logger.error(f"Exception while handling an update: {context.error}")
    if update and update.effective_message:
        user_id = update.effective_user.id
        user_data_store = context.bot_data.get('user_data_store')
        prefs = user_data_store.get_user_prefs(user_id)
        await update.effective_message.reply_text(get_localized_message(prefs.language, "unexpected_error"))


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
    except Exception as e:
        logger.critical(f"Failed to start bot: {e}")
        print(f"❌ Critical Error: {e}")