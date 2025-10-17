"""
Real Telegram Account Selling Bot - Production Version
Uses actual Telethon integration for real account operations
"""
import asyncio
import logging
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler
from handlers.real_handlers import setup_real_handlers

# Configure detailed logging with Unicode support
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('real_bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def main():
    """Main function to run the real account selling bot."""
    # Get bot token
    BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN') or os.getenv('BOT_TOKEN')
    
    if not BOT_TOKEN:
        # Load from .env file
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
    
    # Validate Telegram API credentials
    API_ID = os.getenv('API_ID')
    API_HASH = os.getenv('API_HASH')
    
    if not API_ID or not API_HASH:
        try:
            with open('.env', 'r') as f:
                content = f.read()
                if 'API_ID=' in content and 'API_HASH=' in content:
                    logger.info("Telegram API credentials found in .env")
                else:
                    logger.error("API_ID and API_HASH required for real Telegram operations!")
                    return
        except FileNotFoundError:
            logger.error(".env file not found! API credentials required!")
            return
    
    # Start WebApp server for embedded forms
    from webapp.server import start_webapp_server
    if start_webapp_server():
        logger.info("WebApp server started for embedded forms")
    else:
        logger.error("Failed to start WebApp server")
        return
    
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add all handlers using the real handler setup  
    setup_real_handlers(application)
    
    logger.info("REAL Telegram Account Selling Bot Started!")
    logger.info("Features: Real OTP -> Real Login -> Real Account Transfer")
    logger.info("WARNING: This performs ACTUAL account operations!")
    logger.info("Using Telethon for real Telegram API integration")
    logger.info("Embedded forms available via WebApp")
    
    # Run the bot
    try:
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
    finally:
        logger.info("Bot stopped.")

if __name__ == '__main__':
    main()