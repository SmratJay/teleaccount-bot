"""
Keyboard layout helper for Telegram bot.
Provides main menu keyboard in the correct 2x2 grid format.
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from utils.runtime_settings import get_support_settings


def get_main_menu_keyboard(*, is_admin: bool = False) -> InlineKeyboardMarkup:
    """Build the main menu keyboard with optional admin controls."""
    keyboard = [
        [InlineKeyboardButton("🚀 LFG (Buy Account)", callback_data="start_real_selling")],
        [
            InlineKeyboardButton("💰 Balance", callback_data="check_balance"),
            InlineKeyboardButton("📤 Withdraw", callback_data="withdraw_menu")
        ],
        [
            InlineKeyboardButton("🌐 Language", callback_data="language_menu"),
            InlineKeyboardButton("📊 Status", callback_data="status")
        ]
    ]

    if is_admin:
        keyboard.append([InlineKeyboardButton("🔧 Admin Panel", callback_data="admin_panel")])

    support = get_support_settings()
    support_label = support.get("main_button_label") or "💬 Support"
    support_url = support.get("main_button_url")
    if support_url:
        keyboard.append([InlineKeyboardButton(support_label, url=support_url)])

    return InlineKeyboardMarkup(keyboard)
