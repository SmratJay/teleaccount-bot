"""
Internationalization (i18n) utilities for the Telegram Account Bot.
"""
import json
import os
import logging
from typing import Dict, Any, Optional
from database import get_db_session, close_db_session
from database.operations import UserService

logger = logging.getLogger(__name__)

class LocaleManager:
    """Manages localization and translations."""
    
    def __init__(self):
        self.messages = {}
        self.default_locale = 'en'
        self.supported_locales = ['en', 'es', 'ru']
        self._load_messages()
    
    def _load_messages(self):
        """Load messages from JSON files."""
        try:
            messages_file = os.path.join(os.path.dirname(__file__), 'messages.json')
            with open(messages_file, 'r', encoding='utf-8') as f:
                self.messages = json.load(f)
            logger.info(f"Loaded messages for locales: {list(self.messages.keys())}")
        except Exception as e:
            logger.error(f"Error loading messages: {e}")
            # Fallback to empty dict
            self.messages = {self.default_locale: {}}
    
    def get_user_locale(self, telegram_user_id: int) -> str:
        """Get user's preferred locale from database."""
        try:
            db = get_db_session()
            try:
                user = UserService.get_user_by_telegram_id(db, telegram_user_id)
                if user and user.language_code:
                    # Extract base language (e.g., 'en' from 'en-US')
                    base_lang = user.language_code.split('-')[0].lower()
                    if base_lang in self.supported_locales:
                        return base_lang
            finally:
                close_db_session(db)
        except Exception as e:
            logger.warning(f"Error getting user locale: {e}")
        
        return self.default_locale
    
    def get_message(self, key: str, locale: str = None, **kwargs) -> str:
        """Get localized message."""
        if locale is None:
            locale = self.default_locale
        
        if locale not in self.messages:
            locale = self.default_locale
        
        # Support nested keys like 'buttons.lfg'
        keys = key.split('.')
        message = self.messages.get(locale, {})
        
        for k in keys:
            if isinstance(message, dict) and k in message:
                message = message[k]
            else:
                # Fallback to English if key not found
                message = self.messages.get(self.default_locale, {})
                for k in keys:
                    if isinstance(message, dict) and k in message:
                        message = message[k]
                    else:
                        return f"Missing translation: {key}"
                break
        
        if not isinstance(message, str):
            return f"Invalid translation: {key}"
        
        # Format with kwargs if provided
        try:
            return message.format(**kwargs)
        except KeyError as e:
            logger.warning(f"Missing format parameter {e} for key {key}")
            return message
    
    def get_user_message(self, telegram_user_id: int, key: str, **kwargs) -> str:
        """Get localized message for specific user."""
        locale = self.get_user_locale(telegram_user_id)
        return self.get_message(key, locale, **kwargs)
    
    def set_user_locale(self, telegram_user_id: int, locale: str) -> bool:
        """Set user's preferred locale."""
        if locale not in self.supported_locales:
            return False
        
        try:
            db = get_db_session()
            try:
                user = UserService.get_user_by_telegram_id(db, telegram_user_id)
                if user:
                    from database.models import User
                    db.query(User).filter(User.telegram_user_id == telegram_user_id).update(
                        {'language_code': locale}
                    )
                    db.commit()
                    logger.info(f"Set locale {locale} for user {telegram_user_id}")
                    return True
            finally:
                close_db_session(db)
        except Exception as e:
            logger.error(f"Error setting user locale: {e}")
        
        return False
    
    def get_supported_locales(self) -> Dict[str, str]:
        """Get supported locales with their names."""
        return {
            'en': '🇺🇸 English',
            'es': '🇪🇸 Español', 
            'ru': '🇷🇺 Русский'
        }

# Global locale manager instance
locale_manager = LocaleManager()

def t(key: str, locale: str = 'en', **kwargs) -> str:
    """Shortcut function for translations."""
    return locale_manager.get_message(key, locale, **kwargs)

def tu(telegram_user_id: int, key: str, **kwargs) -> str:
    """Shortcut function for user-specific translations."""
    return locale_manager.get_user_message(telegram_user_id, key, **kwargs)
