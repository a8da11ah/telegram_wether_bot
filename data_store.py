import json
import logging
from typing import Dict, List
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class UserPreferences:
    """User preferences data class"""
    unit: str = "metric"
    language: str = "en"
    favorites: List[str] = None
    default_city: str = None
    
    def __post_init__(self):
        if self.favorites is None:
            self.favorites = []

class UserDataStore:
    def __init__(self, filename: str = 'user_preferences.json'):
        self.filename = filename
        self.user_preferences: Dict[int, UserPreferences] = {}
        self.load_user_data()

    def load_user_data(self):
        """Load user preferences from file."""
        try:
            if os.path.exists(self.filename):
                with open(self.filename, 'r') as f:
                    data = json.load(f)
                    for user_id, prefs_data in data.items():
                        # Ensure favorites is a list if it was null/None in JSON
                        if 'favorites' in prefs_data and prefs_data['favorites'] is None:
                            prefs_data['favorites'] = []
                        self.user_preferences[int(user_id)] = UserPreferences(**prefs_data)
            logger.info(f"Loaded preferences for {len(self.user_preferences)} users.")
        except Exception as e:
            logger.error(f"Error loading user data from {self.filename}: {e}")

    def save_user_data(self):
        """Save user preferences to file."""
        try:
            data_to_save = {str(user_id): asdict(prefs) for user_id, prefs in self.user_preferences.items()}
            with open(self.filename, 'w') as f:
                json.dump(data_to_save, f, indent=2)
            logger.info(f"Saved preferences for {len(self.user_preferences)} users.")
        except Exception as e:
            logger.error(f"Error saving user data to {self.filename}: {e}")

    def get_user_prefs(self, user_id: int) -> UserPreferences:
        """Get user preferences or create default if not exists."""
        if user_id not in self.user_preferences:
            self.user_preferences[user_id] = UserPreferences()
            self.save_user_data() # Save new user's default prefs immediately
        return self.user_preferences[user_id]

    def reset_user_prefs(self, user_id: int):
        """Resets user preferences to default."""
        self.user_preferences[user_id] = UserPreferences()
        self.save_user_data()