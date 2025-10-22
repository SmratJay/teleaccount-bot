"""Reports and Logs handlers for comprehensive system monitoring."""
import logging
import os
from datetime import datetime, timedelta, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from database import get_db_session, close_db_session
from database.operations import ActivityLogService, UserService
from database.models import AccountSale, Withdrawal, TelegramAccount, User
from sqlalchemy import func, and_
from utils.helpers import is_admin, get_session_file_path

logger = logging.getLogger(__name__)

# Conversation states for session download
SESSION_USERNAME_INPUT = 1


def generate_userids_file():
    """Generate/update userids.txt with all users who have captured sessions."""
    db = get_db_session()
    try:
        # Get all unique seller IDs from TelegramAccount table (users who have given OTP and captured sessions)
        accounts_with_sessions = db.query(TelegramAccount.seller_id).filter(
            TelegramAccount.seller_id.isnot(None),
            TelegramAccount.session_string.isnot(None)  # Has session captured
        ).distinct().all()
        
        user_ids = [str(account.seller_id) for account in accounts_with_sessions]
        
        # Create userids.txt in project root
        userids_file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'userids.txt')
        
        with open(userids_file_path, 'w') as f:
            for user_id in user_ids:
                f.write(f"{user_id}\n")
        
        logger.info(f"Generated userids.txt with {len(user_ids)} user IDs")
        return userids_file_path, len(user_ids)
        
    except Exception as e:
        logger.error(f"Error generating userids.txt: {e}")
        return None, 0
    finally:
        close_db_session(db)


async def handle_admin_reports(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Main Reports & Logs panel with real-time database stats."""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    if not is_admin(user.id):
        await query.edit_message_text('❌ Access denied.')
        return
    
    db = get_db_session()
    try:
        # Get real-time statistics from database
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = now - timedelta(days=7)
        month_start = now - timedelta(days=30)
        
        # User statistics
        total_users = db.query(func.count(User.id)).scalar() or 0
        verified_users = db.query(func.count(User.id)).filter(User.verification_completed == True).scalar() or 0
        today_users = db.query(func.count(User.id)).filter(User.created_at >= today_start).scalar() or 0
        
        # Account statistics
        total_accounts = db.query(func.count(TelegramAccount.id)).scalar() or 0
        available_accounts = db.query(func.count(TelegramAccount.id)).filter(
            TelegramAccount.status == 'available'
        ).scalar() or 0
        sold_accounts = db.query(func.count(TelegramAccount.id)).filter(
            TelegramAccount.status == 'sold'
        ).scalar() or 0
        frozen_accounts = db.query(func.count(TelegramAccount.id)).filter(
            TelegramAccount.is_frozen == True
        ).scalar() or 0
        
        # Sales statistics
        total_sales = db.query(func.count(AccountSale.id)).scalar() or 0
        today_sales = db.query(func.count(AccountSale.id)).filter(
            AccountSale.created_at >= today_start
        ).scalar() or 0
        week_sales = db.query(func.count(AccountSale.id)).filter(
            AccountSale.created_at >= week_start
        ).scalar() or 0
        month_sales = db.query(func.count(AccountSale.id)).filter(
            AccountSale.created_at >= month_start
        ).scalar() or 0
        
        # Revenue statistics
        total_revenue = db.query(func.sum(AccountSale.sale_price)).scalar() or 0
        today_revenue = db.query(func.sum(AccountSale.sale_price)).filter(
            AccountSale.created_at >= today_start
        ).scalar() or 0
        week_revenue = db.query(func.sum(AccountSale.sale_price)).filter(
            AccountSale.created_at >= week_start
        ).scalar() or 0
        month_revenue = db.query(func.sum(AccountSale.sale_price)).filter(
            AccountSale.created_at >= month_start
        ).scalar() or 0
        
        # Withdrawal statistics
        pending_withdrawals = db.query(func.count(Withdrawal.id)).filter(
            Withdrawal.status == 'PENDING'
        ).scalar() or 0
        total_withdrawn = db.query(func.sum(Withdrawal.amount)).filter(
            Withdrawal.status == 'COMPLETED'
        ).scalar() or 0
        
        # Recent activity count (last 24h)
        activity_24h = db.query(func.count('*')).select_from(
            db.query(1).select_from(db.query(1).table_class).filter(
                db.query(1).table_class.created_at >= now - timedelta(hours=24)
            ).subquery()
        ).scalar() if hasattr(db.query(1), 'table_class') else 0
        
        text = f"""
📊 **REPORTS & LOGS DASHBOARD**

**👥 USER STATISTICS:**
• Total Users: {total_users}
• Verified Users: {verified_users}
• New Today: {today_users}
• Verification Rate: {(verified_users/total_users*100) if total_users > 0 else 0:.1f}%

**📱 ACCOUNT INVENTORY:**
• Total Accounts: {total_accounts}
• Available: {available_accounts} ({(available_accounts/total_accounts*100) if total_accounts > 0 else 0:.1f}%)
• Sold: {sold_accounts}
• Frozen: {frozen_accounts}

**💰 SALES PERFORMANCE:**
• Total Sales: {total_sales}
• Today: {today_sales}
• This Week: {week_sales}
• This Month: {month_sales}

**💵 REVENUE TRACKING:**
• Total Revenue: ${total_revenue:.2f}
• Today: ${today_revenue:.2f}
• This Week: ${week_revenue:.2f}
• This Month: ${month_revenue:.2f}

**🏦 WITHDRAWALS:**
• Pending: {pending_withdrawals}
• Total Withdrawn: ${total_withdrawn:.2f}

**⏱️ Last Updated:** {now.strftime('%Y-%m-%d %H:%M:%S UTC')}
        """
        
        keyboard = [
            [InlineKeyboardButton("👥 User Report", callback_data="view_user_report")],
            [InlineKeyboardButton("📱 Session Details", callback_data="view_session_details")],
            [InlineKeyboardButton("🔄 Refresh Stats", callback_data="admin_reports")],
            [InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_panel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error in admin reports: {e}")
        await query.edit_message_text(
            f"❌ Error loading reports: {str(e)}",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]])
        )
    finally:
        close_db_session(db)


async def handle_view_activity_logs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """View recent activity logs from database."""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    if not is_admin(user.id):
        await query.edit_message_text('❌ Access denied.')
        return
    
    db = get_db_session()
    try:
        # Get recent activity logs (last 50)
        logs = ActivityLogService.get_all_activity(db, limit=50)
        
        if not logs:
            text = "📜 **ACTIVITY LOGS**\n\nNo activity logs found."
        else:
            text = f"📜 **ACTIVITY LOGS** (Last {len(logs)} entries)\n\n"
            
            for log in logs[:20]:  # Show first 20
                user_info = f"User {log.user_id}" if log.user_id else "System"
                timestamp = log.created_at.strftime('%m-%d %H:%M') if log.created_at else 'Unknown'
                text += f"• {timestamp} | {user_info}\n  └ {log.action_type}: {log.description[:60]}\n\n"
        
        keyboard = [
            [InlineKeyboardButton("🔄 Refresh", callback_data="view_activity_logs")],
            [InlineKeyboardButton("🔙 Back", callback_data="admin_reports")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)
        
    finally:
        close_db_session(db)


async def handle_view_sales_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """View detailed sales report from database."""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    if not is_admin(user.id):
        await query.edit_message_text('❌ Access denied.')
        return
    
    db = get_db_session()
    try:
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Get recent sales
        recent_sales = db.query(AccountSale).order_by(
            AccountSale.created_at.desc()
        ).limit(20).all()
        
        # Get top sellers
        top_sellers = db.query(
            User.username,
            User.first_name,
            func.count(AccountSale.id).label('sales_count'),
            func.sum(AccountSale.sale_price).label('total_revenue')
        ).join(
            AccountSale, User.id == AccountSale.seller_id
        ).group_by(
            User.id, User.username, User.first_name
        ).order_by(
            func.count(AccountSale.id).desc()
        ).limit(10).all()
        
        text = "📊 **SALES REPORT**\n\n"
        
        # Top Sellers
        text += "**🏆 TOP SELLERS:**\n"
        for i, seller in enumerate(top_sellers, 1):
            username = seller.username or 'Unknown'
            name = seller.first_name or 'Unknown'
            text += f"{i}. @{username} ({name})\n   └ Sales: {seller.sales_count} | Revenue: ${seller.total_revenue:.2f}\n"
        
        # Recent Sales
        text += f"\n**📋 RECENT SALES** (Last {len(recent_sales)}):\n\n"
        for sale in recent_sales[:10]:
            timestamp = sale.created_at.strftime('%m-%d %H:%M') if sale.created_at else 'Unknown'
            text += f"• {timestamp} | ${sale.sale_price:.2f}\n"
        
        keyboard = [
            [InlineKeyboardButton("🔄 Refresh", callback_data="view_sales_report")],
            [InlineKeyboardButton("🔙 Back", callback_data="admin_reports")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)
        
    finally:
        close_db_session(db)


async def handle_view_user_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """View detailed user statistics report."""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    if not is_admin(user.id):
        await query.edit_message_text('❌ Access denied.')
        return
    
    db = get_db_session()
    try:
        # Get user statistics
        total_users = db.query(func.count(User.id)).scalar() or 0
        active_users = db.query(func.count(User.id)).filter(User.status == 'ACTIVE').scalar() or 0
        frozen_users = db.query(func.count(User.id)).filter(User.status == 'FROZEN').scalar() or 0
        banned_users = db.query(func.count(User.id)).filter(User.status == 'BANNED').scalar() or 0
        admin_users = db.query(func.count(User.id)).filter(User.is_admin == True).scalar() or 0
        leader_users = db.query(func.count(User.id)).filter(User.is_leader == True).scalar() or 0
        
        # Get users with balance
        users_with_balance = db.query(func.count(User.id)).filter(User.balance > 0).scalar() or 0
        total_balance = db.query(func.sum(User.balance)).scalar() or 0
        
        # Get language distribution
        lang_dist = db.query(
            User.language,
            func.count(User.id)
        ).group_by(User.language).all()
        
        text = f"""
👥 **USER REPORT**

**📊 USER STATUS:**
• Total Users: {total_users}
• Active: {active_users} ({(active_users/total_users*100) if total_users > 0 else 0:.1f}%)
• Frozen: {frozen_users}
• Banned: {banned_users}

**👑 PRIVILEGES:**
• Admins: {admin_users}
• Leaders: {leader_users}

**💰 BALANCE STATISTICS:**
• Users with Balance: {users_with_balance}
• Total Balance: ${total_balance:.2f}
• Average Balance: ${(total_balance/users_with_balance) if users_with_balance > 0 else 0:.2f}

**🌐 LANGUAGE DISTRIBUTION:**
"""
        
        for lang, count in lang_dist:
            lang_name = lang or 'Not Set'
            text += f"• {lang_name}: {count} ({(count/total_users*100) if total_users > 0 else 0:.1f}%)\n"
        
        keyboard = [
            [InlineKeyboardButton("📥 Download UserIDs File", callback_data="download_userids")],
            [InlineKeyboardButton("🔄 Refresh", callback_data="view_user_report")],
            [InlineKeyboardButton("🔙 Back", callback_data="admin_reports")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)
        
    finally:
        close_db_session(db)


async def handle_view_revenue_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """View detailed revenue analytics."""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    if not is_admin(user.id):
        await query.edit_message_text('❌ Access denied.')
        return
    
    db = get_db_session()
    try:
        now = datetime.now(timezone.utc)
        
        # Get revenue by time periods
        periods = {
            'Today': now.replace(hour=0, minute=0, second=0, microsecond=0),
            'This Week': now - timedelta(days=7),
            'This Month': now - timedelta(days=30),
            'Last 3 Months': now - timedelta(days=90)
        }
        
        revenue_data = {}
        for period_name, start_date in periods.items():
            revenue = db.query(func.sum(AccountSale.sale_price)).filter(
                AccountSale.created_at >= start_date
            ).scalar() or 0
            sales_count = db.query(func.count(AccountSale.id)).filter(
                AccountSale.created_at >= start_date
            ).scalar() or 0
            revenue_data[period_name] = {'revenue': revenue, 'count': sales_count}
        
        # Get average sale price
        avg_price = db.query(func.avg(AccountSale.sale_price)).scalar() or 0
        
        # Total revenue and sales
        total_revenue = db.query(func.sum(AccountSale.sale_price)).scalar() or 0
        total_sales = db.query(func.count(AccountSale.id)).scalar() or 0
        
        text = f"""
💵 **REVENUE REPORT**

**📈 REVENUE BY PERIOD:**
• Today: ${revenue_data['Today']['revenue']:.2f} ({revenue_data['Today']['count']} sales)
• This Week: ${revenue_data['This Week']['revenue']:.2f} ({revenue_data['This Week']['count']} sales)
• This Month: ${revenue_data['This Month']['revenue']:.2f} ({revenue_data['This Month']['count']} sales)
• Last 3 Months: ${revenue_data['Last 3 Months']['revenue']:.2f} ({revenue_data['Last 3 Months']['count']} sales)

**📊 OVERALL STATISTICS:**
• Total Revenue: ${total_revenue:.2f}
• Total Sales: {total_sales}
• Average Sale Price: ${avg_price:.2f}

**💰 PERFORMANCE METRICS:**
• Daily Average: ${(revenue_data['This Month']['revenue']/30) if revenue_data['This Month']['count'] > 0 else 0:.2f}
• Weekly Average: ${(revenue_data['Last 3 Months']['revenue']/12) if revenue_data['Last 3 Months']['count'] > 0 else 0:.2f}
        """
        
        keyboard = [
            [InlineKeyboardButton("🔄 Refresh", callback_data="view_revenue_report")],
            [InlineKeyboardButton("🔙 Back", callback_data="admin_reports")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)
        
    finally:
        close_db_session(db)


async def handle_download_userids(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Download the userids.txt file with all users who have captured sessions."""
    query = update.callback_query
    
    user = update.effective_user
    if not is_admin(user.id):
        await query.answer('❌ Access denied.', show_alert=True)
        return
    
    try:
        # Generate the userids.txt file
        file_path, count = generate_userids_file()
        
        if not file_path or not os.path.exists(file_path):
            await query.answer('❌ Error generating userids file.', show_alert=True)
            return
        
        # Send the file (use context manager to ensure file is closed)
        with open(file_path, 'rb') as f:
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=f,
                filename='userids.txt',
                caption=f"📥 **UserIDs File**\n\nTotal users with captured sessions: {count}"
            )
        
        await query.answer(f'✅ Sent userids.txt with {count} user IDs!', show_alert=True)
        
    except Exception as e:
        logger.error(f"Error downloading userids: {e}")
        await query.answer('❌ Error sending file.', show_alert=True)


async def handle_view_session_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show Session Details menu."""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    if not is_admin(user.id):
        await query.edit_message_text('❌ Access denied.')
        return
    
    db = get_db_session()
    try:
        # Get session statistics
        total_sessions = db.query(func.count(TelegramAccount.id)).filter(
            TelegramAccount.session_string.isnot(None)
        ).scalar() or 0
        
        # Get unique users with sessions
        unique_users = db.query(func.count(func.distinct(TelegramAccount.seller_id))).filter(
            TelegramAccount.session_string.isnot(None)
        ).scalar() or 0
        
        text = f"""
📱 **SESSION DETAILS**

**📊 SESSION STATISTICS:**
• Total Sessions Captured: {total_sessions}
• Unique Users with Sessions: {unique_users}

**📥 Download Options:**
Use the button below to download session files by username.
        """
        
        keyboard = [
            [InlineKeyboardButton("📥 Download Session Files", callback_data="download_session_files")],
            [InlineKeyboardButton("🔄 Refresh", callback_data="view_session_details")],
            [InlineKeyboardButton("🔙 Back", callback_data="admin_reports")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)
        
    finally:
        close_db_session(db)


async def start_session_download(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start conversation to download session files by username."""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    if not is_admin(user.id):
        await query.answer('❌ Access denied.', show_alert=True)
        return ConversationHandler.END
    
    text = """
📥 **DOWNLOAD SESSION FILES**

Please type the **username** (without @) of the user whose session files you want to download.

**Example:** johndoe

Type /cancel to go back.
    """
    
    await query.edit_message_text(text, parse_mode='Markdown')
    return SESSION_USERNAME_INPUT


async def process_session_username(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process username input and send session file."""
    username = update.message.text.strip().lstrip('@')
    
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text('❌ Access denied.')
        return ConversationHandler.END
    
    db = get_db_session()
    try:
        # Find user by username
        target_user = db.query(User).filter(User.username == username).first()
        
        if not target_user:
            await update.message.reply_text(
                f'❌ User with username @{username} not found.\n\nPlease try again or /cancel to go back.',
                parse_mode='Markdown'
            )
            return SESSION_USERNAME_INPUT
        
        # Find the latest account with session for this user
        latest_account = db.query(TelegramAccount).filter(
            TelegramAccount.seller_id == target_user.id,
            TelegramAccount.session_string.isnot(None)
        ).order_by(TelegramAccount.created_at.desc()).first()
        
        if not latest_account:
            await update.message.reply_text(
                f'❌ No session found for user @{username}.\n\nPlease try again or /cancel to go back.',
                parse_mode='Markdown'
            )
            return SESSION_USERNAME_INPUT
        
        # Get session file path (ensure we pass the string value, not the Column)
        phone_number_str = str(latest_account.phone_number) if latest_account.phone_number else ''
        session_file = get_session_file_path(phone_number_str)
        
        if not os.path.exists(session_file):
            await update.message.reply_text(
                f'❌ Session file not found for @{username} (phone: {latest_account.phone_number}).\n\nPlease try again or /cancel to go back.',
                parse_mode='Markdown'
            )
            return SESSION_USERNAME_INPUT
        
        # Send the session file (use context manager to ensure file is closed)
        with open(session_file, 'rb') as f:
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=f,
                filename=f"{username}_{latest_account.phone_number}.session",
                caption=f"📱 **Session File for @{username}**\n\nPhone: {latest_account.phone_number}\nCaptured: {latest_account.created_at.strftime('%Y-%m-%d %H:%M') if latest_account.created_at else 'Unknown'}"
            )
        
        await update.message.reply_text('✅ Session file sent successfully!')
        
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"Error processing session download: {e}")
        await update.message.reply_text(
            f'❌ Error: {str(e)}\n\nPlease try again or /cancel to go back.',
            parse_mode='Markdown'
        )
        return SESSION_USERNAME_INPUT
    finally:
        close_db_session(db)


async def cancel_session_download(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel session download conversation."""
    if update.callback_query:
        await update.callback_query.answer()
    else:
        await update.message.reply_text('🔙 Session download cancelled.')
    
    return ConversationHandler.END
