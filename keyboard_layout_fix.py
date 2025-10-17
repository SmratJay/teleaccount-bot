"""
Keyboard layout fix for Telegram Bot - provides consistent menu layouts
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def get_main_menu_keyboard():
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
        
        # Last row - Support (Full width button)
        [InlineKeyboardButton("🆘 Support", url="https://t.me/BujhlamNaKiHolo")]
    ]
    
    return InlineKeyboardMarkup(keyboard)