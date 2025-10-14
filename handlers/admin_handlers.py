"""
Admin command handlers for the Telegram Account Bot.
"""
import os
import logging
from typing import Dict, Any, List
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, ConversationHandler, MessageHandler, CallbackQueryHandler, filters
from database import get_db_session, close_db_session
from database.operations import UserService, AccountService, WithdrawalService, SystemSettingsService
from services.otp_monitor import OTPMonitor
from utils.helpers import MessageUtils

logger = logging.getLogger(__name__)

# Admin user ID from environment
ADMIN_USER_ID = int(os.getenv('ADMIN_USER_ID', 0))

# Conversation states
BROADCAST_MESSAGE = 0

def is_admin(user_id: int) -> bool:
    """Check if user is admin."""
    return user_id == ADMIN_USER_ID

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Main admin command handler."""
    user = update.effective_user
    
    if not is_admin(user.id):
        await update.message.reply_text("❌ Access denied. Admin privileges required.")
        return
    
    db = get_db_session()
    try:
        # Get system statistics
        all_users = UserService.get_all_active_users(db)
        
        # Get account statistics
        from database.models import Account
        total_accounts = db.query(Account).count()
        active_accounts = db.query(Account).filter(Account.status == 'ACTIVE').count()
        frozen_accounts = db.query(Account).filter(Account.status == 'FROZEN').count()
        banned_accounts = db.query(Account).filter(Account.status == 'BANNED').count()
        hold_accounts = db.query(Account).filter(Account.status == '24_HOUR_HOLD').count()
        
        # Get withdrawal statistics
        pending_withdrawals = WithdrawalService.get_pending_withdrawals(db)
        total_pending_amount = sum(w.amount for w in pending_withdrawals)
        
        admin_text = f"""
🛡️ **Admin Dashboard**

📊 **System Overview:**
• 👥 Total Users: {len(all_users)}
• 📱 Total Accounts: {total_accounts}
• ✅ Active: {active_accounts}
• ❄️ Frozen: {frozen_accounts}
• 🚫 Banned: {banned_accounts}
• ⏳ On Hold: {hold_accounts}

💸 **Withdrawals:**
• 📋 Pending Requests: {len(pending_withdrawals)}
• 💰 Pending Amount: {total_pending_amount:.2f} credits

🔧 **Quick Actions:**
        """
        
        keyboard = [
            [InlineKeyboardButton("💸 Manage Withdrawals", callback_data="admin_withdrawals")],
            [InlineKeyboardButton("📱 Account Management", callback_data="admin_accounts")],
            [InlineKeyboardButton("⚙️ System Settings", callback_data="admin_settings")],
            [InlineKeyboardButton("📢 Broadcast Message", callback_data="admin_broadcast")],
            [InlineKeyboardButton("📊 Detailed Stats", callback_data="admin_stats")],
            [InlineKeyboardButton("🔄 Refresh", callback_data="admin_refresh")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            admin_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Error in admin command: {e}")
        await update.message.reply_text(
            "❌ An error occurred while loading admin dashboard."
        )
    finally:
        close_db_session(db)

async def admin_withdrawals(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle withdrawal management."""
    query = update.callback_query
    await query.answer()
    
    if not is_admin(update.effective_user.id):
        await query.edit_message_text("❌ Access denied.")
        return
    
    db = get_db_session()
    try:
        pending_withdrawals = WithdrawalService.get_pending_withdrawals(db)
        
        if not pending_withdrawals:
            await query.edit_message_text(
                "💸 **Withdrawal Management**\n\n"
                "✅ No pending withdrawals!\n\n"
                "All withdrawal requests have been processed.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_refresh")
                ]])
            )
            return
        
        withdrawal_text = f"💸 **Pending Withdrawals ({len(pending_withdrawals)})**\n\n"
        
        for i, w in enumerate(pending_withdrawals[:10], 1):  # Show max 10
            withdrawal_text += f"""
**{i}. Request #{w.id}**
├ User: {w.user_id} 
├ Amount: {w.amount} {w.currency}
├ Address: `{w.destination_address[:20]}...`
├ Date: {w.created_at.strftime('%Y-%m-%d %H:%M')}
└ [Approve](callback://approve_{w.id}) | [Reject](callback://reject_{w.id})
            """
        
        if len(pending_withdrawals) > 10:
            withdrawal_text += f"\n... and {len(pending_withdrawals) - 10} more"
        
        keyboard = []
        for w in pending_withdrawals[:5]:  # Show buttons for first 5
            keyboard.append([
                InlineKeyboardButton(f"✅ Approve #{w.id}", callback_data=f"approve_withdrawal_{w.id}"),
                InlineKeyboardButton(f"❌ Reject #{w.id}", callback_data=f"reject_withdrawal_{w.id}")
            ])
        
        keyboard.append([InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_refresh")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            withdrawal_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Error in admin withdrawals: {e}")
        await query.edit_message_text("❌ Error loading withdrawals.")
    finally:
        close_db_session(db)

async def handle_withdrawal_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle withdrawal approval/rejection."""
    query = update.callback_query
    await query.answer()
    
    if not is_admin(update.effective_user.id):
        await query.edit_message_text("❌ Access denied.")
        return
    
    try:
        data_parts = query.data.split('_')
        action = data_parts[0]  # 'approve' or 'reject'
        withdrawal_id = int(data_parts[2])
        
        db = get_db_session()
        try:
            if action == 'approve':
                success = WithdrawalService.update_withdrawal_status(
                    db=db,
                    withdrawal_id=withdrawal_id,
                    status='COMPLETED',
                    admin_id=update.effective_user.id,
                    admin_notes=f"Approved by admin {update.effective_user.id}"
                )
                
                if success:
                    await query.edit_message_text(
                        f"✅ **Withdrawal #{withdrawal_id} Approved**\n\n"
                        f"The withdrawal has been marked as completed.\n"
                        f"The user will be notified automatically."
                    )
                else:
                    await query.edit_message_text(f"❌ Failed to approve withdrawal #{withdrawal_id}")
                    
            elif action == 'reject':
                success = WithdrawalService.update_withdrawal_status(
                    db=db,
                    withdrawal_id=withdrawal_id,
                    status='REJECTED',
                    admin_id=update.effective_user.id,
                    admin_notes=f"Rejected by admin {update.effective_user.id}"
                )
                
                if success:
                    # Refund the amount to user balance
                    from database.models import Withdrawal
                    withdrawal = db.query(Withdrawal).filter(Withdrawal.id == withdrawal_id).first()
                    if withdrawal:
                        UserService.update_user_balance(db, withdrawal.user_id, withdrawal.amount)
                    
                    await query.edit_message_text(
                        f"❌ **Withdrawal #{withdrawal_id} Rejected**\n\n"
                        f"The withdrawal has been rejected and funds refunded.\n"
                        f"The user will be notified automatically."
                    )
                else:
                    await query.edit_message_text(f"❌ Failed to reject withdrawal #{withdrawal_id}")
        finally:
            close_db_session(db)
            
    except Exception as e:
        logger.error(f"Error handling withdrawal action: {e}")
        await query.edit_message_text("❌ Error processing withdrawal action.")

async def admin_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle system settings."""
    query = update.callback_query
    await query.answer()
    
    if not is_admin(update.effective_user.id):
        await query.edit_message_text("❌ Access denied.")
        return
    
    db = get_db_session()
    try:
        # Get current settings
        usdt_enabled = SystemSettingsService.is_withdrawal_enabled(db, 'USDT-BEP20')
        trx_enabled = SystemSettingsService.is_withdrawal_enabled(db, 'TRX')
        
        settings_text = f"""
⚙️ **System Settings**

💸 **Withdrawal Settings:**
• USDT-BEP20: {'✅ Enabled' if usdt_enabled else '❌ Disabled'}
• TRX: {'✅ Enabled' if trx_enabled else '❌ Disabled'}

🔧 **Configuration:**
        """
        
        keyboard = [
            [InlineKeyboardButton(
                f"{'❌ Disable' if usdt_enabled else '✅ Enable'} USDT Withdrawals",
                callback_data=f"toggle_withdrawal_usdt-bep20"
            )],
            [InlineKeyboardButton(
                f"{'❌ Disable' if trx_enabled else '✅ Enable'} TRX Withdrawals",
                callback_data=f"toggle_withdrawal_trx"
            )],
            [InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_refresh")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            settings_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Error in admin settings: {e}")
        await query.edit_message_text("❌ Error loading settings.")
    finally:
        close_db_session(db)

async def toggle_withdrawal_setting(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Toggle withdrawal settings."""
    query = update.callback_query
    await query.answer()
    
    if not is_admin(update.effective_user.id):
        await query.edit_message_text("❌ Access denied.")
        return
    
    try:
        currency = query.data.replace('toggle_withdrawal_', '').upper()
        
        db = get_db_session()
        try:
            current_status = SystemSettingsService.is_withdrawal_enabled(db, currency)
            new_status = not current_status
            
            SystemSettingsService.set_setting(
                db=db,
                key=f"withdrawal_{currency.lower()}_enabled",
                value='true' if new_status else 'false',
                description=f"Enable/disable {currency} withdrawals"
            )
            
            await query.edit_message_text(
                f"✅ **Setting Updated**\n\n"
                f"💎 **Currency:** {currency}\n"
                f"📊 **Status:** {'✅ Enabled' if new_status else '❌ Disabled'}\n\n"
                f"The setting has been updated successfully.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Back to Settings", callback_data="admin_settings")
                ]])
            )
            
        finally:
            close_db_session(db)
            
    except Exception as e:
        logger.error(f"Error toggling withdrawal setting: {e}")
        await query.edit_message_text("❌ Error updating setting.")

async def start_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start broadcast message process."""
    query = update.callback_query
    await query.answer()
    
    if not is_admin(update.effective_user.id):
        await query.edit_message_text("❌ Access denied.")
        return ConversationHandler.END
    
    await query.edit_message_text(
        "📢 **Broadcast Message**\n\n"
        "Send a message that will be delivered to all active users.\n\n"
        "**Please enter your message:**\n"
        "• You can use Markdown formatting\n"
        "• Keep it concise and clear\n"
        "• Avoid spam or excessive messaging\n\n"
        "**Enter your broadcast message:**"
    )
    
    return BROADCAST_MESSAGE

async def handle_broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle broadcast message input."""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Access denied.")
        return ConversationHandler.END
    
    message_text = update.message.text
    
    if len(message_text) > 4000:
        await update.message.reply_text(
            "❌ **Message too long!**\n\n"
            "Please keep your message under 4000 characters.\n"
            "Current length: {len(message_text)} characters\n\n"
            "**Please enter a shorter message:**"
        )
        return BROADCAST_MESSAGE
    
    # Confirm broadcast
    confirm_text = f"""
📢 **Confirm Broadcast**

**Preview:**
{message_text}

**This message will be sent to ALL active users.**

Are you sure you want to proceed?
    """
    
    keyboard = [
        [InlineKeyboardButton("✅ Send Broadcast", callback_data=f"confirm_broadcast")],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel_broadcast")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Store message in context
    context.user_data['broadcast_message'] = message_text
    
    await update.message.reply_text(
        confirm_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    
    return ConversationHandler.END

async def confirm_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Confirm and send broadcast."""
    query = update.callback_query
    await query.answer()
    
    if not is_admin(update.effective_user.id):
        await query.edit_message_text("❌ Access denied.")
        return
    
    message_text = context.user_data.get('broadcast_message')
    if not message_text:
        await query.edit_message_text("❌ No message found. Please try again.")
        return
    
    await query.edit_message_text(
        "📢 **Broadcasting Message...**\n\n"
        "Please wait while the message is sent to all users.\n"
        "This may take a few minutes."
    )
    
    # Send broadcast
    db = get_db_session()
    try:
        active_users = UserService.get_all_active_users(db)
        
        sent_count = 0
        failed_count = 0
        
        broadcast_header = "📢 **System Announcement**\n\n"
        full_message = broadcast_header + message_text
        
        for user in active_users:
            try:
                await context.bot.send_message(
                    chat_id=user.telegram_user_id,
                    text=full_message,
                    parse_mode='Markdown'
                )
                sent_count += 1
                
                # Small delay to avoid rate limiting
                if sent_count % 20 == 0:
                    await asyncio.sleep(1)
                    
            except Exception as e:
                logger.warning(f"Failed to send broadcast to user {user.telegram_user_id}: {e}")
                failed_count += 1
        
        result_text = f"""
✅ **Broadcast Complete**

📊 **Results:**
• ✅ Successfully sent: {sent_count}
• ❌ Failed to send: {failed_count}
• 📱 Total users: {len(active_users)}

The broadcast has been completed!
        """
        
        await query.edit_message_text(
            result_text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_refresh")
            ]])
        )
        
        logger.info(f"Broadcast completed: {sent_count} sent, {failed_count} failed")
        
    except Exception as e:
        logger.error(f"Error during broadcast: {e}")
        await query.edit_message_text(
            f"❌ **Broadcast Failed**\n\n"
            f"An error occurred during the broadcast:\n"
            f"`{str(e)}`"
        )
    finally:
        close_db_session(db)

async def admin_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle admin callback queries."""
    query = update.callback_query
    
    if query.data == "admin_refresh":
        await admin_command(update, context)
    elif query.data == "admin_withdrawals":
        await admin_withdrawals(update, context)
    elif query.data == "admin_settings":
        await admin_settings(update, context)
    elif query.data.startswith("approve_withdrawal_") or query.data.startswith("reject_withdrawal_"):
        await handle_withdrawal_action(update, context)
    elif query.data.startswith("toggle_withdrawal_"):
        await toggle_withdrawal_setting(update, context)
    elif query.data == "confirm_broadcast":
        await confirm_broadcast(update, context)
    elif query.data == "cancel_broadcast":
        await query.edit_message_text(
            "❌ **Broadcast Cancelled**\n\n"
            "The broadcast message was not sent."
        )

def setup_admin_handlers(application) -> None:
    """Set up admin command handlers."""
    
    # Basic admin command
    application.add_handler(CommandHandler("admin", admin_command))
    
    # Broadcast conversation handler
    broadcast_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_broadcast, pattern="^admin_broadcast$")
        ],
        states={
            BROADCAST_MESSAGE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_broadcast_message)
            ]
        },
        fallbacks=[
            CallbackQueryHandler(lambda u, c: ConversationHandler.END, pattern="^cancel_broadcast$")
        ],
        allow_reentry=True
    )
    
    application.add_handler(broadcast_handler)
    
    # Admin callback handlers
    application.add_handler(CallbackQueryHandler(
        admin_callback_handler,
        pattern="^(admin_|approve_|reject_|toggle_|confirm_|cancel_)"
    ))
    
    logger.info("Admin handlers set up successfully")