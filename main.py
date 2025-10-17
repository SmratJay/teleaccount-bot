"""
Telegram Account Bot - Main Application En        # Set up handlers
        setup_main_handlers(self.application)y Point
"""
import os
import sys
import logging
import asyncio
from datetime import datetime
from dotenv import load_dotenv

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from telegram.ext import Application, CommandHandler, MessageHandler, ConversationHandler, filters
from database import db_manager, create_tables
from handlers.main_handlers import setup_main_handlers
from utils.logging_config import setup_logging

# Load environment variables
load_dotenv()

class TelegramAccountBot:
    """Main Telegram Account Bot class."""
    
    def __init__(self):
        self.bot_token = os.getenv('BOT_TOKEN')
        self.admin_user_id = int(os.getenv('ADMIN_USER_ID', 0))
        self.admin_chat_id = os.getenv('ADMIN_CHAT_ID')
        
        if not self.bot_token:
            raise ValueError("BOT_TOKEN environment variable is required")
        
        # Setup logging
        setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # Initialize database
        try:
            create_tables()
            self.logger.info("Database tables created successfully")
        except Exception as e:
            self.logger.error(f"Failed to create database tables: {e}")
            raise
        
        # Initialize application
        self.application = Application.builder().token(self.bot_token).build()
        
        # Setup handlers
        setup_main_handlers(self.application)
        
        self.logger.info("Telegram Account Bot initialized successfully")
    
    async def start(self):
        """Start the bot."""
        try:
            self.logger.info("Starting Telegram Account Bot...")
            
            # Start the bot
            await self.application.initialize()
            await self.application.start()
            
            # Send startup notification to admin
            if self.admin_chat_id:
                try:
                    await self.application.bot.send_message(
                        chat_id=self.admin_chat_id,
                        text=f"🤖 Telegram Account Bot started successfully!\n"
                             f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    )
                except Exception as e:
                    self.logger.warning(f"Could not send startup notification to admin: {e}")
            
            # Start polling
            await self.application.updater.start_polling(drop_pending_updates=True)
            
            self.logger.info("Bot is now running and listening for messages...")
            
            # Keep the bot running
            await asyncio.Event().wait()
            
        except Exception as e:
            self.logger.error(f"Error starting bot: {e}")
            raise
    
    async def stop(self):
        """Stop the bot."""
        try:
            self.logger.info("Stopping Telegram Account Bot...")
            
            # Send shutdown notification to admin
            if self.admin_chat_id:
                try:
                    await self.application.bot.send_message(
                        chat_id=self.admin_chat_id,
                        text=f"🛑 Telegram Account Bot shutting down...\n"
                             f"⏰ Shutdown at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    )
                except Exception as e:
                    self.logger.warning(f"Could not send shutdown notification to admin: {e}")
            
            await self.application.stop()
            await self.application.shutdown()
            
            self.logger.info("Bot stopped successfully")
            
        except Exception as e:
            self.logger.error(f"Error stopping bot: {e}")

def main():
    """Main entry point."""
    try:
        bot = TelegramAccountBot()
        asyncio.run(bot.start())
    except KeyboardInterrupt:
        print("\nBot interrupted by user")
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()