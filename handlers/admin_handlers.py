"""Admin command handlers for the Telegram Account Bot."""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

logger = logging.getLogger(__name__)

def setup_admin_handlers(application) -> None:
    """Set up admin handlers."""
    logger.info("Admin handlers set up successfully")
