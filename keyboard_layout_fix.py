"""
Keyboard layou            InlineKeyboardButton("💸 Withdraw", callback_data="withdraw_menu"), fix for Telegram Bot - provides consistent menu layouts
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def get_main_menu_keyboard(user_id: int = None):
    """Returns the main menu keyboard layout with exact user specification."""
    keyboard = [
        # First row - LFG (Full width button)
        [InlineKeyboardButton("🚀 LFG (Let's F***ing Go)", callback_data="start_real_selling")],
        
        # 3x2 Grid starts here
        # Row 1 of grid - Account Details and Balance
        [
            InlineKeyboardButton("📋 Account Details", callback_data="account_details"),
            InlineKeyboardButton("💰 Balance", callback_data="check_balance")
        ],
        # Row 2 of grid - Withdraw and Language  
        [
            InlineKeyboardButton("� Withdraw", callback_data="withdraw_menu"),
            InlineKeyboardButton("🌍 Language", callback_data="language_menu")
        ],
        # Row 3 of grid - System Capacity and Status
        [
            InlineKeyboardButton("📊 System Capacity", callback_data="system_capacity"),
            InlineKeyboardButton("📊 Status", callback_data="status")
        ],
        
    ]
    
    # Add admin/leader buttons if user has privileges
    if user_id and (is_admin(user_id) or is_leader(user_id)):
        admin_row = []
        if is_admin(user_id):
            admin_row.append(InlineKeyboardButton("⚙️ Admin Panel", callback_data="admin_panel"))
        if is_leader(user_id):
            admin_row.append(InlineKeyboardButton("👑 Leader Panel", callback_data="leader_refresh"))
        keyboard.append(admin_row)
        
        # Add analytics button for privileged users
        keyboard.append([InlineKeyboardButton("📊 Analytics", callback_data="analytics_refresh")])
    
    # Last row - Support (Full width button)
    keyboard.append([InlineKeyboardButton("🆘 Support", url="https://t.me/BujhlamNaKiHolo")])
    
    return InlineKeyboardMarkup(keyboard)

def is_admin(user_id: int) -> bool:
    """Check if user has admin privileges."""
    ADMIN_IDS = [6733908384]  # Your actual admin ID
    return user_id in ADMIN_IDS

def is_leader(user_id: int) -> bool:
    """Check if user has leader privileges."""
    try:
        from database import get_db_session, close_db_session
        from database.models import User
        
        db = get_db_session()
        try:
            user = db.query(User).filter(User.telegram_user_id == user_id).first()
            return user and user.is_leader
        finally:
            close_db_session(db)
    except Exception:
        return False