"""Additional security and admin management handlers."""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters, CallbackQueryHandler
from database import get_db_session, close_db_session
from database.operations import UserService, ActivityLogService
from utils.helpers import is_admin

logger = logging.getLogger(__name__)

# Conversation states
ADMIN_ID_INPUT = 1


async def handle_view_all_admins(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """View all admin users."""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    if not is_admin(user.id):
        await query.edit_message_text('❌ Access denied.')
        return
    
    db = get_db_session()
    try:
        from database.models import User
        admins = db.query(User).filter(User.is_admin == True).all()
        
        if not admins:
            text = "👥 **ALL ADMINS**\n\nNo admin users found in database."
        else:
            text = f"👥 **ALL ADMINS** ({len(admins)})\n\n"
            for admin in admins:
                text += f"• @{admin.username or 'No username'} (ID: {admin.telegram_user_id})\n"
                text += f"  └ Name: {admin.first_name or 'N/A'}\n"
        
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="settings_security")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)
        
    finally:
        close_db_session(db)


async def handle_view_all_leaders(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """View all leader users."""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    if not is_admin(user.id):
        await query.edit_message_text('❌ Access denied.')
        return
    
    db = get_db_session()
    try:
        from database.models import User
        leaders = db.query(User).filter(User.is_leader == True).all()
        
        if not leaders:
            text = "👥 **ALL LEADERS**\n\nNo leader users found in database."
        else:
            text = f"👥 **ALL LEADERS** ({len(leaders)})\n\n"
            for leader in leaders:
                text += f"• @{leader.username or 'No username'} (ID: {leader.telegram_user_id})\n"
                text += f"  └ Name: {leader.first_name or 'N/A'}\n"
        
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="settings_security")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)
        
    finally:
        close_db_session(db)


async def handle_add_admin_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start add admin conversation."""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    if not is_admin(user.id):
        await query.edit_message_text('❌ Access denied.')
        return ConversationHandler.END
    
    text = """
➕ **ADD ADMIN**

Please send the Telegram User ID of the person you want to make an admin.

You can get the user ID from their profile or by asking them to use a bot like @userinfobot.

Send /cancel to abort.
    """
    
    await query.edit_message_text(text, parse_mode='Markdown')
    return ADMIN_ID_INPUT


async def handle_add_admin_id_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process admin ID input."""
    user_id_str = update.message.text.strip()
    
    try:
        target_user_id = int(user_id_str)
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID. Please send a valid numeric Telegram user ID.")
        return ADMIN_ID_INPUT
    
    db = get_db_session()
    try:
        # Check if user exists
        target_user = UserService.get_user_by_telegram_id(db, target_user_id)
        
        if not target_user:
            await update.message.reply_text(
                f"❌ User with ID {target_user_id} not found in database.\n\n"
                "The user must interact with the bot first before being made an admin."
            )
            return ConversationHandler.END
        
        # Set as admin
        target_user.is_admin = True
        db.commit()
        
        # Log action
        admin_user = UserService.get_user_by_telegram_id(db, update.effective_user.id)
        if admin_user:
            ActivityLogService.log_action(
                db, admin_user.id, "ADMIN_GRANT",
                f"Granted admin privileges to user {target_user_id}",
                extra_data=f'{{"target_user_id": {target_user_id}}}'
            )
        
        await update.message.reply_text(
            f"✅ **ADMIN GRANTED**\n\n"
            f"User @{target_user.username or 'Unknown'} (ID: {target_user_id}) is now an admin!",
            parse_mode='Markdown'
        )
        
        return ConversationHandler.END
        
    finally:
        close_db_session(db)


async def handle_remove_admin_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start remove admin conversation."""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    if not is_admin(user.id):
        await query.edit_message_text('❌ Access denied.')
        return ConversationHandler.END
    
    text = """
➖ **REMOVE ADMIN**

Please send the Telegram User ID of the admin you want to remove.

⚠️ **Warning:** This will revoke their admin privileges immediately.

Send /cancel to abort.
    """
    
    await query.edit_message_text(text, parse_mode='Markdown')
    return ADMIN_ID_INPUT


async def handle_remove_admin_id_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process admin removal."""
    user_id_str = update.message.text.strip()
    
    try:
        target_user_id = int(user_id_str)
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID. Please send a valid numeric Telegram user ID.")
        return ADMIN_ID_INPUT
    
    # Prevent self-removal
    if target_user_id == update.effective_user.id:
        await update.message.reply_text("❌ You cannot remove yourself as admin!")
        return ConversationHandler.END
    
    db = get_db_session()
    try:
        target_user = UserService.get_user_by_telegram_id(db, target_user_id)
        
        if not target_user:
            await update.message.reply_text(f"❌ User with ID {target_user_id} not found.")
            return ConversationHandler.END
        
        if not target_user.is_admin:
            await update.message.reply_text(f"❌ User {target_user_id} is not an admin.")
            return ConversationHandler.END
        
        # Remove admin
        target_user.is_admin = False
        db.commit()
        
        # Log action
        admin_user = UserService.get_user_by_telegram_id(db, update.effective_user.id)
        if admin_user:
            ActivityLogService.log_action(
                db, admin_user.id, "ADMIN_REVOKE",
                f"Revoked admin privileges from user {target_user_id}",
                extra_data=f'{{"target_user_id": {target_user_id}}}'
            )
        
        await update.message.reply_text(
            f"✅ **ADMIN REMOVED**\n\n"
            f"User @{target_user.username or 'Unknown'} (ID: {target_user_id}) is no longer an admin.",
            parse_mode='Markdown'
        )
        
        return ConversationHandler.END
        
    finally:
        close_db_session(db)


async def cancel_admin_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel admin management conversation."""
    await update.message.reply_text("❌ Operation cancelled.")
    return ConversationHandler.END


def get_add_admin_conversation():
    """Get add admin conversation handler."""
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(handle_add_admin_start, pattern='^add_admin$')
        ],
        states={
            ADMIN_ID_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_add_admin_id_input)
            ]
        },
        fallbacks=[
            MessageHandler(filters.Regex('^/cancel$'), cancel_admin_conversation)
        ],
        per_user=True,
        per_chat=True
    )


def get_remove_admin_conversation():
    """Get remove admin conversation handler."""
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(handle_remove_admin_start, pattern='^remove_admin$')
        ],
        states={
            ADMIN_ID_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_remove_admin_id_input)
            ]
        },
        fallbacks=[
            MessageHandler(filters.Regex('^/cancel$'), cancel_admin_conversation)
        ],
        per_user=True,
        per_chat=True
    )
