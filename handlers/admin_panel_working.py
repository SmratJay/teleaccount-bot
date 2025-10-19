"""
COMPLETE ADMIN PANEL IMPLEMENTATION WITH WORKING MAILING MODE
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CallbackQueryHandler, MessageHandler, CommandHandler, filters

from database import get_db_session, close_db_session
from database.models import User, UserStatus

logger = logging.getLogger(__name__)

# Conversation states for mailing
MAIL_TARGET_SELECT = 1
MAIL_USER_ID_INPUT = 2
MAIL_MESSAGE_INPUT = 3

def is_admin_or_leader(user_id: int) -> bool:
    """Check if user is admin or leader."""
    db = get_db_session()
    try:
        user = db.query(User).filter(User.telegram_user_id == user_id).first()
        if user:
            return user.is_admin or user.is_leader
        return False
    finally:
        close_db_session(db)

async def admin_panel_main(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Main admin panel."""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    if not is_admin_or_leader(user_id):
        await query.edit_message_text("❌ Access denied. Admin/Leader privileges required.")
        return
    
    admin_text = """
🔧 **ADMIN CONTROL PANEL**

Welcome to the administration dashboard!

**Available Functions:**
📢 **Mailing Mode** - Broadcast messages to users
👥 **User Management** - View and edit user data
📊 **Statistics** - View system stats
⚙️ **Settings** - Configure bot settings

Choose an option below:
    """
    
    keyboard = [
        [InlineKeyboardButton("📢 Mailing Mode", callback_data="admin_mailing_start")],
        [InlineKeyboardButton("👥 User Management", callback_data="admin_users")],
        [InlineKeyboardButton("📊 Statistics", callback_data="admin_stats")],
        [InlineKeyboardButton("⚙️ Settings", callback_data="admin_settings")],
        [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        admin_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def admin_mailing_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start mailing mode - show options."""
    query = update.callback_query
    await query.answer()
    
    mailing_text = """
📢 **MAILING MODE**

Choose how you want to send your message:

**Options:**
👤 **Specific User** - Send to a single user by ID
📡 **All Users** - Broadcast to everyone in the database

Select your target:
    """
    
    keyboard = [
        [InlineKeyboardButton("👤 Mail to Specific User", callback_data="mail_specific")],
        [InlineKeyboardButton("📡 Mail to All Users", callback_data="mail_all")],
        [InlineKeyboardButton("🔙 Back to Admin Panel", callback_data="admin_panel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        mailing_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    
    return MAIL_TARGET_SELECT

async def mail_specific_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Ask for specific user ID."""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "👤 **Send to Specific User**\n\n"
        "Please enter the Telegram User ID of the recipient:\n"
        "(You can find user IDs in the User Management section)\n\n"
        "Type /cancel to abort.",
        parse_mode='Markdown'
    )
    
    return MAIL_USER_ID_INPUT

async def receive_user_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive and validate user ID."""
    try:
        user_id = int(update.message.text.strip())
        
        # Check if user exists
        db = get_db_session()
        try:
            target_user = db.query(User).filter(User.telegram_user_id == user_id).first()
            if not target_user:
                await update.message.reply_text(
                    f"❌ User with ID {user_id} not found in database.\n\n"
                    "Please try again or type /cancel to abort."
                )
                return MAIL_USER_ID_INPUT
            
            # Store user ID in context
            context.user_data['mail_target_id'] = user_id
            context.user_data['mail_target_name'] = target_user.first_name or "Unknown"
            
            await update.message.reply_text(
                f"✅ Target user: {target_user.first_name} (ID: {user_id})\n\n"
                "📝 Now, please type or paste the message you want to send:\n\n"
                "Type /cancel to abort.",
                parse_mode='Markdown'
            )
            
            return MAIL_MESSAGE_INPUT
            
        finally:
            close_db_session(db)
            
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid format. Please enter a numeric user ID.\n\n"
            "Type /cancel to abort."
        )
        return MAIL_USER_ID_INPUT

async def mail_all_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Prepare to mail all users."""
    query = update.callback_query
    await query.answer()
    
    # Count users
    db = get_db_session()
    try:
        total_users = db.query(User).count()
    finally:
        close_db_session(db)
    
    context.user_data['mail_target_id'] = 'all'
    
    await query.edit_message_text(
        f"📡 **Broadcast to All Users**\n\n"
        f"Total recipients: **{total_users}** users\n\n"
        f"📝 Please type or paste the message you want to broadcast:\n\n"
        f"Type /cancel to abort.",
        parse_mode='Markdown'
    )
    
    return MAIL_MESSAGE_INPUT

async def receive_and_send_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive message and send it to target(s)."""
    message_text = update.message.text
    target = context.user_data.get('mail_target_id')
    
    if not target:
        await update.message.reply_text("❌ Error: No target specified. Please start over.")
        return ConversationHandler.END
    
    db = get_db_session()
    try:
        if target == 'all':
            # Broadcast to all users
            all_users = db.query(User).all()
            total = len(all_users)
            success = 0
            failed = 0
            
            progress_msg = await update.message.reply_text(
                f"📡 **Broadcasting...**\n\n"
                f"Total users: {total}\n"
                f"✅ Sent: 0\n"
                f"❌ Failed: 0\n\n"
                f"Please wait...",
                parse_mode='Markdown'
            )
            
            for i, user in enumerate(all_users, 1):
                try:
                    await context.bot.send_message(
                        chat_id=user.telegram_user_id,
                        text=f"📢 **System Broadcast**\n\n{message_text}",
                        parse_mode='Markdown'
                    )
                    success += 1
                except Exception as e:
                    logger.error(f"Failed to send to user {user.telegram_user_id}: {e}")
                    failed += 1
                
                # Update progress every 10 users
                if i % 10 == 0 or i == total:
                    try:
                        await progress_msg.edit_text(
                            f"📡 **Broadcasting...**\n\n"
                            f"Progress: {i}/{total}\n"
                            f"✅ Sent: {success}\n"
                            f"❌ Failed: {failed}",
                            parse_mode='Markdown'
                        )
                    except:
                        pass
            
            await progress_msg.edit_text(
                f"✅ **Broadcast Complete!**\n\n"
                f"Total users: {total}\n"
                f"✅ Successfully sent: {success}\n"
                f"❌ Failed: {failed}\n\n"
                f"Message sent:\n{message_text[:100]}{'...' if len(message_text) > 100 else ''}",
                parse_mode='Markdown'
            )
            
        else:
            # Send to specific user
            try:
                await context.bot.send_message(
                    chat_id=target,
                    text=f"📨 **Message from Admin**\n\n{message_text}",
                    parse_mode='Markdown'
                )
                
                target_name = context.user_data.get('mail_target_name', 'Unknown')
                await update.message.reply_text(
                    f"✅ **Message Sent Successfully!**\n\n"
                    f"Recipient: {target_name} (ID: {target})\n\n"
                    f"Message sent:\n{message_text[:100]}{'...' if len(message_text) > 100 else ''}",
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Failed to send message to {target}: {e}")
                await update.message.reply_text(
                    f"❌ **Failed to send message**\n\n"
                    f"Error: {str(e)}\n\n"
                    f"The user may have blocked the bot or deleted their account.",
                    parse_mode='Markdown'
                )
    
    finally:
        close_db_session(db)
        # Clear context
        context.user_data.clear()
    
    return ConversationHandler.END

async def cancel_mailing(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the mailing operation."""
    context.user_data.clear()
    await update.message.reply_text(
        "❌ Mailing operation cancelled.\n\n"
        "Returning to admin panel..."
    )
    return ConversationHandler.END

def get_admin_mailing_conversation_handler():
    """Get the conversation handler for admin mailing."""
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(admin_mailing_start, pattern="^admin_mailing_start$")
        ],
        states={
            MAIL_TARGET_SELECT: [
                CallbackQueryHandler(mail_specific_user, pattern="^mail_specific$"),
                CallbackQueryHandler(mail_all_users, pattern="^mail_all$"),
            ],
            MAIL_USER_ID_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_user_id),
            ],
            MAIL_MESSAGE_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_and_send_message),
            ],
        },
        fallbacks=[
            CommandHandler('cancel', cancel_mailing),
            CallbackQueryHandler(admin_panel_main, pattern="^admin_panel$"),
        ],
        per_message=False,
    )
