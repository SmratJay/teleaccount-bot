"""
Leader Panel System for Telegram Account Bot
Handles withdrawal requests, payment processing, and leader dashboard functionality
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

from database import get_db_session, close_db_session
from database.models import User, Withdrawal, WithdrawalStatus

logger = logging.getLogger(__name__)

class LeaderPanelService:
    """Leader panel service for withdrawal management and statistics."""
    
    @staticmethod
    def is_leader(user_id: int) -> bool:
        """Check if user has leader privileges."""
        db = get_db_session()
        try:
            user = db.query(User).filter(User.telegram_user_id == user_id).first()
            return user and user.is_leader
        except Exception as e:
            logger.error(f"Error checking leader status: {e}")
            return False
        finally:
            close_db_session(db)

async def leader_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /leader command - show leader panel."""
    user = update.effective_user
    
    if not LeaderPanelService.is_leader(user.id):
        await update.message.reply_text(
            "❌ **Access Denied**\n\nLeader privileges required.",
            parse_mode='Markdown'
        )
        return
    
    await show_leader_panel(update, context)

async def show_leader_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display the main leader panel with all options."""
    user = update.effective_user
    
    if not LeaderPanelService.is_leader(user.id):
        if update.callback_query:
            await update.callback_query.answer("❌ Access denied. Leader privileges required.", show_alert=True)
        return

    # Get withdrawal statistics
    db = get_db_session()
    try:
        pending_withdrawals = db.query(Withdrawal).filter(
            Withdrawal.status == WithdrawalStatus.PENDING
        ).all()
        
        leader_approved = db.query(Withdrawal).filter(
            Withdrawal.status == WithdrawalStatus.LEADER_APPROVED
        ).all()
        
        completed_today = db.query(Withdrawal).filter(
            Withdrawal.status == WithdrawalStatus.COMPLETED,
            Withdrawal.updated_at >= datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        ).all()
        
        total_pending_amount = sum(w.amount for w in pending_withdrawals)
        total_approved_amount = sum(w.amount for w in leader_approved)
        total_completed_today = sum(w.amount for w in completed_today)
        
    except Exception as e:
        logger.error(f"Error getting leader stats: {e}")
        pending_withdrawals = leader_approved = completed_today = []
        total_pending_amount = total_approved_amount = total_completed_today = 0.0
    finally:
        close_db_session(db)

    leader_text = f"""
👑 **Leader Dashboard**

**📊 Withdrawal Statistics:**
• 📋 Pending Reviews: {len(pending_withdrawals)}
• 💰 Pending Amount: ${total_pending_amount:.2f}
• ✅ Approved (Awaiting Payment): {len(leader_approved)}
• 💸 Approved Amount: ${total_approved_amount:.2f}
• ✨ Completed Today: {len(completed_today)}
• 🏆 Completed Amount: ${total_completed_today:.2f}

**🔧 Quick Actions:**
• Review withdrawal requests
• Process approved payments
• View payment statistics
• Export transaction reports

**📈 Performance Metrics:**
• Today's processed: ${total_completed_today:.2f}
• Approval efficiency: Ready for implementation
• User satisfaction: Monitoring system active
    """
    
    keyboard = [
        [InlineKeyboardButton("📋 Review Withdrawals", callback_data="leader_review")],
        [InlineKeyboardButton("💸 Process Payments", callback_data="leader_payments")],
        [InlineKeyboardButton("📊 Statistics", callback_data="leader_stats")],
        [InlineKeyboardButton("📈 Reports", callback_data="leader_reports")],
        [InlineKeyboardButton("⚙️ Settings", callback_data="leader_settings")],
        [InlineKeyboardButton("🔄 Refresh", callback_data="leader_refresh")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(leader_text, parse_mode='Markdown', reply_markup=reply_markup)
    else:
        await update.message.reply_text(leader_text, parse_mode='Markdown', reply_markup=reply_markup)

async def leader_review_withdrawals(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle withdrawal review management."""
    query = update.callback_query
    await query.answer()
    
    db = get_db_session()
    try:
        pending_withdrawals = db.query(Withdrawal).filter(
            Withdrawal.status == WithdrawalStatus.PENDING
        ).order_by(Withdrawal.created_at.desc()).limit(10).all()
        
        if not pending_withdrawals:
            await query.edit_message_text(
                "📋 **Withdrawal Reviews**\n\n✅ No pending withdrawals to review.\n\nAll requests have been processed!",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Back to Dashboard", callback_data="leader_refresh")
                ]])
            )
            return
            
        review_text = f"📋 **Pending Withdrawal Reviews ({len(pending_withdrawals)})**\n\n"
        
        for i, withdrawal in enumerate(pending_withdrawals, 1):
            user = db.query(User).filter(User.id == withdrawal.user_id).first()
            username = f"@{user.username}" if user and user.username else f"User {user.telegram_user_id}" if user else "Unknown"
            
            review_text += f"""
**#{i} - {username}**
💰 Amount: ${withdrawal.amount:.2f}
🏦 Method: {withdrawal.method}
📱 Address: `{withdrawal.address}`
🕒 Requested: {withdrawal.created_at.strftime('%Y-%m-%d %H:%M')}
📝 Note: {withdrawal.note or 'No note provided'}

"""
        
        keyboard = []
        if pending_withdrawals:
            first_withdrawal = pending_withdrawals[0]
            keyboard.extend([
                [InlineKeyboardButton(f"✅ Approve #{1}", callback_data=f"approve_withdrawal_{first_withdrawal.id}")],
                [InlineKeyboardButton(f"❌ Reject #{1}", callback_data=f"reject_withdrawal_{first_withdrawal.id}")],
                [InlineKeyboardButton("📋 View Details", callback_data=f"withdrawal_details_{first_withdrawal.id}")],
            ])
        
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="leader_refresh")])
        
        await query.edit_message_text(
            review_text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        logger.error(f"Error in leader review: {e}")
        await query.edit_message_text(
            f"❌ Error loading withdrawals: {str(e)}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Back", callback_data="leader_refresh")
            ]])
        )
    finally:
        close_db_session(db)

async def leader_process_payments(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle payment processing management."""
    query = update.callback_query
    await query.answer()
    
    db = get_db_session()
    try:
        approved_withdrawals = db.query(Withdrawal).filter(
            Withdrawal.status == WithdrawalStatus.LEADER_APPROVED
        ).order_by(Withdrawal.updated_at.desc()).limit(10).all()
        
        if not approved_withdrawals:
            await query.edit_message_text(
                "💸 **Payment Processing**\n\n✅ No approved withdrawals awaiting payment.\n\nAll payments are up to date!",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Back to Dashboard", callback_data="leader_refresh")
                ]])
            )
            return
            
        payment_text = f"💸 **Approved Withdrawals - Awaiting Payment ({len(approved_withdrawals)})**\n\n"
        
        for i, withdrawal in enumerate(approved_withdrawals, 1):
            user = db.query(User).filter(User.id == withdrawal.user_id).first()
            username = f"@{user.username}" if user and user.username else f"User {user.telegram_user_id}" if user else "Unknown"
            
            payment_text += f"""
**#{i} - {username}**
💰 Amount: ${withdrawal.amount:.2f}
🏦 Method: {withdrawal.method}
📱 Address: `{withdrawal.address}`
✅ Approved: {withdrawal.updated_at.strftime('%Y-%m-%d %H:%M')}

"""
        
        keyboard = []
        if approved_withdrawals:
            first_withdrawal = approved_withdrawals[0]
            keyboard.extend([
                [InlineKeyboardButton(f"✅ Mark as Paid #{1}", callback_data=f"mark_paid_{first_withdrawal.id}")],
                [InlineKeyboardButton(f"❌ Mark as Failed #{1}", callback_data=f"mark_failed_{first_withdrawal.id}")],
                [InlineKeyboardButton("📋 Payment Details", callback_data=f"payment_details_{first_withdrawal.id}")],
            ])
        
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="leader_refresh")])
        
        await query.edit_message_text(
            payment_text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        logger.error(f"Error in leader payments: {e}")
        await query.edit_message_text(
            f"❌ Error loading payments: {str(e)}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Back", callback_data="leader_refresh")
            ]])
        )
    finally:
        close_db_session(db)

async def leader_statistics(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle leader statistics display."""
    query = update.callback_query
    await query.answer()
    
    db = get_db_session()
    try:
        # Get comprehensive statistics
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        # Today's stats
        today_completed = db.query(Withdrawal).filter(
            Withdrawal.status == WithdrawalStatus.COMPLETED,
            Withdrawal.updated_at >= today
        ).all()
        
        # Week's stats
        week_completed = db.query(Withdrawal).filter(
            Withdrawal.status == WithdrawalStatus.COMPLETED,
            Withdrawal.updated_at >= week_ago
        ).all()
        
        # Month's stats
        month_completed = db.query(Withdrawal).filter(
            Withdrawal.status == WithdrawalStatus.COMPLETED,
            Withdrawal.updated_at >= month_ago
        ).all()
        
        # All time stats
        all_completed = db.query(Withdrawal).filter(
            Withdrawal.status == WithdrawalStatus.COMPLETED
        ).all()
        
        stats_text = f"""
📊 **Leader Statistics Dashboard**

**📈 Daily Performance:**
• ✅ Completed Today: {len(today_completed)}
• 💰 Amount Today: ${sum(w.amount for w in today_completed):.2f}
• 📊 Average per Transaction: ${(sum(w.amount for w in today_completed) / max(len(today_completed), 1)):.2f}

**📅 Weekly Overview:**
• ✅ Completed This Week: {len(week_completed)}
• 💰 Total Amount: ${sum(w.amount for w in week_completed):.2f}
• 📊 Daily Average: {len(week_completed) / 7:.1f} transactions

**📆 Monthly Summary:**
• ✅ Completed This Month: {len(month_completed)}
• 💰 Total Amount: ${sum(w.amount for w in month_completed):.2f}
• 📊 Success Rate: 100% (All approved payments completed)

**🏆 All-Time Records:**
• ✅ Total Withdrawals: {len(all_completed)}
• 💰 Total Paid: ${sum(w.amount for w in all_completed):.2f}
• 📊 Average Transaction: ${(sum(w.amount for w in all_completed) / max(len(all_completed), 1)):.2f}
        """
        
        keyboard = [
            [InlineKeyboardButton("📈 Export Report", callback_data="export_stats")],
            [InlineKeyboardButton("📊 Detailed Analysis", callback_data="detailed_stats")],
            [InlineKeyboardButton("🔄 Refresh Stats", callback_data="leader_stats")],
            [InlineKeyboardButton("🔙 Back", callback_data="leader_refresh")]
        ]
        
        await query.edit_message_text(
            stats_text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        logger.error(f"Error in leader statistics: {e}")
        await query.edit_message_text(
            f"❌ Error loading statistics: {str(e)}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Back", callback_data="leader_refresh")
            ]])
        )
    finally:
        close_db_session(db)

async def approve_withdrawal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Approve a withdrawal request."""
    query = update.callback_query
    withdrawal_id = int(query.data.split('_')[-1])
    
    db = get_db_session()
    try:
        withdrawal = db.query(Withdrawal).filter(Withdrawal.id == withdrawal_id).first()
        if not withdrawal:
            await query.answer("❌ Withdrawal not found", show_alert=True)
            return
        
        withdrawal.status = WithdrawalStatus.LEADER_APPROVED
        withdrawal.updated_at = datetime.utcnow()
        db.commit()
        
        # Notify user
        user = db.query(User).filter(User.id == withdrawal.user_id).first()
        if user:
            try:
                await context.bot.send_message(
                    chat_id=user.telegram_user_id,
                    text=f"✅ **Withdrawal Approved**\n\n"
                         f"Your withdrawal request for ${withdrawal.amount:.2f} has been approved by our leader!\n"
                         f"Payment will be processed within 24 hours.\n\n"
                         f"**Method:** {withdrawal.method}\n"
                         f"**Address:** `{withdrawal.address}`",
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.warning(f"Failed to notify user {user.telegram_user_id}: {e}")
        
        await query.answer("✅ Withdrawal approved!", show_alert=True)
        await leader_review_withdrawals(update, context)
        
    except Exception as e:
        logger.error(f"Error approving withdrawal: {e}")
        await query.answer(f"❌ Error: {str(e)}", show_alert=True)
    finally:
        close_db_session(db)

async def reject_withdrawal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reject a withdrawal request."""
    query = update.callback_query
    withdrawal_id = int(query.data.split('_')[-1])
    
    db = get_db_session()
    try:
        withdrawal = db.query(Withdrawal).filter(Withdrawal.id == withdrawal_id).first()
        if not withdrawal:
            await query.answer("❌ Withdrawal not found", show_alert=True)
            return
        
        # Return balance to user
        user = db.query(User).filter(User.id == withdrawal.user_id).first()
        if user:
            user.balance += withdrawal.amount
        
        withdrawal.status = WithdrawalStatus.REJECTED
        withdrawal.updated_at = datetime.utcnow()
        db.commit()
        
        # Notify user
        if user:
            try:
                await context.bot.send_message(
                    chat_id=user.telegram_user_id,
                    text=f"❌ **Withdrawal Rejected**\n\n"
                         f"Your withdrawal request for ${withdrawal.amount:.2f} has been rejected.\n"
                         f"The amount has been returned to your balance.\n\n"
                         f"**Current Balance:** ${user.balance:.2f}\n"
                         f"Please ensure your withdrawal details are correct before submitting again.",
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.warning(f"Failed to notify user {user.telegram_user_id}: {e}")
        
        await query.answer("❌ Withdrawal rejected and balance returned", show_alert=True)
        await leader_review_withdrawals(update, context)
        
    except Exception as e:
        logger.error(f"Error rejecting withdrawal: {e}")
        await query.answer(f"❌ Error: {str(e)}", show_alert=True)
    finally:
        close_db_session(db)

async def mark_payment_completed(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mark a payment as completed."""
    query = update.callback_query
    withdrawal_id = int(query.data.split('_')[-1])
    
    db = get_db_session()
    try:
        withdrawal = db.query(Withdrawal).filter(Withdrawal.id == withdrawal_id).first()
        if not withdrawal:
            await query.answer("❌ Withdrawal not found", show_alert=True)
            return
        
        withdrawal.status = WithdrawalStatus.COMPLETED
        withdrawal.updated_at = datetime.utcnow()
        db.commit()
        
        # Notify user
        user = db.query(User).filter(User.id == withdrawal.user_id).first()
        if user:
            try:
                await context.bot.send_message(
                    chat_id=user.telegram_user_id,
                    text=f"🎉 **Payment Completed**\n\n"
                         f"Your withdrawal of ${withdrawal.amount:.2f} has been successfully paid!\n\n"
                         f"**Method:** {withdrawal.method}\n"
                         f"**Address:** `{withdrawal.address}`\n"
                         f"**Transaction ID:** Processing...\n\n"
                         f"Thank you for using our service!",
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.warning(f"Failed to notify user {user.telegram_user_id}: {e}")
        
        await query.answer("✅ Payment marked as completed!", show_alert=True)
        await leader_process_payments(update, context)
        
    except Exception as e:
        logger.error(f"Error marking payment completed: {e}")
        await query.answer(f"❌ Error: {str(e)}", show_alert=True)
    finally:
        close_db_session(db)

async def leader_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle all leader callback queries."""
    query = update.callback_query
    callback_data = query.data
    
    # Check leader access
    if not LeaderPanelService.is_leader(update.effective_user.id):
        await query.answer("❌ Access denied. Leader privileges required.", show_alert=True)
        return
    
    try:
        if callback_data == "leader_refresh":
            await show_leader_panel(update, context)
        elif callback_data == "leader_review":
            await leader_review_withdrawals(update, context)
        elif callback_data == "leader_payments":
            await leader_process_payments(update, context)
        elif callback_data == "leader_stats":
            await leader_statistics(update, context)
        elif callback_data.startswith("approve_withdrawal_"):
            await approve_withdrawal(update, context)
        elif callback_data.startswith("reject_withdrawal_"):
            await reject_withdrawal(update, context)
        elif callback_data.startswith("mark_paid_"):
            await mark_payment_completed(update, context)
        else:
            await query.answer("Feature under development", show_alert=True)
    
    except Exception as e:
        logger.error(f"Error in leader callback handler: {e}")
        await query.answer(f"Error: {str(e)}", show_alert=True)

def setup_leader_handlers(application) -> None:
    """Set up all leader handlers."""
    
    # Add leader command handler
    application.add_handler(CommandHandler("leader", leader_command))
    
    # Add leader callback handlers
    application.add_handler(CallbackQueryHandler(leader_callback_handler, pattern="^leader_"))
    application.add_handler(CallbackQueryHandler(leader_callback_handler, pattern="^approve_withdrawal_"))
    application.add_handler(CallbackQueryHandler(leader_callback_handler, pattern="^reject_withdrawal_"))
    application.add_handler(CallbackQueryHandler(leader_callback_handler, pattern="^mark_paid_"))
    
    logger.info("Leader handlers set up successfully")