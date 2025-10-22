"""
Real Telegram Account Selling Bot - Production Version
Uses actual Telethon integration for real account operations
"""
import asyncio
import logging
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, filters
from handlers import setup_all_handlers  # Unified handler entry point
from utils.chat_filters import private_chat_only  # Privacy protection

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
    
    # Create application with job queue enabled
    from telegram.ext import JobQueue
    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .job_queue(JobQueue())  # Explicitly enable job queue
        .build()
    )
    
    # Initialize notification service
    from utils.notification_service import initialize_notification_service
    notification_service = initialize_notification_service(application.bot)
    logger.info("Notification service initialized")
    
    # Initialize proxy refresh scheduler
    from services.proxy_scheduler import start_proxy_scheduler, proxy_refresh_scheduler
    try:
        start_proxy_scheduler()
        logger.info("Proxy refresh scheduler initialized")
    except Exception as e:
        logger.warning(f"Failed to start proxy scheduler: {e}")
    
    # Add scheduled job for freeze expiry checks (runs every hour)
    from services.account_management import account_manager
    from database import get_db_session, close_db_session
    
    async def check_expired_freezes_job(context):
        """Background job to check and release expired account freezes"""
        try:
            db = get_db_session()
            try:
                result = account_manager.check_and_release_expired_freezes(db)
                if result['released_count'] > 0:
                    logger.info(f"Auto-released {result['released_count']} expired frozen accounts")
                    
                    # Send notifications for unfrozen accounts
                    for account_info in result.get('released_accounts', []):
                        try:
                            # Get account owner's telegram ID
                            from database.operations import TelegramAccountService
                            account = TelegramAccountService.get_account_by_id(db, account_info['account_id'])
                            if account and account.user:
                                await notification_service.notify_account_unfrozen(
                                    user_telegram_id=account.user.telegram_user_id,
                                    phone_number=account.phone_number,
                                    unfreeze_reason="Freeze period expired - automatic release"
                                )
                        except Exception as e:
                            logger.error(f"Error sending unfreeze notification: {e}")
            finally:
                close_db_session(db)
        except Exception as e:
            logger.error(f"Error in freeze expiry check job: {e}")
    
    # Schedule the job to run every hour
    job_queue = application.job_queue
    job_queue.run_repeating(check_expired_freezes_job, interval=3600, first=10)
    logger.info("Scheduled hourly freeze expiry check job")
    
    # Register all bot handlers through unified entry point
    setup_all_handlers(application)
    
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
