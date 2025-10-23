"""
Conversation Helper Utilities
Universal handlers for ConversationHandler fallbacks and state management
"""
import logging
import os
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

logger = logging.getLogger(__name__)


async def universal_cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Universal cancel handler for all ConversationHandlers.
    
    This function should be added as a fallback to ALL ConversationHandlers
    to prevent the bot from getting "stuck" when users try to exit a conversation.
    
    What it does:
    1. Clears all user conversation state
    2. Cleans up temporary resources (files, images, etc.)
    3. Returns ConversationHandler.END to exit the conversation
    4. Shows a friendly message to the user
    
    Usage:
        Add to ConversationHandler fallbacks:
        fallbacks=[
            CommandHandler('start', universal_cancel_handler),
            CallbackQueryHandler(universal_cancel_handler, pattern='^(main_menu|cancel)$')
        ]
    """
    user = update.effective_user
    logger.info(f"User {user.id} ({user.username}) cancelled conversation via universal handler")
    
    # Clean up temporary CAPTCHA images if they exist
    captcha_image_path = context.user_data.get('captcha_image_path')
    if captcha_image_path and os.path.exists(captcha_image_path):
        try:
            os.remove(captcha_image_path)
            logger.info(f"Cleaned up CAPTCHA image: {captcha_image_path}")
        except Exception as e:
            logger.warning(f"Could not delete CAPTCHA image {captcha_image_path}: {e}")
    
    # Clean up any other temporary files stored in user_data
    temp_files = context.user_data.get('temp_files', [])
    for file_path in temp_files:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"Cleaned up temp file: {file_path}")
            except Exception as e:
                logger.warning(f"Could not delete temp file {file_path}: {e}")
    
    # Clear ALL user conversation state to prevent memory leaks
    context.user_data.clear()
    logger.debug(f"Cleared user_data for user {user.id}")
    
    # Send a friendly cancellation message
    cancel_message = (
        "❌ **Operation Cancelled**\n\n"
        "You've exited the current operation.\n"
        "Use /start to return to the main menu."
    )
    
    try:
        if update.callback_query:
            await update.callback_query.answer("Operation cancelled")
            await update.callback_query.message.reply_text(cancel_message, parse_mode='Markdown')
        elif update.message:
            await update.message.reply_text(cancel_message, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error sending cancellation message: {e}")
    
    # End the conversation
    return ConversationHandler.END


async def timeout_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handler for conversation timeouts.
    Automatically cleans up state when a conversation times out.
    
    Usage:
        Add conversation_timeout parameter to ConversationHandler:
        ConversationHandler(
            conversation_timeout=300,  # 5 minutes
            ...
        )
    """
    user = update.effective_user
    logger.info(f"Conversation timed out for user {user.id} ({user.username})")
    
    # Clean up resources (same as cancel)
    captcha_image_path = context.user_data.get('captcha_image_path')
    if captcha_image_path and os.path.exists(captcha_image_path):
        try:
            os.remove(captcha_image_path)
        except Exception as e:
            logger.warning(f"Could not delete CAPTCHA image on timeout: {e}")
    
    context.user_data.clear()
    
    timeout_message = (
        "⏱️ **Operation Timed Out**\n\n"
        "Your session has expired due to inactivity.\n"
        "Use /start to begin again."
    )
    
    try:
        if update.message:
            await update.message.reply_text(timeout_message, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error sending timeout message: {e}")
    
    return ConversationHandler.END


def escape_markdown_v2(text: str) -> str:
    """
    Escape special characters for MarkdownV2 parse mode.
    
    This prevents "Can't parse entities" errors when sending messages
    with user-generated or database content that contains special characters.
    
    Args:
        text: The text to escape
        
    Returns:
        Escaped text safe for MarkdownV2
        
    Usage:
        safe_username = escape_markdown_v2(user.username)
        await message.reply_text(
            f"Hello {safe_username}!",
            parse_mode='MarkdownV2'
        )
    """
    if not text:
        return ""
    
    # Characters that need to be escaped in MarkdownV2
    # Reference: https://core.telegram.org/bots/api#markdownv2-style
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    
    escaped_text = text
    for char in special_chars:
        escaped_text = escaped_text.replace(char, f'\\{char}')
    
    return escaped_text


def cleanup_temp_resource(file_path: str, resource_name: str = "file") -> bool:
    """
    Safely cleanup a temporary resource (file, image, etc.)
    
    Args:
        file_path: Path to the resource to delete
        resource_name: Human-readable name for logging
        
    Returns:
        True if cleanup succeeded, False otherwise
    """
    if not file_path or not os.path.exists(file_path):
        return True
    
    try:
        os.remove(file_path)
        logger.info(f"Successfully cleaned up {resource_name}: {file_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to cleanup {resource_name} at {file_path}: {e}")
        return False
