"""
Bot handlers for the Telegram Account Bot.
"""
import logging
from telegram.ext import Application

logger = logging.getLogger(__name__)

def setup_handlers(application: Application) -> None:
    """Set up all bot handlers - temporarily disabled old handlers."""
    try:
        # Old handlers temporarily disabled during rebuild
        # Will be rebuilt to match new specification
        logger.info("Handler setup placeholder - using main_handlers instead")
        
    except Exception as e:
        logger.error(f"Error setting up handlers: {e}")
        raise