"""System Settings handlers for bot configuration and maintenance."""
import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import get_db_session, close_db_session
from database.operations import SystemSettingsService, ActivityLogService
from utils.helpers import is_admin

logger = logging.getLogger(__name__)


async def handle_admin_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Main System Settings panel."""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    if not is_admin(user.id):
        await query.edit_message_text('❌ Access denied.')
        return
    
    db = get_db_session()
    try:
        # Get current settings from database
        settings = SystemSettingsService.get_all_settings(db)
        
        # Get system info
        from database.models import User, TelegramAccount, ActivityLog
        total_users = db.query(User).count()
        total_accounts = db.query(TelegramAccount).count()
        total_logs = db.query(ActivityLog).count()
        
        text = f"""
⚙️ **SYSTEM SETTINGS & CONFIGURATION**

**📊 SYSTEM STATUS:**
• Total Users: {total_users}
• Total Accounts: {total_accounts}
• Activity Logs: {total_logs}

**🔧 CURRENT CONFIGURATION:**
• Verification Required: {settings.get('verification_required', 'true')}
• Default Freeze Duration: {settings.get('default_freeze_hours', '24')}h
• Min Withdrawal Amount: ${settings.get('min_withdrawal', '10.00')}
• Commission Rate: {settings.get('commission_rate', '10')}%
• Max Daily Sales/User: {settings.get('max_daily_sales', '10')}

**⚡ QUICK ACTIONS:**
Configure bot behavior, manage system maintenance, and control security settings.
        """
        
        keyboard = [
            [InlineKeyboardButton("🔧 Bot Configuration", callback_data="settings_bot_config")],
            [InlineKeyboardButton("💰 Financial Settings", callback_data="settings_financial")],
            [InlineKeyboardButton("🔐 Security & Access", callback_data="settings_security")],
            [InlineKeyboardButton("🧹 System Maintenance", callback_data="settings_maintenance")],
            [InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_panel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)
        
    finally:
        close_db_session(db)


async def handle_settings_bot_config(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Bot configuration settings."""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    if not is_admin(user.id):
        await query.edit_message_text('❌ Access denied.')
        return
    
    db = get_db_session()
    try:
        settings = SystemSettingsService.get_all_settings(db)
        
        verification_required = settings.get('verification_required', 'true') == 'true'
        captcha_enabled = settings.get('captcha_enabled', 'true') == 'true'
        channel_verification = settings.get('channel_verification_required', 'true') == 'true'
        default_freeze_hours = settings.get('default_freeze_hours', '24')
        max_daily_sales = settings.get('max_daily_sales', '10')
        
        text = f"""
🔧 **BOT CONFIGURATION**

**📋 VERIFICATION SETTINGS:**
• Verification Required: {'✅ Enabled' if verification_required else '❌ Disabled'}
• CAPTCHA Enabled: {'✅ Enabled' if captcha_enabled else '❌ Disabled'}
• Channel Join Required: {'✅ Enabled' if channel_verification else '❌ Disabled'}

**⚙️ OPERATIONAL SETTINGS:**
• Default Freeze Duration: {default_freeze_hours} hours
• Max Daily Sales/User: {max_daily_sales}

**ℹ️ CONFIGURATION INFO:**
These settings control core bot behavior. Changes take effect immediately.
        """
        
        keyboard = [
            [InlineKeyboardButton(
                f"{'❌ Disable' if verification_required else '✅ Enable'} Verification",
                callback_data="toggle_verification"
            )],
            [InlineKeyboardButton(
                f"{'❌ Disable' if captcha_enabled else '✅ Enable'} CAPTCHA",
                callback_data="toggle_captcha"
            )],
            [InlineKeyboardButton(
                f"{'❌ Disable' if channel_verification else '✅ Enable'} Channel Join",
                callback_data="toggle_channel_verification"
            )],
            [InlineKeyboardButton("⏱️ Set Freeze Duration", callback_data="set_freeze_duration")],
            [InlineKeyboardButton("📊 Set Daily Limit", callback_data="set_daily_limit")],
            [InlineKeyboardButton("🔙 Back", callback_data="admin_settings")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)
        
    finally:
        close_db_session(db)


async def handle_settings_financial(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Financial settings panel."""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    if not is_admin(user.id):
        await query.edit_message_text('❌ Access denied.')
        return
    
    db = get_db_session()
    try:
        settings = SystemSettingsService.get_all_settings(db)
        
        min_withdrawal = settings.get('min_withdrawal', '10.00')
        commission_rate = settings.get('commission_rate', '10')
        min_account_price = settings.get('min_account_price', '1.00')
        max_account_price = settings.get('max_account_price', '1000.00')
        
        text = f"""
💰 **FINANCIAL SETTINGS**

**🏦 WITHDRAWAL CONFIGURATION:**
• Minimum Withdrawal: ${min_withdrawal}
• Current Commission Rate: {commission_rate}%

**💵 ACCOUNT PRICING:**
• Minimum Price: ${min_account_price}
• Maximum Price: ${max_account_price}

**📊 FINANCIAL CONTROLS:**
Configure pricing limits, commission rates, and withdrawal thresholds.
        """
        
        keyboard = [
            [InlineKeyboardButton("💵 Set Min Withdrawal", callback_data="set_min_withdrawal")],
            [InlineKeyboardButton("📈 Set Commission Rate", callback_data="set_commission")],
            [InlineKeyboardButton("💲 Set Price Limits", callback_data="set_price_limits")],
            [InlineKeyboardButton("🔙 Back", callback_data="admin_settings")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)
        
    finally:
        close_db_session(db)


async def handle_settings_security(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Security and access control settings."""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    if not is_admin(user.id):
        await query.edit_message_text('❌ Access denied.')
        return
    
    db = get_db_session()
    try:
        # Get admin/leader count
        from database.models import User
        admin_count = db.query(User).filter(User.is_admin == True).count()
        leader_count = db.query(User).filter(User.is_leader == True).count()
        
        # Get environment variables for current access control
        admin_ids = os.getenv('ADMIN_USER_ID', 'Not set')
        leader_channel = os.getenv('LEADER_CHANNEL_ID', 'Not set')
        
        settings = SystemSettingsService.get_all_settings(db)
        max_login_attempts = settings.get('max_login_attempts', '3')
        session_timeout = settings.get('session_timeout_minutes', '60')
        
        text = f"""
🔐 **SECURITY & ACCESS CONTROL**

**👑 PRIVILEGED USERS:**
• Active Admins: {admin_count}
• Active Leaders: {leader_count}

**🔧 ENVIRONMENT CONFIGURATION:**
• Admin User IDs: {admin_ids}
• Leader Channel ID: {leader_channel}

**⚙️ SECURITY SETTINGS:**
• Max Login Attempts: {max_login_attempts}
• Session Timeout: {session_timeout} minutes

**ℹ️ NOTE:**
Admin and Leader access is controlled via environment variables (ADMIN_USER_ID, LEADER_CHANNEL_ID) and can be managed in the Manual User Edit panel.
        """
        
        keyboard = [
            [InlineKeyboardButton("👥 View All Admins", callback_data="view_all_admins")],
            [InlineKeyboardButton("👥 View All Leaders", callback_data="view_all_leaders")],
            [InlineKeyboardButton("🔒 Set Login Attempts", callback_data="set_login_attempts")],
            [InlineKeyboardButton("⏱️ Set Session Timeout", callback_data="set_session_timeout")],
            [InlineKeyboardButton("🔙 Back", callback_data="admin_settings")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)
        
    finally:
        close_db_session(db)


async def handle_settings_maintenance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """System maintenance panel."""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    if not is_admin(user.id):
        await query.edit_message_text('❌ Access denied.')
        return
    
    db = get_db_session()
    try:
        # Get system statistics
        from database.models import User, TelegramAccount, ActivityLog, AccountSale, Withdrawal
        
        total_logs = db.query(ActivityLog).count()
        total_inactive_accounts = db.query(TelegramAccount).filter(
            TelegramAccount.status == 'inactive'
        ).count()
        completed_sales = db.query(AccountSale).count()
        completed_withdrawals = db.query(Withdrawal).filter(
            Withdrawal.status == 'COMPLETED'
        ).count()
        
        text = f"""
🧹 **SYSTEM MAINTENANCE**

**📊 DATABASE STATISTICS:**
• Activity Logs: {total_logs} entries
• Inactive Accounts: {total_inactive_accounts}
• Completed Sales: {completed_sales}
• Completed Withdrawals: {completed_withdrawals}

**🔧 MAINTENANCE ACTIONS:**
Perform system cleanup, optimize database, and manage old records.

**⚠️ WARNING:**
Some maintenance actions are irreversible. Use with caution.
        """
        
        keyboard = [
            [InlineKeyboardButton("🗑️ Clear Old Activity Logs", callback_data="clear_old_logs")],
            [InlineKeyboardButton("🧹 Clean Inactive Accounts", callback_data="clean_inactive_accounts")],
            [InlineKeyboardButton("📊 Database Statistics", callback_data="view_db_stats")],
            [InlineKeyboardButton("🔄 Optimize Database", callback_data="optimize_database")],
            [InlineKeyboardButton("🔙 Back", callback_data="admin_settings")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)
        
    finally:
        close_db_session(db)


async def handle_toggle_verification(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Toggle verification requirement."""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    if not is_admin(user.id):
        return
    
    db = get_db_session()
    try:
        current = SystemSettingsService.get_setting(db, 'verification_required', 'true')
        new_value = 'false' if current == 'true' else 'true'
        SystemSettingsService.set_setting(db, 'verification_required', new_value)
        
        await query.answer(f"✅ Verification {'disabled' if new_value == 'false' else 'enabled'}!", show_alert=True)
        await handle_settings_bot_config(update, context)
        
    finally:
        close_db_session(db)


async def handle_toggle_captcha(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Toggle CAPTCHA requirement."""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    if not is_admin(user.id):
        return
    
    db = get_db_session()
    try:
        current = SystemSettingsService.get_setting(db, 'captcha_enabled', 'true')
        new_value = 'false' if current == 'true' else 'true'
        SystemSettingsService.set_setting(db, 'captcha_enabled', new_value)
        
        await query.answer(f"✅ CAPTCHA {'disabled' if new_value == 'false' else 'enabled'}!", show_alert=True)
        await handle_settings_bot_config(update, context)
        
    finally:
        close_db_session(db)


async def handle_toggle_channel_verification(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Toggle channel verification requirement."""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    if not is_admin(user.id):
        return
    
    db = get_db_session()
    try:
        current = SystemSettingsService.get_setting(db, 'channel_verification_required', 'true')
        new_value = 'false' if current == 'true' else 'true'
        SystemSettingsService.set_setting(db, 'channel_verification_required', new_value)
        
        await query.answer(f"✅ Channel verification {'disabled' if new_value == 'false' else 'enabled'}!", show_alert=True)
        await handle_settings_bot_config(update, context)
        
    finally:
        close_db_session(db)


async def handle_clear_old_logs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Clear activity logs older than 90 days."""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    if not is_admin(user.id):
        return
    
    db = get_db_session()
    try:
        from datetime import datetime, timedelta, timezone
        from database.models import ActivityLog
        
        # Delete logs older than 90 days
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=90)
        deleted = db.query(ActivityLog).filter(ActivityLog.created_at < cutoff_date).delete()
        db.commit()
        
        await query.answer(f"✅ Deleted {deleted} old activity logs!", show_alert=True)
        await handle_settings_maintenance(update, context)
        
    except Exception as e:
        logger.error(f"Error clearing logs: {e}")
        await query.answer(f"❌ Error: {str(e)}", show_alert=True)
    finally:
        close_db_session(db)


async def handle_view_db_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """View detailed database statistics."""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    if not is_admin(user.id):
        return
    
    db = get_db_session()
    try:
        from database.models import User, TelegramAccount, ActivityLog, AccountSale, Withdrawal, ProxyPool
        
        stats = {
            'Users': db.query(User).count(),
            'Telegram Accounts': db.query(TelegramAccount).count(),
            'Activity Logs': db.query(ActivityLog).count(),
            'Account Sales': db.query(AccountSale).count(),
            'Withdrawals': db.query(Withdrawal).count(),
            'Proxies': db.query(ProxyPool).count()
        }
        
        text = "📊 **DATABASE STATISTICS**\n\n"
        for table, count in stats.items():
            text += f"• {table}: {count:,} records\n"
        
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="settings_maintenance")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)
        
    finally:
        close_db_session(db)
