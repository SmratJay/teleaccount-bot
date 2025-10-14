"""
Bot handlers for the Telegram Account Bot.
"""
import logging
from telegram.ext import Application
from .basic_handlers import setup_basic_handlers
from .lfg_handlers import setup_lfg_handlers
from .user_handlers import setup_user_handlers
from .admin_handlers import setup_admin_handlers

logger = logging.getLogger(__name__)

def setup_handlers(application: Application) -> None:
    """Set up all bot handlers."""
    try:
        # Setup different handler groups
        setup_basic_handlers(application)
        setup_lfg_handlers(application)
        setup_user_handlers(application)
        setup_admin_handlers(application)
        
        logger.info("All bot handlers set up successfully")
        
    except Exception as e:
        logger.error(f"Error setting up handlers: {e}")
        raise