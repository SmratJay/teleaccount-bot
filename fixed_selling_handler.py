async def start_real_selling_fixed(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start real selling process - prompt for phone number input."""
    
    # Mark this as a selling conversation
    context.user_data['conversation_type'] = 'selling'
    
    sell_text = """
🚀 **Real Telegram Account Selling**

**💰 Sell Your Telegram Account - 100% Real Process!**

⚠️ **This is REAL - not a simulation!**

**What we do:**
• Send **real OTP** to your phone via Telegram
• **Actually login** to your account  
• **Really modify** account settings
• **Actually transfer** ownership
• **Real payment** processing

**Ready to sell your account?**

**Please type your phone number with country code:**
**Format:** +1234567890
**Example:** +919876543210
    """
    
    # No buttons - just prompt for phone number input (this is the selling process)
    keyboard = [
        [InlineKeyboardButton("🏠 Back to Menu", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(sell_text, parse_mode='Markdown', reply_markup=reply_markup)
    return PHONE