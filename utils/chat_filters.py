"""
Chat type filters for security and privacy protection.
"""
import logging
from telegram import Update, Chat
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

async def private_chat_only(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Filter to ensure bot only works in private chats.
    
    This is CRITICAL for privacy and security:
    - Prevents balance information leaks in groups
    - Prevents CAPTCHA answers from being visible to group members
    - Prevents account details and transactions from being exposed
    - Prevents withdrawal information from being public
    
    Returns:
        bool: True if private chat, False if group/channel
    """
    if not update.effective_chat:
        return False
    
    chat_type = update.effective_chat.type
    
    # Allow only private chats (1-on-1 with bot)
    if chat_type == Chat.PRIVATE:
        return True
    
    # Reject groups, supergroups, and channels
    if chat_type in [Chat.GROUP, Chat.SUPERGROUP, Chat.CHANNEL]:
        logger.warning(
            f"🚫 Blocked {chat_type} chat access from user {update.effective_user.id} "
            f"in chat {update.effective_chat.id}"
        )
        
        # Send warning message (only if the user can receive it)
        try:
            if update.message:
                await update.message.reply_text(
                    "🔒 **Privacy Protection Active**\n\n"
                    "⚠️ This bot handles sensitive financial and account information.\n\n"
                    "For your security, the bot **ONLY** works in private chats.\n\n"
                    "**To use the bot:**\n"
                    "1. Click here: @" + context.bot.username + "\n"
                    "2. Start a private conversation with /start\n\n"
                    "❌ The bot will NOT respond to commands in groups or channels.",
                    parse_mode='Markdown'
                )
            elif update.callback_query:
                await update.callback_query.answer(
                    "🔒 This bot only works in private chats for security reasons. "
                    "Please message the bot directly.",
                    show_alert=True
                )
        except Exception as e:
            logger.error(f"Error sending privacy warning: {e}")
        
        return False
    
    # Default: reject unknown chat types
    return False


async def admin_only(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Filter to ensure only admin users can access certain features.
    
    Returns:
        bool: True if user is admin, False otherwise
    """
    import os
    from database import get_db_session, close_db_session
    from database.operations import UserService
    
    user_id = update.effective_user.id
    
    # Check environment variable for admin ID
    admin_id = os.getenv('ADMIN_TELEGRAM_ID') or os.getenv('ADMIN_USER_ID')
    if admin_id and str(user_id) == str(admin_id):
        return True
    
    # Check database for admin status
    db = get_db_session()
    try:
        db_user = UserService.get_user_by_telegram_id(db, user_id)
        if db_user and getattr(db_user, 'is_admin', False):
            return True
    finally:
        close_db_session(db)
    
    # Not an admin
    logger.warning(f"🚫 Non-admin user {user_id} attempted admin action")
    
    try:
        if update.message:
            await update.message.reply_text(
                "❌ **Access Denied**\n\n"
                "This command is only available to administrators.",
                parse_mode='Markdown'
            )
        elif update.callback_query:
            await update.callback_query.answer(
                "❌ Admin access required",
                show_alert=True
            )
    except Exception as e:
        logger.error(f"Error sending admin denial message: {e}")
    
    return False
