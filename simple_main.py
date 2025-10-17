"""
Simple Telegram Account Selling Bot - Main Entry Point
Clean implementation focused on core selling functionality.
"""
import asyncio
import logging
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from handlers.simple_handlers import start_command, button_callback, get_selling_handler

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    """Main function to run the bot."""
    # Get bot token from environment or .env file
    BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN') or os.getenv('BOT_TOKEN')
    
    if not BOT_TOKEN:
        # Load from .env file if available
        try:
            with open('.env', 'r') as f:
                for line in f:
                    if line.startswith('BOT_TOKEN=') or line.startswith('TELEGRAM_BOT_TOKEN='):
                        BOT_TOKEN = line.split('=', 1)[1].strip()
                        break
        except FileNotFoundError:
            pass
    
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN not found! Set it in environment or .env file")
        return
    
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(get_selling_handler())  # Conversation handler for selling
    application.add_handler(CallbackQueryHandler(button_callback))  # Other buttons
    
    logger.info("🤖 Simple Account Selling Bot started!")
    logger.info("📱 Core features: Phone → OTP → Account Setup → Sale")
    
    # Run the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()