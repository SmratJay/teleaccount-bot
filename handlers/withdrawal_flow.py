"""
Withdrawal Flow Handlers
Handles withdrawal requests and leader approval workflows
"""
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import get_db_session, close_db_session
from database.operations import UserService, ActivityLogService, WithdrawalService
from database.models import Withdrawal, WithdrawalStatus, User
from services.translation_service import translation_service

logger = logging.getLogger(__name__)


async def handle_approve_withdrawal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle withdrawal approval by leaders."""
    query = update.callback_query
    user = update.effective_user
    
    # Extract withdrawal ID from callback data
    withdrawal_id = int(query.data.split("_")[-1])
    
    db = get_db_session()
    try:
        # Check if user is a leader
        db_user = UserService.get_user_by_telegram_id(db, user.id)
        if not db_user or not db_user.is_leader:
            await query.edit_message_text("❌ Access denied. Only leaders can approve withdrawals.")
            return
        
        # Get withdrawal
        withdrawal = WithdrawalService.get_withdrawal(db, withdrawal_id)
        if not withdrawal:
            await query.edit_message_text("❌ Withdrawal not found.")
            return
        
        if withdrawal.status != WithdrawalStatus.PENDING:
            await query.edit_message_text(f"❌ Withdrawal already {withdrawal.status.value.lower()}.")
            return
        
        # Get withdrawal user
        withdrawal_user = UserService.get_user(db, withdrawal.user_id)
        if not withdrawal_user:
            await query.edit_message_text("❌ User not found.")
            return
        
        # Check balance
        if withdrawal_user.balance < withdrawal.amount:
            await query.edit_message_text("❌ Error: User has insufficient balance for this withdrawal.")
            return
        
        # Update withdrawal status
        WithdrawalService.update_withdrawal_status(
            db, withdrawal_id, WithdrawalStatus.LEADER_APPROVED,
            admin_notes=f"Approved by {db_user.first_name}"
        )
        
        # Deduct the amount from user's balance
        UserService.update_balance(db, withdrawal_user.id, withdrawal_user.balance - withdrawal.amount)
        
        # Refresh withdrawal object
        withdrawal = WithdrawalService.get_withdrawal(db, withdrawal_id)
        withdrawal_user = UserService.get_user(db, withdrawal.user_id)
        
        # Update the message to show approval
        approval_text = (
            f"✅ **WITHDRAWAL APPROVED**\n\n"
            f"👤 User: {withdrawal_user.first_name or 'Unknown'} (@{withdrawal_user.username or 'no_username'})\n"
            f"💰 Amount: *${withdrawal.amount:.2f}*\n"
            f"💳 Method: *{withdrawal.withdrawal_method}*\n"
            f"📍 Address: `{withdrawal.withdrawal_address}`\n"
            f"👑 Approved by: {db_user.first_name} (@{db_user.username})\n"
            f"💸 **Balance Deducted: ${withdrawal.amount:.2f}**\n"
            f"💰 **User's New Balance: ${withdrawal_user.balance:.2f}**\n\n"
            f"⚡ **Next Step:** Process payment and mark as paid"
        )
        
        keyboard = [
            [InlineKeyboardButton("💰 Mark as Paid", callback_data=f"mark_paid_{withdrawal.id}")],
            [InlineKeyboardButton("👤 View User", callback_data=f"view_user_{withdrawal_user.telegram_user_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(approval_text, parse_mode='Markdown', reply_markup=reply_markup)
        
        # Notify user of approval
        try:
            user_lang = 'en'
            
            approval_user_text = (
                f"✅ **Withdrawal Approved!**\n\n"
                f"💰 **Amount:** ${withdrawal.amount:.2f}\n"
                f"💳 **Method:** {withdrawal.withdrawal_method}\n"
                f"📍 **Address:** {withdrawal.withdrawal_address}\n"
                f"💸 **Amount deducted from balance**\n"
                f"💰 **New Balance:** ${withdrawal_user.balance:.2f}\n\n"
                f"🚀 **Status:** LEADER APPROVED ✅\n\n"
                f"⏳ Your payment is being processed and will be sent to your address shortly."
            )
            await context.bot.send_message(
                chat_id=withdrawal_user.telegram_user_id,
                text=approval_user_text,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Failed to notify user of withdrawal approval: {e}")
        
        # Log activity
        ActivityLogService.log_action(
            db, withdrawal.user_id, "WITHDRAWAL_APPROVED",
            f"Withdrawal ${withdrawal.amount:.2f} approved by leader {db_user.first_name}"
        )
            
    except Exception as e:
        logger.error(f"Error approving withdrawal: {e}")
        await query.edit_message_text("❌ Error processing approval. Please try again.")
    finally:
        close_db_session(db)


async def handle_reject_withdrawal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle withdrawal rejection by leaders."""
    query = update.callback_query
    user = update.effective_user
    
    # Extract withdrawal ID from callback data
    withdrawal_id = int(query.data.split("_")[-1])
    
    db = get_db_session()
    try:
        # Check if user is a leader
        db_user = UserService.get_user_by_telegram_id(db, user.id)
        if not db_user or not db_user.is_leader:
            await query.edit_message_text("❌ Access denied. Only leaders can reject withdrawals.")
            return
        
        # Get withdrawal
        withdrawal = WithdrawalService.get_withdrawal(db, withdrawal_id)
        if not withdrawal:
            await query.edit_message_text("❌ Withdrawal not found.")
            return
        
        if withdrawal.status != WithdrawalStatus.PENDING:
            await query.edit_message_text(f"❌ Withdrawal already {withdrawal.status.value.lower()}.")
            return
        
        # Update withdrawal status
        WithdrawalService.update_withdrawal_status(
            db, withdrawal_id, WithdrawalStatus.REJECTED,
            admin_notes=f"Rejected by {db_user.first_name}"
        )
        
        # Get user who made the withdrawal
        withdrawal_user = UserService.get_user(db, withdrawal.user_id)
        
        # Update the message to show rejection
        rejection_text = (
            f"❌ **WITHDRAWAL REJECTED**\n\n"
            f"👤 User: {withdrawal_user.first_name or 'Unknown'} (@{withdrawal_user.username or 'no_username'})\n"
            f"💰 Amount: *${withdrawal.amount:.2f}*\n"
            f"💳 Method: *{withdrawal.withdrawal_method}*\n"
            f"📍 Address: `{withdrawal.withdrawal_address}`\n"
            f"👑 Rejected by: {db_user.first_name} (@{db_user.username})\n\n"
            f"❌ **Status:** REJECTED"
        )
        
        await query.edit_message_text(rejection_text, parse_mode='Markdown')
        
        # Notify user of rejection
        try:
            rejection_user_text = (
                f"❌ **Withdrawal Rejected**\n\n"
                f"💰 **Amount:** ${withdrawal.amount:.2f}\n"
                f"💳 **Method:** {withdrawal.withdrawal_method}\n"
                f"📍 **Address:** {withdrawal.withdrawal_address}\n\n"
                f"❌ **Status:** REJECTED ❌\n"
                f"👑 **Rejected By:** Leader\n\n"
                f"💰 **Your balance remains:** ${withdrawal_user.balance:.2f}\n"
                f"📞 Please contact support if you have questions about this rejection.\n"
                f"🔄 You can submit a new withdrawal request if needed."
            )
            await context.bot.send_message(
                chat_id=withdrawal_user.telegram_user_id,
                text=rejection_user_text,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Failed to notify user of withdrawal rejection: {e}")
        
        # Log activity
        ActivityLogService.log_action(
            db, withdrawal.user_id, "WITHDRAWAL_REJECTED",
            f"Withdrawal ${withdrawal.amount:.2f} rejected by leader {db_user.first_name}"
        )
            
    except Exception as e:
        logger.error(f"Error rejecting withdrawal: {e}")
        await query.edit_message_text("❌ Error processing rejection. Please try again.")
    finally:
        close_db_session(db)


async def handle_mark_paid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle marking withdrawal as paid."""
    query = update.callback_query
    user = update.effective_user
    
    # Extract withdrawal ID from callback data
    withdrawal_id = int(query.data.split("_")[-1])
    
    db = get_db_session()
    try:
        # Check if user is a leader
        db_user = UserService.get_user_by_telegram_id(db, user.id)
        if not db_user or not db_user.is_leader:
            await query.edit_message_text("❌ Access denied. Only leaders can mark withdrawals as paid.")
            return
        
        # Get withdrawal
        withdrawal = WithdrawalService.get_withdrawal(db, withdrawal_id)
        if not withdrawal:
            await query.edit_message_text("❌ Withdrawal not found.")
            return
        
        if withdrawal.status != WithdrawalStatus.LEADER_APPROVED:
            await query.edit_message_text(f"❌ Withdrawal must be approved first. Current status: {withdrawal.status.value}")
            return
        
        # Update withdrawal status
        WithdrawalService.update_withdrawal_status(
            db, withdrawal_id, WithdrawalStatus.COMPLETED,
            admin_notes=f"Payment completed by {db_user.first_name}"
        )
        
        # Get user who made the withdrawal
        withdrawal_user = UserService.get_user(db, withdrawal.user_id)
        
        # Update user's total withdrawn
        if withdrawal_user:
            UserService.update_user(
                db, withdrawal_user.id,
                total_withdrawn=withdrawal_user.total_withdrawn + withdrawal.amount
            )
        
        # Update the message to show completion
        completion_text = (
            f"✅ **WITHDRAWAL COMPLETED**\n\n"
            f"👤 User: {withdrawal_user.first_name or 'Unknown'} (@{withdrawal_user.username or 'no_username'})\n"
            f"💰 Amount: *${withdrawal.amount:.2f}*\n"
            f"💳 Method: *{withdrawal.withdrawal_method}*\n"
            f"📍 Address: `{withdrawal.withdrawal_address}`\n"
            f"💳 Completed by: {db_user.first_name} (@{db_user.username})\n\n"
            f"✅ **Status:** PAID & COMPLETED"
        )
        
        await query.edit_message_text(completion_text, parse_mode='Markdown')
        
        # Notify user of completion
        try:
            completion_user_text = (
                f"🎉 **Withdrawal Completed!**\n\n"
                f"💰 **Amount:** ${withdrawal.amount:.2f}\n"
                f"💳 **Method:** {withdrawal.withdrawal_method}\n"
                f"📍 **Address:** {withdrawal.withdrawal_address}\n\n"
                f"✅ **Status:** PAYMENT SENT! 🚀\n"
                f"💳 **Processed By:** Leader Team\n\n"
                f"🎯 **Your payment has been successfully sent to your address!**\n"
                f"💎 Thank you for using our service.\n"
                f"📈 You can continue selling more accounts to earn more!"
            )
            await context.bot.send_message(
                chat_id=withdrawal_user.telegram_user_id,
                text=completion_user_text,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Failed to notify user of withdrawal completion: {e}")
        
        # Log activity
        ActivityLogService.log_action(
            db, withdrawal.user_id, "WITHDRAWAL_COMPLETED",
            f"Withdrawal ${withdrawal.amount:.2f} completed by leader {db_user.first_name}"
        )
            
    except Exception as e:
        logger.error(f"Error marking withdrawal as paid: {e}")
        await query.edit_message_text("❌ Error processing payment confirmation. Please try again.")
    finally:
        close_db_session(db)


async def handle_view_user_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle viewing user details from withdrawal context."""
    query = update.callback_query
    user = update.effective_user
    
    # Extract user telegram ID from callback data
    user_telegram_id = int(query.data.split("_")[-1])
    
    db = get_db_session()
    try:
        # Check if requester is a leader
        db_user = UserService.get_user_by_telegram_id(db, user.id)
        if not db_user or not db_user.is_leader:
            await query.edit_message_text("❌ Access denied. Only leaders can view user details.")
            return
        
        # Get target user
        target_user = UserService.get_user_by_telegram_id(db, user_telegram_id)
        if not target_user:
            await query.edit_message_text("❌ User not found.")
            return
        
        # Get user's withdrawals
        withdrawals = WithdrawalService.get_user_withdrawals(db, target_user.id, limit=5)
        
        details_text = f"""
👤 **User Details**

**Profile:**
• Name: {target_user.first_name or 'N/A'} {target_user.last_name or ''}
• Username: @{target_user.username or 'no_username'}
• User ID: `{target_user.telegram_user_id}`
• Status: {target_user.status.value}

**Financial:**
• Balance: ${target_user.balance:.2f}
• Total Earnings: ${target_user.total_earnings:.2f}
• Total Withdrawn: ${target_user.total_withdrawn:.2f}
• Accounts Sold: {target_user.total_accounts_sold}

**Recent Withdrawals:**
"""
        
        if withdrawals:
            for w in withdrawals:
                status_icon = "✅" if w.status == WithdrawalStatus.COMPLETED else "⏳"
                details_text += f"\n{status_icon} ${w.amount:.2f} - {w.status.value} - {w.created_at.strftime('%b %d')}"
        else:
            details_text += "\n_No withdrawals yet_"
        
        keyboard = [[InlineKeyboardButton("← Back", callback_data="leader_panel")]]
        await query.edit_message_text(
            details_text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        logger.error(f"Error viewing user details: {e}")
        await query.edit_message_text("❌ Error loading user details. Please try again.")
    finally:
        close_db_session(db)
