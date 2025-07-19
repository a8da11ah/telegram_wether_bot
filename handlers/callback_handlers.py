import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from data_store import UserDataStore
from localization import get_localized_message
from handlers.command_handlers import send_current_weather, settings_command # Import settings_command to reuse it
from config import MAX_FAVORITES # Also need to access MAX_FAVORITES here

logger = logging.getLogger(__name__)

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline keyboard callbacks."""
    query = update.callback_query
    await query.answer() # Acknowledge the callback query
    
    data = query.data
    user_id = update.effective_user.id
    user_data_store: UserDataStore = context.bot_data['user_data_store']
    weather_api_client = context.bot_data['weather_api_client']
    prefs = user_data_store.get_user_prefs(user_id)
    
    if data.startswith("weather_"):
        city = data.replace("weather_", "")
        await send_current_weather(update, city, prefs, weather_api_client, edit_message=True)
    
    elif data.startswith("addfav_"):
        city = data.replace("addfav_", "")
        if city.lower() not in [fav.lower() for fav in prefs.favorites]:
            prefs.favorites.append(city)
            user_data_store.save_user_data()
            await query.edit_message_text(get_localized_message(prefs.language, "added_favorite", city=city))
        else:
            await query.edit_message_text(get_localized_message(prefs.language, "already_favorite", city=city))
        # Optionally, refresh the message or go back to main menu

    elif data == "toggle_units":
        prefs.unit = "imperial" if prefs.unit == "metric" else "metric"
        user_data_store.save_user_data()
        await settings_command(update, context) # Re-send settings menu with updated unit
    
    elif data == "choose_language":
        keyboard = [
            [InlineKeyboardButton(get_localized_message(prefs.language, "english"), callback_data="set_lang_en")],
            [InlineKeyboardButton(get_localized_message(prefs.language, "arabic"), callback_data="set_lang_ar")],
            [InlineKeyboardButton(get_localized_message(prefs.language, "manage_favorites_back"), callback_data="back_to_settings")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            get_localized_message(prefs.language, "choose_language"),
            parse_mode='HTML',
            reply_markup=reply_markup
        )
    
    elif data.startswith("set_lang_"):
        lang_code = data.replace("set_lang_", "")
        prefs.language = lang_code
        user_data_store.save_user_data()
        language_name = get_localized_message(prefs.language, lang_code)
        await query.edit_message_text(get_localized_message(prefs.language, "language_set", language_name=language_name))
        await settings_command(update, context) # Go back to main settings menu
        
    elif data == "set_default_city":
        await query.edit_message_text(
            get_localized_message(prefs.language, "set_default_city_instructions"),
            parse_mode='HTML'
        )
    
    elif data == "manage_favorites":
        if not prefs.favorites:
            await query.edit_message_text(
                get_localized_message(prefs.language, "no_favorites"),
                parse_mode='HTML'
            )
            return
        
        keyboard = []
        for city in prefs.favorites:
            keyboard.append([InlineKeyboardButton(f"🗑️ Remove {city}", callback_data=f"removefav_callback_{city}")])
        
        keyboard.append([InlineKeyboardButton(get_localized_message(prefs.language, "manage_favorites_back"), callback_data="back_to_settings")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            get_localized_message(prefs.language, "manage_favorites_menu"),
            parse_mode='HTML',
            reply_markup=reply_markup
        )
    
    elif data.startswith("removefav_callback_"):
        city = data.replace("removefav_callback_", "")
        if city in prefs.favorites:
            prefs.favorites.remove(city)
            user_data_store.save_user_data()
            await query.edit_message_text(get_localized_message(prefs.language, "removed_favorite", city=city))
            await handle_callback(update, context) # Refresh the manage favorites list
        else:
            await query.edit_message_text(get_localized_message(prefs.language, "not_in_favorites", city=city))
    
    elif data == "back_to_settings":
        await settings_command(update, context)
    
    elif data == "reset_settings":
        user_data_store.reset_user_prefs(user_id)
        await query.edit_message_text(get_localized_message(prefs.language, "reset_settings_confirm"))
    
    # Handle help menu callbacks (from /start)
    elif data.startswith("help_"):
        help_type = data.replace("help_", "")
        # For simplicity, these just send a generic help message.
        # You could expand this to send specific help for each section.
        await query.edit_message_text(get_localized_message(prefs.language, "help"), parse_mode='HTML')