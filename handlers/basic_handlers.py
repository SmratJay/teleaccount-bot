"""
Basic bot handlers (start, help, etc.).
"""
import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from database import get_db_session, close_db_session
from database.operations import UserService

logger = logging.getLogger(__name__)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    user = update.effective_user
    
    # Create or get user
    db = get_db_session()
    try:
        db_user = UserService.get_or_create_user(
            db=db,
            telegram_user_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            language_code=user.language_code or 'en'
        )
        
        welcome_text = f"""
🤖 **Welcome to Telegram Account Bot!**

Hello {user.first_name or 'User'}! 👋

This bot helps you manage Telegram accounts securely with advanced features:

🔐 **Secure Account Management**
• Automated login with unique proxy assignment
• 2FA setup and security hardening
• Session management and protection

💰 **Financial Features**
• Balance tracking and management
• Secure withdrawal system
• Multiple currency support

✨ **Available Commands:**
• ✅ `/lfg` - Add new Telegram account
• 💰 `/balance` - Check your balance
• 💸 `/withdraw` - Request withdrawal
• 📱 `/accounts` - View your accounts
• ❓ `/help` - Get help and support

Ready to get started? Click the button below or use `/lfg` to add your first account! 🚀
        """
        
        keyboard = [
            [InlineKeyboardButton("✅ Let's Get Started (LFG)", callback_data="start_lfg")],
            [InlineKeyboardButton("💰 Check Balance", callback_data="check_balance")],
            [InlineKeyboardButton("📱 My Accounts", callback_data="my_accounts")],
            [InlineKeyboardButton("❓ Help & Support", callback_data="help_support")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            welcome_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
        logger.info(f"Start command handled for user {user.id}")
        
    except Exception as e:
        logger.error(f"Error in start command: {e}")
        await update.message.reply_text(
            "❌ An error occurred. Please try again later."
        )
    finally:
        close_db_session(db)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    help_text = """
❓ **Help & Support**

**Available Commands:**

🆕 **Account Management:**
• `/lfg` - Add new Telegram account
• `/accounts` - View your managed accounts

💰 **Financial:**
• `/balance` - Check your current balance
• `/withdraw` - Request withdrawal

ℹ️ **Information:**
• `/help` - Show this help message
• `/support` - Contact support

🔧 **How it works:**

1️⃣ **Add Account**: Use `/lfg` to start adding a new Telegram account
2️⃣ **Verification**: Complete captcha and phone verification
3️⃣ **Login**: Enter the code sent to your phone
4️⃣ **Security**: Automatic 2FA setup and security hardening
5️⃣ **Earnings**: Your account starts earning automatically

🛡️ **Security Features:**
• Unique proxy for each account
• Automatic 2FA protection
• Session isolation
• OTP monitoring

💸 **Withdrawals:**
• Supported currencies: USDT-BEP20, TRX
• Minimum amounts apply
• Manual review for security

📞 **Support:**
Need help? Contact our support team using `/support` or join our support channel.

**System Status:** 🟢 Online
    """
    
    keyboard = [
        [InlineKeyboardButton("✅ Add Account", callback_data="start_lfg")],
        [InlineKeyboardButton("💰 Check Balance", callback_data="check_balance")],
        [InlineKeyboardButton("📞 Contact Support", callback_data="contact_support")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        help_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def support_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /support command."""
    support_text = """
📞 **Support & Contact**

Need help? We're here for you! 🤝

**Support Channels:**
• 💬 Support Chat: @your_support_chat
• 📧 Email: support@yourbot.com
• 📱 Telegram: @your_support_bot

**Common Issues:**

🔐 **Login Problems:**
• Check your phone number format
• Ensure SMS/call reception
• Verify internet connection

💰 **Balance Questions:**
• Earnings update every 24 hours
• Check account status in /accounts
• Withdrawals processed manually

📱 **Account Issues:**
• Each phone number can only be used once
• Accounts are automatically protected
• Status changes are logged

**Response Times:**
• General inquiries: 2-24 hours
• Technical issues: 1-6 hours
• Urgent matters: Within 1 hour

**System Information:**
• Bot Version: 1.0.0
• Last Update: Today
• Status: 🟢 All systems operational

Click below to get instant help! 👇
    """
    
    keyboard = [
        [InlineKeyboardButton("💬 Live Support Chat", url="https://t.me/your_support_chat")],
        [InlineKeyboardButton("🤖 Support Bot", url="https://t.me/your_support_bot")],
        [InlineKeyboardButton("📋 FAQ", callback_data="show_faq")],
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        support_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle button callbacks."""
    query = update.callback_query
    await query.answer()
    
    if query.data == "start_lfg":
        # Import here to avoid circular imports
        from .lfg_handlers import start_lfg_flow
        await start_lfg_flow(update, context)
        
    elif query.data == "check_balance":
        from .user_handlers import balance_command
        # Create a mock update for the balance command
        await balance_command(update, context)
        
    elif query.data == "my_accounts":
        from .user_handlers import accounts_command
        await accounts_command(update, context)
        
    elif query.data == "help_support":
        await help_command(update, context)
        
    elif query.data == "contact_support":
        await support_command(update, context)
        
    elif query.data == "show_faq":
        faq_text = """
🙋 **Frequently Asked Questions**

**Q: How does the bot work?**
A: The bot helps you manage Telegram accounts securely with automatic earnings and withdrawal features.

**Q: Is it safe?**
A: Yes! We use advanced security measures including unique proxies, 2FA, and session isolation.

**Q: How much can I earn?**
A: Earnings depend on account activity and current market conditions. Check your balance regularly.

**Q: How do withdrawals work?**
A: Request withdrawals through /withdraw. All requests are manually reviewed for security.

**Q: Can I use multiple phone numbers?**
A: Yes, but each number can only be used once per account.

**Q: What if my account gets banned?**
A: We monitor account health and provide protection, but Telegram's terms still apply.
        """
        
        await query.edit_message_text(
            faq_text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Back to Support", callback_data="contact_support")
            ]])
        )
        
    elif query.data == "back_to_menu":
        await start_command(update, context)

def setup_basic_handlers(application) -> None:
    """Set up basic command handlers."""
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("support", support_command))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    logger.info("Basic handlers set up successfully")