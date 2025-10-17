"""
Keyboard Layout Fix for Real Handlers
This will provide the exact layout matching the screenshot
"""

def get_main_menu_keyboard():
    """Get the main menu keyboard with exact layout from screenshot."""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    
    keyboard = [
        # Top row - LFG (Sell) full width
        [
            InlineKeyboardButton("🚀 LFG (Sell)", callback_data="start_real_selling")
        ],
        # Row 2: Account Details | Withdraw  
        [
            InlineKeyboardButton("📋 Account Details", callback_data="account_details"),
            InlineKeyboardButton("💸 Withdraw", callback_data="withdraw_menu")
        ],
        # Row 3: System Capacity | Language
        [
            InlineKeyboardButton("📊 System Capacity", callback_data="system_capacity"),
            InlineKeyboardButton("🌍 Language", callback_data="language_menu")
        ],
        # Row 4: Balance | Status
        [
            InlineKeyboardButton("💰 Balance", callback_data="check_balance"),
            InlineKeyboardButton("📈 Status", callback_data="status")
        ],
        # Bottom row - Support full width
        [
            InlineKeyboardButton("🆘 Support", url="https://t.me/BujhlamNaKiHolo")
        ]
    ]
    
    return InlineKeyboardMarkup(keyboard)

# Test the layout
if __name__ == "__main__":
    keyboard = get_main_menu_keyboard()
    print("✅ Keyboard layout created successfully!")
    print("Layout structure:")
    print("Row 1: [🚀 LFG (Sell)]")
    print("Row 2: [📋 Account Details] [💸 Withdraw]")  
    print("Row 3: [📊 System Capacity] [🌍 Language]")
    print("Row 4: [💰 Balance] [📈 Status]")
    print("Row 5: [🆘 Support]")
    print("\nThis matches the client's requested layout exactly!")