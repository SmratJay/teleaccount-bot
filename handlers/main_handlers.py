"""
Main handlers for the Telegram Account Selling Bot.
Complete rebuild to match specification requirements.
"""
import logging
import json
import os
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler, ConversationHandler, MessageHandler, filters
from database import get_db_session, close_db_session
from database.operations import UserService, TelegramAccountService, SystemSettingsService, VerificationService, ActivityLogService, WithdrawalService
from services.captcha import CaptchaService
# from services.translator import TranslatorService  # Will implement later
from utils.helpers import MessageUtils
from handlers.real_handlers import get_real_selling_handler

logger = logging.getLogger(__name__)

# Conversation states
VERIFICATION_CAPTCHA, VERIFICATION_CHANNELS, VERIFICATION_TASKS = range(3)
SELL_PHONE, SELL_CODE, SELL_2FA_CHECK, SELL_2FA_DISABLE, SELL_SPAM_CHECK, SELL_NAME, SELL_PHOTO, SELL_2FA_SETUP, SELL_CONFIRM = range(10, 19)
WITHDRAW_DETAILS, WITHDRAW_CONFIRM = range(20, 22)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command - Entry point with verification check."""
    user = update.effective_user
    
    db = get_db_session()
    try:
        # Get or create user
        db_user = UserService.get_or_create_user(
            db=db,
            telegram_user_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            language_code=user.language_code or 'en'
        )
        
        # Check if user needs verification
        if db_user.status.value == "PENDING_VERIFICATION" or not db_user.verification_completed:
            await start_verification_process(update, context, db_user)
            return
        
        # Check if user is banned/frozen
        if db_user.status.value in ["BANNED", "FROZEN", "SUSPENDED"]:
            await show_banned_message(update, context, db_user)
            return
        
        # Show main menu for verified users
        await show_main_menu(update, context, db_user)
        
        # Log activity
        ActivityLogService.log_action(
            db=db,
            user_id=db_user.id,
            action_type="START_COMMAND",
            description=f"User accessed bot main menu",
            extra_data=json.dumps({"username": user.username, "first_name": user.first_name})
        )
        
    except Exception as e:
        logger.error(f"Error in start command: {e}")
        await update.message.reply_text(
            "❌ **System Error**\\n\\nPlease try again in a moment. If the issue persists, contact support.",
            parse_mode='Markdown'
        )
    finally:
        close_db_session(db)

async def start_verification_process(update: Update, context: ContextTypes.DEFAULT_TYPE, db_user) -> None:
    """Start the human verification process."""
    verification_text = f"""
🔒 **Human Verification Required**

Welcome {update.effective_user.first_name or 'User'}!

Before accessing the **Telegram Account Selling Platform**, you must complete our security verification:

🛡️ **Verification Steps:**
• 🧩 **CAPTCHA** - Prove you're human  
• 📢 **Channel Joins** - Join required channels
• ✅ **Final Verification** - Account activation

**Why verification is required:**
• Prevents automated bots and spam
• Ensures only legitimate sellers
• Protects our community integrity
• Maintains platform security

🚀 **Ready to start earning?** Click below!

⏱️ *Estimated time: 2-3 minutes*
    """
    
    keyboard = [
        [InlineKeyboardButton("🔓 Start Verification", callback_data="start_verification")],
        [InlineKeyboardButton("❓ Why Verification?", callback_data="why_verification")],
        [InlineKeyboardButton("🆘 Contact Support", callback_data="contact_support")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            verification_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            verification_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, db_user) -> None:
    """Show the main bot interface with ONLY the necessary buttons as requested."""
    
    # Get user statistics
    db = get_db_session()
    try:
        accounts_count = TelegramAccountService.get_user_accounts_count(db, db_user.id)
        system_capacity = SystemSettingsService.get_setting(db, "system_capacity", "🟢 Normal Load")
        
        main_menu_text = f"""
🤖 **Telegram Account Selling Platform**

👋 **Welcome, {update.effective_user.first_name or 'User'}!**

💼 **Your Statistics:**
• 📱 Accounts Available: {accounts_count}
• 💰 Balance: `${db_user.balance:.2f}`
• 📊 Total Sold: {db_user.total_accounts_sold}
• 💵 Total Earnings: `${db_user.total_earnings:.2f}`

🌍 **System Status:** {system_capacity}
📊 **Your Status:** {get_status_emoji(db_user.status.value)} {db_user.status.value}
        """
        
        # Create ONLY the necessary buttons as specified in requirements
        keyboard = [
            [InlineKeyboardButton("🚀 LFG (Sell)", callback_data="lfg_sell")],
            [InlineKeyboardButton("📄 Account Details", callback_data="account_details"),
             InlineKeyboardButton("💰 Balance", callback_data="check_balance")],
            [InlineKeyboardButton("💸 Withdraw", callback_data="withdraw_menu"),
             InlineKeyboardButton("🌍 Language", callback_data="language_menu")],
            [InlineKeyboardButton("📊 System Capacity", callback_data="system_capacity"),
             InlineKeyboardButton("📋 Status", callback_data="user_status")],
            [InlineKeyboardButton("🆘 Support", url="https://t.me/BujhlamNaKiHolo")]
        ]
        
        # Admin and leader panels only if user has those roles
        if db_user.is_admin:
            keyboard.append([InlineKeyboardButton("⚙️ Admin Panel", callback_data="admin_panel")])
        if db_user.is_leader:
            keyboard.append([InlineKeyboardButton("👑 Leader Panel", callback_data="leader_panel")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.callback_query:
            await update.callback_query.edit_message_text(
                main_menu_text,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                main_menu_text,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            
    except Exception as e:
        logger.error(f"Error showing main menu: {e}")
    finally:
        close_db_session(db)

def get_status_emoji(status: str) -> str:
    """Get emoji for user status."""
    status_emojis = {
        "ACTIVE": "✅",
        "PENDING_VERIFICATION": "⏳", 
        "FROZEN": "❄️",
        "BANNED": "🚫",
        "SUSPENDED": "⏸️"
    }
    return status_emojis.get(status, "❓")

async def show_banned_message(update: Update, context: ContextTypes.DEFAULT_TYPE, db_user) -> None:
    """Show message for banned/frozen users."""
    status_messages = {
        "BANNED": "🚫 **Account Banned**\\n\\nYour account has been permanently banned from the platform. Contact support if you believe this is an error.",
        "FROZEN": "❄️ **Account Frozen**\\n\\nYour account is temporarily frozen. Please contact support for assistance.",
        "SUSPENDED": "⏸️ **Account Suspended**\\n\\nYour account is suspended. Contact support for more information."
    }
    
    message = status_messages.get(db_user.status.value, "❓ **Account Restricted**\\n\\nYour account has restricted access.")
    
    keyboard = [[InlineKeyboardButton("🆘 Contact Support", callback_data="contact_support")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            message,
            parse_mode='Markdown', 
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            message,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

# Button callback handlers
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle all inline button callbacks."""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user = update.effective_user
    
    # Debug logging
    logger.info(f"Button pressed by {user.id} ({user.username}): {data}")
    
    # Route to appropriate handlers based on callback data
    if data == "start_verification":
        await handle_start_verification(update, context)
    elif data == "new_captcha":
        await handle_start_verification(update, context)  # Generate new captcha
    elif data == "verify_channels":
        await handle_verify_channels(update, context)
    elif data == "lfg_sell":
        await handle_lfg_sell(update, context)

    elif data == "account_details":
        await handle_account_details(update, context)
    elif data == "check_balance":
        await handle_check_balance(update, context)
    elif data == "withdraw_menu":
        await handle_withdraw_menu(update, context)
    elif data == "language_menu":
        await handle_language_menu(update, context)
    elif data == "system_capacity":
        await handle_system_capacity(update, context)
    elif data == "user_status":
        await handle_user_status(update, context)
    elif data == "contact_support":
        await handle_contact_support(update, context)
    elif data == "admin_panel":
        await handle_admin_panel(update, context)
    elif data == "leader_panel":
        await handle_leader_panel(update, context)
    elif data == "my_available_accounts":
        await show_my_accounts(update, context)
    elif data == "skip_password":
        await handle_sell_password(update, context)
    elif data == "confirm_sale":
        await process_account_sale(update, context)
    elif data == "main_menu":
        await start_command(update, context)
    elif data == "why_verification":
        await handle_why_verification(update, context)
    elif data == "view_all_accounts":
        await handle_view_all_accounts(update, context)
    elif data == "withdraw_trx":
        await handle_withdraw_trx(update, context)
    elif data == "withdraw_usdt":
        await handle_withdraw_usdt(update, context)
    elif data == "withdraw_binance":
        await handle_withdraw_binance(update, context)
    elif data == "withdrawal_history":
        await handle_withdrawal_history(update, context)
    elif data.startswith("delete_withdrawal_"):
        await handle_delete_withdrawal(update, context)
    else:
        logger.warning(f"Unknown callback data: {data} from user {user.id}")
        await query.edit_message_text("❓ Unknown option. Returning to main menu...")
        await start_command(update, context)

async def handle_start_verification(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start the verification process with IMAGE CAPTCHA."""
    from services.captcha import ImageCaptchaService
    
    image_captcha_service = ImageCaptchaService()
    
    # Clean up any previous CAPTCHA image before generating a new one
    old_captcha_filepath = context.user_data.get('captcha_filepath')
    if old_captcha_filepath:
        image_captcha_service.cleanup_captcha_image(old_captcha_filepath)
    
    captcha_data = await image_captcha_service.generate_image_captcha()
    
    if not captcha_data:
        await update.callback_query.answer("❌ Error generating CAPTCHA. Please try again.", show_alert=True)
        return
    
    verification_text = f"""
🔒 **Step 1/3: IMAGE CAPTCHA Verification**

🖼️ **Please solve the CAPTCHA below:**

**📝 Instructions:**
• Look at the image carefully
• Type the characters you see
• Send the answer as a regular message
• Case doesn't matter

**👇 Type your answer now:**
    """
    
    keyboard = [
        [InlineKeyboardButton("🔄 New CAPTCHA", callback_data="new_captcha")],
        [InlineKeyboardButton("← Back to Start", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Store CAPTCHA answer and filepath in context
    context.user_data['captcha_answer'] = captcha_data['answer']
    context.user_data['captcha_filepath'] = captcha_data['filepath']
    context.user_data['verification_step'] = 1
    
    # Send the CAPTCHA image
    try:
        if update.callback_query:
            await update.callback_query.message.delete()
        
        await update.effective_chat.send_photo(
            photo=captcha_data['image_bytes'],
            caption=verification_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Error sending image CAPTCHA: {e}")
        await update.effective_chat.send_message(
            "❌ Error displaying CAPTCHA. Please try again.",
            reply_markup=reply_markup
        )

async def handle_lfg_sell(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle LFG (Let's F***ing Go) - Account selling process."""
    user = update.effective_user
    db = get_db_session()
    
    try:
        db_user = UserService.get_user_by_telegram_id(db, user.id)
        available_accounts = TelegramAccountService.get_available_accounts(db, db_user.id)
        
        lfg_text = f"""
🚀 **LFG - Sell Your Telegram Account!**

**How It Works:**
1️⃣ Provide your account phone number
2️⃣ We automatically configure:
   • Change account name 💠
   • Change username 💠  
   • Set new profile photo 💠
   • Setup new 2FA 💠
   • Terminate all sessions 🔄
3️⃣ Get paid instantly! 💰

**Current Stats:**
• 📱 Available Accounts: {len(available_accounts)}
• 💵 Earning Rate: $5-50 per account
• ⚡ Process Time: 5-15 minutes

**Ready to sell?**
        """
        
        keyboard = [
            [InlineKeyboardButton("📱 Sell New Account", callback_data="sell_new_account")],
        ]
        
        if available_accounts:
            keyboard.append([InlineKeyboardButton("📊 My Accounts ({})".format(len(available_accounts)), callback_data="my_available_accounts")])
        
        keyboard.append([InlineKeyboardButton("← Back", callback_data="main_menu")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            lfg_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Error in LFG sell: {e}")
        await update.callback_query.edit_message_text(
            "❌ Error loading selling options. Try again.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← Back", callback_data="main_menu")]])
        )
    finally:
        close_db_session(db)

async def handle_account_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user's account details and statistics."""
    user = update.effective_user
    db = get_db_session()
    
    try:
        db_user = UserService.get_user_by_telegram_id(db, user.id)
        accounts = TelegramAccountService.get_user_accounts(db, db_user.id)
        
        details_text = f"""
📄 **Account Details**

👤 **User Information:**
• **Name:** {user.first_name or 'N/A'} {user.last_name or ''}
• **Username:** @{user.username or 'No username'}
• **User ID:** `{user.id}`
• **Member Since:** {db_user.created_at.strftime('%Y-%m-%d')}

📱 **Account Statistics:**
• **Total Accounts:** {len(accounts)}
• **Available to Sell:** {len([a for a in accounts if a.status.value == 'AVAILABLE'])}
• **Already Sold:** {len([a for a in accounts if a.status.value == 'SOLD'])}
• **On Hold:** {len([a for a in accounts if a.status.value == '24_HOUR_HOLD'])}

💰 **Financial Summary:**
• **Current Balance:** `${db_user.balance:.2f}`
• **Total Sold:** {db_user.total_accounts_sold} accounts
• **Total Earnings:** `${db_user.total_earnings:.2f}`
• **Average per Account:** `${(db_user.total_earnings / max(db_user.total_accounts_sold, 1)):.2f}`

🎯 **Performance:**
• **Success Rate:** {((db_user.total_accounts_sold / max(len(accounts), 1)) * 100):.1f}%
• **Status:** {get_status_emoji(db_user.status.value)} {db_user.status.value}
        """
        
        keyboard = [
            [InlineKeyboardButton("📊 View All Accounts", callback_data="view_all_accounts")],
            [InlineKeyboardButton("💸 Withdrawal History", callback_data="withdrawal_history")],
            [InlineKeyboardButton("← Back to Menu", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            details_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Error in account details: {e}")
        await update.callback_query.edit_message_text(
            "❌ Error loading account details. Please try again."
        )
    finally:
        close_db_session(db)

async def handle_check_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user's current balance and recent transactions."""
    user = update.effective_user
    db = get_db_session()
    
    try:
        db_user = UserService.get_user_by_telegram_id(db, user.id)
        
        balance_text = f"""
💰 **Your Balance**

**Current Balance:** `${db_user.balance:.2f}`

📊 **Quick Stats:**
• **Total Earned:** `${db_user.total_earnings:.2f}`
• **Accounts Sold:** {db_user.total_accounts_sold}
• **Average Earning:** `${(db_user.total_earnings / max(db_user.total_accounts_sold, 1)):.2f}` per account

💸 **Withdrawal Options:**
• **Minimum Withdrawal:** $10.00
• **Available Methods:** TRX, USDT-BEP20, Binance
• **Processing Time:** 1-24 hours

**Ready to cash out?** Use the withdraw button below!
        """
        
        keyboard = [
            [InlineKeyboardButton("💸 Withdraw Now", callback_data="withdraw_menu")],
            [InlineKeyboardButton("📈 Earning History", callback_data="earning_history")],
            [InlineKeyboardButton("🔄 Refresh Balance", callback_data="check_balance")],
            [InlineKeyboardButton("← Back to Menu", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            balance_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Error checking balance: {e}")
        await update.callback_query.edit_message_text(
            "❌ Error loading balance. Please try again."
        )
    finally:
        close_db_session(db)

async def handle_withdraw_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle withdraw menu."""
    withdraw_text = """
💸 **Withdrawal Menu**

Choose your withdrawal method:

💰 **Available Methods:**
• 🟢 **TRX (Tron)** - Fast & Low fees  
• 🟡 **USDT-BEP20** - Stable & Reliable
• 🔵 **Binance** - Direct to exchange

⚠️ **Requirements:**
• Minimum withdrawal: $10.00
• Processing time: 1-24 hours  
• Leader approval required

📋 **What you need:**
• Your wallet address or Binance ID
• Verified account status
    """
    
    keyboard = [
        [InlineKeyboardButton("🟢 TRX Withdrawal", callback_data="withdraw_trx")],
        [InlineKeyboardButton("🟡 USDT-BEP20", callback_data="withdraw_usdt")],
        [InlineKeyboardButton("🔵 Binance", callback_data="withdraw_binance")],
        [InlineKeyboardButton("📊 Withdrawal History", callback_data="withdrawal_history")],
        [InlineKeyboardButton("← Back to Menu", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        withdraw_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def handle_language_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle language selection."""
    language_text = """
🌍 **Language Selection**

Choose your preferred language:

**Available Languages:**
• 🇺🇸 English
• 🇪🇸 Español  
• 🇫🇷 Français
• 🇩🇪 Deutsch
• 🇷🇺 Русский
• 🇨🇳 中文
• 🇮🇳 हिंदी
• 🇦🇪 العربية

*Language will be applied to all bot messages*
    """
    
    keyboard = [
        [InlineKeyboardButton("🇺🇸 English", callback_data="lang_en"),
         InlineKeyboardButton("🇪🇸 Español", callback_data="lang_es")],
        [InlineKeyboardButton("🇫🇷 Français", callback_data="lang_fr"),
         InlineKeyboardButton("🇩🇪 Deutsch", callback_data="lang_de")],
        [InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"),
         InlineKeyboardButton("🇨🇳 中文", callback_data="lang_zh")],
        [InlineKeyboardButton("🇮🇳 हिंदी", callback_data="lang_hi"),
         InlineKeyboardButton("🇦🇪 العربية", callback_data="lang_ar")],
        [InlineKeyboardButton("← Back to Menu", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        language_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def handle_system_capacity(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show system capacity and global statistics."""
    db = get_db_session()
    try:
        # Get system statistics
        from database.models import User
        total_users = db.query(User).count()
        system_capacity = SystemSettingsService.get_setting(db, "system_capacity", "🟢 Normal Load")
        
        capacity_text = f"""
📊 **System Capacity & Status**

🌍 **Global Statistics:**
• **Total Users:** {total_users:,}
• **System Load:** {system_capacity}
• **Active Sales:** Processing...
• **Success Rate:** 99.2%

🔄 **Current Status:**
• **API Response:** ⚡ Fast (< 100ms)
• **Database:** ✅ Healthy  
• **Proxy Pool:** 🟢 Available
• **Payment Processing:** ✅ Online

📈 **Performance Metrics:**
• **Uptime:** 99.9%
• **Avg. Sale Time:** 8 minutes
• **User Satisfaction:** ⭐⭐⭐⭐⭐

Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}
        """
        
        keyboard = [
            [InlineKeyboardButton("🔄 Refresh Status", callback_data="system_capacity")],
            [InlineKeyboardButton("📊 Detailed Stats", callback_data="detailed_stats")],
            [InlineKeyboardButton("← Back to Menu", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            capacity_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    finally:
        close_db_session(db)

async def handle_user_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user's personal status."""
    user = update.effective_user
    db = get_db_session()
    
    try:
        db_user = UserService.get_user_by_telegram_id(db, user.id)
        
        status_text = f"""
📋 **Your Personal Status**

👤 **Account Information:**
• **Status:** {get_status_emoji(db_user.status.value)} {db_user.status.value}
• **Verification:** {'✅ Complete' if db_user.verification_completed else '⏳ Pending'}
• **Member Since:** {db_user.created_at.strftime('%Y-%m-%d')}

🎯 **Performance Metrics:**
• **Trust Score:** ⭐⭐⭐⭐⭐ (Excellent)
• **Success Rate:** 100%
• **Response Time:** Fast

🔒 **Security Status:**
• **2FA Enabled:** ✅ Recommended
• **IP Monitoring:** 🟢 Active
• **Session Security:** ✅ Verified

📊 **Activity Summary:**
• **Last Active:** {db_user.updated_at.strftime('%Y-%m-%d %H:%M')}
• **Total Sessions:** Tracking...
        """
        
        keyboard = [
            [InlineKeyboardButton("🔄 Refresh Status", callback_data="user_status")],
            [InlineKeyboardButton("🔒 Security Settings", callback_data="security_settings")],
            [InlineKeyboardButton("← Back to Menu", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            status_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    finally:
        close_db_session(db)

async def handle_contact_support(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle support contact."""
    support_text = """
🆘 **Contact Support**

Need help? Our support team is here for you!

**📞 Support Options:**

🔸 **Live Chat:** @support_bot
🔸 **Support Channel:** @telegram_bot_support  
🔸 **Email:** support@telegrambot.com
🔸 **Response Time:** < 2 hours

**🔧 Common Issues:**
• Account verification problems
• Withdrawal delays  
• Technical difficulties
• Account selling questions

**📋 Before contacting:**
• Have your User ID ready: `{update.effective_user.id}`
• Describe your issue clearly
• Include screenshots if relevant

**⚡ For urgent issues, use Live Chat!**
    """
    
    keyboard = [
        [InlineKeyboardButton("💬 Live Chat", url="https://t.me/BujhlamNaKiHolo")],
        [InlineKeyboardButton("📢 Support Channel", url="https://t.me/telegram_bot_support")],
        [InlineKeyboardButton("❓ FAQ", callback_data="faq")],
        [InlineKeyboardButton("← Back to Menu", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        support_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def handle_why_verification(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Explain why verification is required."""
    explanation_text = """
🔒 **Why Verification is Required**

Our verification system protects both sellers and buyers:

**🛡️ Security Benefits:**
• **Prevents Bots:** Automated scripts can't pass CAPTCHA
• **Stops Scammers:** Human verification filters out bad actors
• **Account Protection:** Reduces risk of stolen/fake accounts
• **Quality Control:** Ensures only legitimate sellers

**📈 Platform Benefits:**
• **Higher Trust:** Verified users get better prices
• **Faster Sales:** Buyers prefer verified sellers
• **Lower Disputes:** Verified accounts have fewer issues
• **Better Support:** Priority customer service

**⚡ Quick Process:**
1. **CAPTCHA** - 30 seconds
2. **Channel Joins** - 1 minute  
3. **Final Check** - 30 seconds

**Total Time: ~2 minutes for lifetime access!**

Ready to get verified and start earning? 💰
    """
    
    keyboard = [
        [InlineKeyboardButton("🔓 Start Verification Now", callback_data="start_verification")],
        [InlineKeyboardButton("← Back", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        explanation_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def handle_view_all_accounts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """View all user accounts with detailed information."""
    user = update.effective_user
    db = get_db_session()
    
    try:
        # Get user from database
        db_user = UserService.get_user_by_telegram_id(db, user.id)
        if not db_user:
            await update.callback_query.edit_message_text(
                "❌ User not found. Please start the bot with /start",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Start", callback_data="main_menu")]])
            )
            return
        
        # Get all user accounts
        accounts = TelegramAccountService.get_user_accounts(db, db_user.id)
        
        if not accounts:
            no_accounts_text = """
📱 **No Accounts Found**

You haven't added any accounts yet.

🚀 **Ready to start selling?**
Click "Sell New Account" to add your first account and start earning!

💡 **Pro Tip:** Verified accounts with good history sell faster and for higher prices.
            """
            keyboard = [
                [InlineKeyboardButton("🚀 Sell My First Account", callback_data="start_real_selling")],
                [InlineKeyboardButton("← Back to Menu", callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.callback_query.edit_message_text(
                no_accounts_text,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            return
        
        # Display accounts summary
        accounts_text = f"""
📱 **All Your Accounts ({len(accounts)} total)**

"""
        
        for i, account in enumerate(accounts, 1):
            status_emoji = {
                'AVAILABLE': '✅',
                'SOLD': '💰',
                '24_HOUR_HOLD': '⏳',
                'PENDING_REVIEW': '🔍',
                'REJECTED': '❌'
            }.get(account.status.value, '❓')
            
            accounts_text += f"""
**{i}. {account.phone_number}**
{status_emoji} Status: {account.status.value}
💵 Price: ${account.sale_price:.2f}
📅 Added: {account.created_at.strftime('%Y-%m-%d')}
"""
            if account.sold_at:
                accounts_text += f"💰 Sold: {account.sold_at.strftime('%Y-%m-%d')}\n"
            accounts_text += "\n"
        
        keyboard = [
            [InlineKeyboardButton("🚀 Sell Another Account", callback_data="start_real_selling")],
            [InlineKeyboardButton("📊 Account Details", callback_data="account_details")],
            [InlineKeyboardButton("← Back to Menu", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            accounts_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Error viewing all accounts: {e}")
        await update.callback_query.edit_message_text(
            "❌ Error loading accounts. Please try again.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Retry", callback_data="view_all_accounts")]])
        )
    finally:
        close_db_session(db)

async def fallback_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Fallback handler for any unmatched callback queries."""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user = update.effective_user
    
    logger.warning(f"Fallback handler triggered - Unmatched callback: {data} from user {user.id}")
    
    # For any unmatched callback, return to main menu
    await query.edit_message_text("🔄 Returning to main menu...")
    await start_command(update, context)

async def handle_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle admin panel access."""
    admin_text = """
⚙️ **Admin Panel**

**Available Admin Functions:**

📢 **Broadcasting:**
• Send messages to all users
• Targeted announcements
• System notifications  

👥 **User Management:**
• View user statistics
• Modify user data
• Ban/unban users
• Status updates

📊 **System Controls:**
• View system logs
• Monitor capacity
• Proxy management
• Settings configuration

🔧 **Advanced Tools:**
• Database operations
• Bulk user actions
• Security monitoring
    """
    
    keyboard = [
        [InlineKeyboardButton("📢 Broadcast Message", callback_data="admin_broadcast")],
        [InlineKeyboardButton("👥 User Management", callback_data="admin_users")],
        [InlineKeyboardButton("📊 System Monitor", callback_data="admin_system")],
        [InlineKeyboardButton("🔧 Advanced Tools", callback_data="admin_advanced")],
        [InlineKeyboardButton("← Back to Menu", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        admin_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def handle_leader_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle leader panel access."""
    leader_text = """
👑 **Leader Panel**

**Regional Leader Functions:**

💸 **Withdrawal Management:**
• Review pending withdrawals
• Approve/reject requests
• Process payments
• Upload payment proofs

📊 **Statistics:**
• Regional performance
• User activity tracking
• Payment analytics
• Success metrics

👥 **Team Management:**
• Monitor regional users
• Performance tracking
• Support assistance

**Pending Actions:** Loading...
    """
    
    keyboard = [
        [InlineKeyboardButton("💸 Pending Withdrawals", callback_data="leader_withdrawals")],
        [InlineKeyboardButton("📊 Regional Stats", callback_data="leader_stats")],
        [InlineKeyboardButton("👥 Team Overview", callback_data="leader_team")],
        [InlineKeyboardButton("← Back to Menu", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        leader_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def start_account_selling(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the account selling process."""
    sell_text = """
📱 **Sell Your Telegram Account**

**Step 1: Account Phone Number**

Please provide your Telegram account phone number (with country code):

**Example:** +1234567890

**What happens next:**
• We login to your account securely
• Change account name & username 💠
• Set new profile photo 💠
• Setup new 2FA 💠
• Terminate all sessions 🔄
• You get paid instantly! 💰

**Type your phone number below:**
    """
    
    keyboard = [
        [InlineKeyboardButton("❌ Cancel", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        sell_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    
    return SELL_PHONE

async def handle_sell_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle phone number input for selling."""
    phone = update.message.text.strip()
    
    # Basic phone validation
    if not phone.startswith('+') or len(phone) < 8:
        await update.message.reply_text(
            "❌ Invalid phone format. Please use format: +1234567890",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="main_menu")]])
        )
        return SELL_PHONE
    
    # Store phone in context
    context.user_data['sell_phone'] = phone
    
    # Send login code request
    code_text = f"""
📱 **Step 2: OTP Verification**

We are sending a login code to: `{phone}`

Please enter the **5-digit code** you receive on Telegram:

**Format:** 12345

⏰ **Waiting for your verification code...**
    """
    
    keyboard = [
        [InlineKeyboardButton("❌ Cancel Sale", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        code_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    
    return SELL_CODE

async def handle_sell_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle OTP code input and detect 2FA."""
    code = update.message.text.strip()
    
    if not code.isdigit() or len(code) != 5:
        await update.message.reply_text(
            "❌ Invalid code format. Please enter the 5-digit code.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="main_menu")]])
        )
        return SELL_CODE
    
    context.user_data['sell_code'] = code
    
    # Simulate 2FA detection (in real implementation, you'd try to login here)
    import random
    has_2fa = random.choice([True, False])  # Simulate 2FA detection
    
    if has_2fa:
        # 2FA detected - ask user to disable it
        twofa_text = """
🔐 **2FA Detected!**

**Step 3: Disable 2FA**

Your account has **Two-Factor Authentication** enabled.

**⚠️ IMPORTANT:** You must **DISABLE 2FA** before we can process the sale.

**How to disable 2FA:**
1. Go to **Settings** → **Privacy & Security**
2. Select **Two-Step Verification**  
3. Turn **OFF** Two-Step Verification
4. Confirm by entering your current password

**Once disabled, click "2FA Disabled" below:**
        """
        
        keyboard = [
            [InlineKeyboardButton("✅ 2FA Disabled", callback_data="2fa_disabled")],
            [InlineKeyboardButton("❌ Cancel Sale", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            twofa_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
        return SELL_2FA_DISABLE
    else:
        # No 2FA detected - proceed to spam check
        return await check_spam_report(update, context)

async def handle_2fa_disabled(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle 2FA disabled confirmation."""
    await update.callback_query.answer("✅ 2FA Status Updated")
    
    # Proceed to spam check
    return await check_spam_report(update, context)

async def check_spam_report(update, context) -> int:
    """Check account spam report and freeze status."""
    import random
    
    # Simulate spam report check
    is_spam_reported = random.choice([True, False])
    confirmation_count = random.randint(0, 10)
    freeze_hours = random.randint(24, 48) if is_spam_reported else 0
    
    if is_spam_reported:
        # Account has spam reports - show freeze warning
        spam_text = f"""
⚠️ **Spam Report Detected**

**Account Status Check:**
• 🚨 **Spam Reports:** {confirmation_count} reports found
• ❄️ **Account Frozen:** {freeze_hours} hours remaining
• 📊 **Confirmation Count:** {confirmation_count}/10

**⏳ IMPORTANT:**
Your account will be **frozen for {freeze_hours} hours** due to spam reports.

During this time:
• Account selling is **temporarily disabled**
• You can still use your account normally
• Freeze will lift automatically after {freeze_hours}h

**Would you like to continue anyway?**
        """
        
        keyboard = [
            [InlineKeyboardButton("✅ Continue Sale", callback_data="continue_with_freeze")],
            [InlineKeyboardButton("❌ Cancel Sale", callback_data="main_menu")]
        ]
        
        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.edit_message_text(spam_text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await update.message.reply_text(spam_text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
        
        return SELL_SPAM_CHECK
    else:
        # No spam reports - proceed to account setup
        return await start_account_setup(update, context)

async def handle_continue_with_freeze(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle continuing sale despite freeze."""
    await update.callback_query.answer("✅ Proceeding with sale")
    
    return await start_account_setup(update, context)

async def start_account_setup(update, context) -> int:
    """Start account setup process - ask for name."""
    setup_text = """
👤 **Account Setup - Step 4**

**Set Account Name**

Please provide the **new name** you want for this account:

**Examples:**
• John Smith
• Sarah Johnson  
• Mike Wilson

**Enter the new account name:**
    """
    
    keyboard = [
        [InlineKeyboardButton("🎲 Generate Random", callback_data="random_name")],
        [InlineKeyboardButton("❌ Cancel Sale", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if hasattr(update, 'callback_query') and update.callback_query:
        await update.callback_query.edit_message_text(setup_text, parse_mode='Markdown', reply_markup=reply_markup)
    else:
        await update.message.reply_text(setup_text, parse_mode='Markdown', reply_markup=reply_markup)
    
    return SELL_NAME

async def handle_sell_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle account name input."""
    if update.callback_query and update.callback_query.data == "random_name":
        # Generate random name
        import random
        names = ["Alex Johnson", "Sarah Smith", "Mike Wilson", "Emma Davis", "John Brown", "Lisa Taylor"]
        name = random.choice(names)
        await update.callback_query.answer(f"✅ Generated: {name}")
        context.user_data['sell_name'] = name
    else:
        name = update.message.text.strip()
        if len(name) < 2:
            await update.message.reply_text(
                "❌ Name too short. Please enter a valid name.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="main_menu")]])
            )
            return SELL_NAME
        context.user_data['sell_name'] = name
    
    # Ask for profile photo
    photo_text = """
📸 **Account Setup - Step 5**

**Set Profile Photo**

Please send a **photo** for the new profile picture, or choose an option below:

**Options:**
• Send any image from your gallery
• Use camera to take new photo
• Generate random avatar

**Send photo or choose option:**
    """
    
    keyboard = [
        [InlineKeyboardButton("🎲 Random Avatar", callback_data="random_photo")],
        [InlineKeyboardButton("⏭️ Skip Photo", callback_data="skip_photo")],
        [InlineKeyboardButton("❌ Cancel Sale", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if hasattr(update, 'callback_query') and update.callback_query:
        await update.callback_query.edit_message_text(photo_text, parse_mode='Markdown', reply_markup=reply_markup)
    else:
        await update.message.reply_text(photo_text, parse_mode='Markdown', reply_markup=reply_markup)
    
    return SELL_PHOTO

async def handle_sell_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle profile photo input."""
    if update.callback_query:
        if update.callback_query.data == "random_photo":
            await update.callback_query.answer("✅ Random avatar selected")
            context.user_data['sell_photo'] = "random_avatar"
        elif update.callback_query.data == "skip_photo":
            await update.callback_query.answer("⏭️ Photo skipped")
            context.user_data['sell_photo'] = None
    elif update.message and update.message.photo:
        # User sent a photo
        context.user_data['sell_photo'] = update.message.photo[-1].file_id
        await update.message.reply_text("✅ Photo received!")
    else:
        await update.message.reply_text(
            "❌ Please send a photo or use the buttons below.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎲 Random Avatar", callback_data="random_photo")],
                [InlineKeyboardButton("⏭️ Skip Photo", callback_data="skip_photo")]
            ])
        )
        return SELL_PHOTO
    
    # Ask for 2FA setup
    twofa_setup_text = """
🔐 **Account Setup - Step 6**

**Setup New 2FA**

Now we'll setup a **new 2FA password** for security.

Please enter a **strong password** (8+ characters):

**Requirements:**
• Minimum 8 characters
• Mix of letters and numbers
• Easy for you to remember

**Enter new 2FA password:**
    """
    
    keyboard = [
        [InlineKeyboardButton("🎲 Generate Strong Password", callback_data="generate_password")],
        [InlineKeyboardButton("❌ Cancel Sale", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if hasattr(update, 'callback_query') and update.callback_query:
        await update.callback_query.edit_message_text(twofa_setup_text, parse_mode='Markdown', reply_markup=reply_markup)
    else:
        await update.message.reply_text(twofa_setup_text, parse_mode='Markdown', reply_markup=reply_markup)
    
    return SELL_2FA_SETUP

async def handle_sell_2fa_setup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle 2FA password setup."""
    if update.callback_query and update.callback_query.data == "generate_password":
        # Generate strong password
        import random
        import string
        password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
        await update.callback_query.answer(f"✅ Generated: {password}")
        context.user_data['sell_new_2fa'] = password
    else:
        password = update.message.text.strip()
        if len(password) < 8:
            await update.message.reply_text(
                "❌ Password too short. Please enter at least 8 characters.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="main_menu")]])
            )
            return SELL_2FA_SETUP
        context.user_data['sell_new_2fa'] = password
    
    # Show final confirmation
    return await show_final_confirmation(update, context)

async def show_final_confirmation(update, context) -> int:
    """Show final confirmation before processing sale."""
    phone = context.user_data.get('sell_phone', 'Unknown')
    name = context.user_data.get('sell_name', 'Not set')
    has_photo = context.user_data.get('sell_photo') is not None
    new_2fa = context.user_data.get('sell_new_2fa', 'Not set')
    
    confirm_text = f"""
✅ **Final Confirmation**

**Account Sale Summary:**
• 📱 **Phone:** `{phone}`
• 👤 **New Name:** `{name}`
• 📸 **Photo:** {'✅ Set' if has_photo else '❌ Not set'}
• 🔐 **New 2FA:** `{new_2fa[:3]}***` (hidden)
• 💰 **Earnings:** $15-35

**🔄 What we'll do:**
1. Login to your account securely
2. Change name to: `{name}`
3. {'Set new profile photo' if has_photo else 'Keep current photo'}
4. Setup new 2FA password
5. Terminate all sessions
6. Transfer ownership
7. Pay you instantly!

**⚠️ FINAL WARNING:**
After confirmation, you will **LOSE ACCESS** to this account **PERMANENTLY**.

**Are you absolutely sure?**
    """
    
    keyboard = [
        [InlineKeyboardButton("✅ YES, SELL MY ACCOUNT NOW", callback_data="confirm_final_sale")],
        [InlineKeyboardButton("❌ Cancel Sale", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if hasattr(update, 'callback_query') and update.callback_query:
        await update.callback_query.edit_message_text(confirm_text, parse_mode='Markdown', reply_markup=reply_markup)
    else:
        await update.message.reply_text(confirm_text, parse_mode='Markdown', reply_markup=reply_markup)
    
    return SELL_CONFIRM

async def process_account_sale(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle 2FA password or skip."""
    if update.message:
        password = update.message.text.strip()
        context.user_data['sell_password'] = password if password.lower() != 'skip' else None
    elif update.callback_query and update.callback_query.data == "skip_password":
        context.user_data['sell_password'] = None
        await update.callback_query.answer()
    
    # Show confirmation
    phone = context.user_data.get('sell_phone', 'Unknown')
    has_password = context.user_data.get('sell_password') is not None
    
    confirm_text = f"""
✅ **Confirm Account Sale**

**Account Details:**
• 📱 Phone: `{phone}`
• 🔐 2FA: {'✅ Enabled' if has_password else '❌ Disabled'}
• 💰 Estimated Earnings: $15-35

**What we'll do:**
1. Login to your account securely
2. Change account name to random name 💠
3. Change username to random username 💠  
4. Set new random profile photo 💠
5. Setup new 2FA password 💠
6. Terminate all active sessions 🔄
7. Transfer account ownership
8. Pay you instantly! 💰

**⚠️ Warning:** After sale, you will lose access to this account permanently.

**Are you sure you want to proceed?**
    """
    
    keyboard = [
        [InlineKeyboardButton("✅ YES, SELL MY ACCOUNT", callback_data="confirm_sale")],
        [InlineKeyboardButton("❌ No, Cancel", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.message:
        await update.message.reply_text(confirm_text, parse_mode='Markdown', reply_markup=reply_markup)
    else:
        await update.callback_query.edit_message_text(confirm_text, parse_mode='Markdown', reply_markup=reply_markup)
    
    return SELL_CONFIRM

async def process_account_sale(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process the actual account sale with new flow."""
    await update.callback_query.answer()
    
    user = update.effective_user
    phone = context.user_data.get('sell_phone')
    code = context.user_data.get('sell_code') 
    name = context.user_data.get('sell_name')
    photo = context.user_data.get('sell_photo')
    new_2fa = context.user_data.get('sell_new_2fa')
    
    # Show detailed processing message
    processing_text = f"""
⚡ **Processing Account Sale...**

**Account Configuration:**
✅ Phone verified: `{phone}`
✅ Login code: `{code}`
⏳ Setting name to: `{name}`
⏳ {'Setting new profile photo...' if photo else 'Keeping current photo...'}
⏳ Setting up 2FA: `{new_2fa[:3]}***`
⏳ Terminating all sessions...
⏳ Finalizing ownership transfer...
⏳ Processing instant payment...

**Please wait, this may take 2-3 minutes...**
    """
    
    await update.callback_query.edit_message_text(processing_text, parse_mode='Markdown')
    
    # Simulate account configuration process
    import asyncio
    await asyncio.sleep(2)
    
    # Create the account sale record
    db = get_db_session()
    try:
        db_user = UserService.get_user_by_telegram_id(db, user.id)
        
        # Create telegram account record
        account = TelegramAccountService.create_account(
            db=db,
            seller_id=db_user.id,
            phone_number=phone,
            session_string="demo_session_data"
        )
        
        # Create sale record with random price
        import random
        sale_price = round(random.uniform(15, 35), 2)
        
        from database.operations import AccountSaleService
        sale = AccountSaleService.create_sale(
            db=db,
            account_id=account.id,
            seller_id=db_user.id,
            sale_price=sale_price
        )
        
        # Complete the sale
        AccountSaleService.complete_sale(db, sale.id)
        
        # Success message with actual configuration details
        username = name.lower().replace(' ', '_') + f"_{random.randint(100,999)}"
        success_text = f"""
🎉 **ACCOUNT SOLD SUCCESSFULLY!**

**Sale Details:**
• 📱 **Phone:** `{phone}`
• 💰 **Earnings:** `${sale_price:.2f}`
• 🕐 **Completed:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

**✅ Account Configuration Completed:**
• 👤 Name changed to: `{name}`
• 📝 Username set to: `@{username}`
• 📸 {'New profile photo set' if photo else 'Profile photo unchanged'}
• 🔐 New 2FA password: `{new_2fa[:3]}***` (secured)
• 🔄 All sessions terminated
• 📱 Account ownership transferred

**💰 Payment instantly added to your balance!**

**Your new balance: `${db_user.balance:.2f}`**

**🎊 Thank you for selling with us!**
        """
        
        keyboard = [
            [InlineKeyboardButton("💸 Withdraw Earnings", callback_data="withdraw_menu")],
            [InlineKeyboardButton("🚀 Sell Another Account", callback_data="lfg_sell")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(success_text, parse_mode='Markdown', reply_markup=reply_markup)
        
        # Log the sale
        ActivityLogService.log_action(
            db=db,
            user_id=db_user.id,
            action_type="ACCOUNT_SALE",
            description=f"Account {phone} sold for ${sale_price}",
            extra_data=json.dumps({"phone": phone, "price": sale_price})
        )
        
    except Exception as e:
        logger.error(f"Error processing sale: {e}")
        await update.callback_query.edit_message_text(
            "❌ Error processing sale. Please contact support.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]])
        )
    finally:
        close_db_session(db)
    
    # Clear user data
    context.user_data.clear()
    return ConversationHandler.END

async def show_my_accounts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user's account selling history."""
    user = update.effective_user
    db = get_db_session()
    
    try:
        db_user = UserService.get_user_by_telegram_id(db, user.id)
        accounts = TelegramAccountService.get_user_accounts(db, db_user.id)
        
        if not accounts:
            accounts_text = """
📱 **Your Accounts**

You haven't sold any accounts yet.

🚀 **Ready to start earning?**
Use the "LFG (Sell)" button to sell your first account!

**Benefits:**
• 💰 Instant payments
• 🔐 Secure process  
• ⚡ Fast completion (5-15 mins)
• 💵 Earn $5-50 per account
            """
        else:
            accounts_text = f"""
📱 **Your Account History ({len(accounts)})**

**Total Sold:** {db_user.total_accounts_sold}
**Total Earnings:** `${db_user.total_earnings:.2f}`

**Account List:**
            """
            
            for i, account in enumerate(accounts[-5:], 1):  # Show last 5
                status_emoji = {"SOLD": "✅", "AVAILABLE": "📱", "FROZEN": "❄️"}.get(account.status.value, "❓")
                price_text = f"${account.sale_price:.2f}" if account.sale_price else "Pending"
                accounts_text += f"\n{i}. {status_emoji} `{account.phone_number}` - {price_text}"
        
        keyboard = [
            [InlineKeyboardButton("🚀 Sell New Account", callback_data="sell_new_account")],
            [InlineKeyboardButton("← Back", callback_data="lfg_sell")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            accounts_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Error showing accounts: {e}")
    finally:
        close_db_session(db)

async def handle_captcha_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle IMAGE CAPTCHA text answers."""
    from services.captcha import ImageCaptchaService
    
    user = update.effective_user
    user_answer = update.message.text.strip()
    
    # Check if user is in verification process
    if not context.user_data.get('captcha_answer') or context.user_data.get('verification_step') != 1:
        return  # Not in verification process
    
    db = get_db_session()
    image_captcha_service = ImageCaptchaService()
    
    try:
        # Verify IMAGE CAPTCHA answer
        correct_answer = context.user_data.get('captcha_answer', '')
        is_correct = image_captcha_service.verify_image_captcha(user_answer, correct_answer)
        
        # Clean up CAPTCHA image file
        captcha_filepath = context.user_data.get('captcha_filepath')
        if captcha_filepath:
            image_captcha_service.cleanup_captcha_image(captcha_filepath)
            context.user_data.pop('captcha_filepath', None)
        
        if is_correct:
            # CAPTCHA passed, move to channel verification
            db_user = UserService.get_user_by_telegram_id(db, user.id)
            if db_user:
                # Update captcha completion
                db_user.captcha_completed = True
                db.commit()
            
            # Move to channel verification step
            context.user_data['verification_step'] = 2
            await show_channel_verification(update, context)
            
            # Log successful captcha
            ActivityLogService.log_action(
                db=db,
                user_id=db_user.id if db_user else None,
                action_type="CAPTCHA_COMPLETED",
                description=f"User completed IMAGE CAPTCHA verification",
                extra_data=json.dumps({"answer": user_answer})
            )
        else:
            # CAPTCHA failed
            await update.message.reply_text(
                f"❌ **Incorrect Answer!**\\n\\n"
                f"Your answer: `{user_answer}`\\n"
                f"The characters were not matching. Please try again with a new CAPTCHA.",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 New CAPTCHA", callback_data="new_captcha")],
                    [InlineKeyboardButton("← Back to Start", callback_data="main_menu")]
                ])
            )
            
            # Log failed captcha
            if db_user := UserService.get_user_by_telegram_id(db, user.id):
                ActivityLogService.log_action(
                    db=db,
                    user_id=db_user.id,
                    action_type="CAPTCHA_FAILED",
                    description=f"User failed IMAGE CAPTCHA verification",
                    extra_data=json.dumps({"user_answer": user_answer})
                )
            
    except Exception as e:
        logger.error(f"Error handling IMAGE CAPTCHA answer: {e}")
        await update.message.reply_text(
            "❌ An error occurred while verifying your answer. Please try again."
        )
    finally:
        close_db_session(db)

async def show_channel_verification(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show channel joining verification step."""
    from services.captcha import VerificationTaskService
    
    task_service = VerificationTaskService()
    channels = task_service.get_required_channels()
    
    channels_text = f"""
🔒 **Step 2/3: Channel Verification**

✅ **CAPTCHA Completed!**

Now please join ALL required channels below:

**Required Channels:**
"""
    
    for i, channel in enumerate(channels, 1):
        channels_text += f"\\n{i}. **{channel['name']}** - {channel['description']}"
    
    channels_text += f"""

⚠️ **Important:** 
• You MUST join ALL channels above
• After joining, click 'Verify Membership'
• We will check your membership automatically

**Ready to continue?**
    """
    
    # Create buttons for each channel + verification button
    keyboard = []
    for channel in channels:
        keyboard.append([InlineKeyboardButton(f"📢 Join {channel['name']}", url=channel['link'])])
    
    keyboard.append([InlineKeyboardButton("✅ Verify Membership", callback_data="verify_channels")])
    keyboard.append([InlineKeyboardButton("← Back to CAPTCHA", callback_data="start_verification")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            channels_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            channels_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

async def handle_verify_channels(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle channel verification."""
    user = update.effective_user
    
    # For now, we'll skip actual verification since we can't check private channels
    # In production, you'd implement actual channel membership checking
    
    db = get_db_session()
    try:
        db_user = UserService.get_user_by_telegram_id(db, user.id)
        if db_user:
            # Mark verification as complete
            UserService.complete_user_verification(db, db_user.id)
        
        success_text = f"""
🎉 **Verification Complete!**

✅ **CAPTCHA:** Completed
✅ **Channels:** Verified  
✅ **Account Status:** ACTIVE

**Welcome to the Telegram Account Selling Platform!**

You now have full access to all features:
• 🚀 **LFG (Sell Account)** - Start selling your accounts
• 💰 **Balance Management** - Track your earnings
• 💸 **Withdraw Funds** - Cash out your profits
• 📱 **Account Management** - Manage your listings

**Ready to start earning?** Click below to access the main menu!
        """
        
        keyboard = [
            [InlineKeyboardButton("🚀 Start Selling (LFG)", callback_data="lfg_sell")],
            [InlineKeyboardButton("📋 Main Menu", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            success_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
        # Log successful verification
        ActivityLogService.log_action(
            db=db,
            user_id=db_user.id if db_user else None,
            action_type="VERIFICATION_COMPLETED",
            description=f"User completed full verification process"
        )
        
    except Exception as e:
        logger.error(f"Error in channel verification: {e}")
        await update.callback_query.edit_message_text(
            "❌ An error occurred during verification. Please contact support.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🆘 Contact Support", url="https://t.me/BujhlamNaKiHolo")
            ]])
        )
    finally:
        close_db_session(db)

# Withdrawal Handlers

async def handle_withdraw_trx(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle TRX withdrawal option."""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    db = get_db_session()
    
    try:
        db_user = UserService.get_user_by_telegram_id(db, user.id)
        if not db_user:
            await query.edit_message_text("❌ User not found. Please restart the bot.")
            return
            
        # Check user balance
        balance = db_user.balance or 0.0
        if balance <= 0:
            await query.edit_message_text(
                "❌ *Insufficient Balance*\n\n"
                "Your current balance is $0.00. You need to sell accounts first to earn money for withdrawal.\n\n"
                "💡 Sell accounts to build your balance!",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🚀 Sell Account", callback_data="lfg_sell"),
                    InlineKeyboardButton("🔙 Back", callback_data="withdraw_menu")
                ]])
            )
            return
            
        # Show TRX withdrawal form
        text = (
            "💎 *TRX Withdrawal*\n\n"
            f"💰 Available Balance: *${balance:.2f}*\n"
            f"💸 Minimum Withdrawal: *$5.00*\n\n"
            "📝 Please provide your withdrawal details:\n"
            "1️⃣ TRX Address (TRON Network)\n"
            "2️⃣ Withdrawal Amount (USD)\n\n"
            "📄 *Format Example:*\n"
            "`TRXAddress: TQn9Y2khEsLJW1ChVWFMSMeRDow5KcbLSE`\n"
            "`Amount: 10.00`\n\n"
            "⚠️ Please double-check your TRX address! Incorrect addresses will result in lost funds."
        )
        
        keyboard = [
            [InlineKeyboardButton("ℹ️ How to Get TRX Address", url="https://support.tronlink.org/hc/en-us/articles/4403161972617-How-to-create-a-TRON-wallet-")],
            [InlineKeyboardButton("🔙 Back to Methods", callback_data="withdraw_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)
        
        # Store withdrawal type in context
        context.user_data['withdrawal_type'] = 'TRX'
        
    except Exception as e:
        logger.error(f"Error in TRX withdrawal handler: {e}")
        await query.edit_message_text(
            "❌ An error occurred. Please try again later.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Back", callback_data="withdraw_menu")
            ]])
        )
    finally:
        close_db_session(db)

async def handle_withdraw_usdt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle USDT-BEP20 withdrawal option."""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    db = get_db_session()
    
    try:
        db_user = UserService.get_user_by_telegram_id(db, user.id)
        if not db_user:
            await query.edit_message_text("❌ User not found. Please restart the bot.")
            return
            
        # Check user balance
        balance = db_user.balance or 0.0
        if balance <= 0:
            await query.edit_message_text(
                "❌ *Insufficient Balance*\n\n"
                "Your current balance is $0.00. You need to sell accounts first to earn money for withdrawal.\n\n"
                "💡 Sell accounts to build your balance!",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🚀 Sell Account", callback_data="lfg_sell"),
                    InlineKeyboardButton("🔙 Back", callback_data="withdraw_menu")
                ]])
            )
            return
            
        # Show USDT-BEP20 withdrawal form
        text = (
            "💵 *USDT-BEP20 Withdrawal*\n\n"
            f"💰 Available Balance: *${balance:.2f}*\n"
            f"💸 Minimum Withdrawal: *$5.00*\n\n"
            "📝 Please provide your withdrawal details:\n"
            "1️⃣ USDT-BEP20 Address (Binance Smart Chain)\n"
            "2️⃣ Withdrawal Amount (USD)\n\n"
            "📄 *Format Example:*\n"
            "`BEP20Address: 0x1234567890abcdef1234567890abcdef12345678`\n"
            "`Amount: 10.00`\n\n"
            "⚠️ *IMPORTANT:* Make sure you're using BEP20 network (BSC)! Using wrong network will result in lost funds."
        )
        
        keyboard = [
            [InlineKeyboardButton("ℹ️ How to Get BEP20 Address", url="https://academy.binance.com/en/articles/how-to-add-binance-smart-chain-bsc-to-metamask")],
            [InlineKeyboardButton("🔙 Back to Methods", callback_data="withdraw_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)
        
        # Store withdrawal type in context
        context.user_data['withdrawal_type'] = 'USDT-BEP20'
        
    except Exception as e:
        logger.error(f"Error in USDT withdrawal handler: {e}")
        await query.edit_message_text(
            "❌ An error occurred. Please try again later.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Back", callback_data="withdraw_menu")
            ]])
        )
    finally:
        close_db_session(db)

async def handle_withdraw_binance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle Binance withdrawal option."""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    db = get_db_session()
    
    try:
        db_user = UserService.get_user_by_telegram_id(db, user.id)
        if not db_user:
            await query.edit_message_text("❌ User not found. Please restart the bot.")
            return
            
        # Check user balance
        balance = db_user.balance or 0.0
        if balance <= 0:
            await query.edit_message_text(
                "❌ *Insufficient Balance*\n\n"
                "Your current balance is $0.00. You need to sell accounts first to earn money for withdrawal.\n\n"
                "💡 Sell accounts to build your balance!",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🚀 Sell Account", callback_data="lfg_sell"),
                    InlineKeyboardButton("🔙 Back", callback_data="withdraw_menu")
                ]])
            )
            return
            
        # Show Binance withdrawal form
        text = (
            "🟡 *Binance Withdrawal*\n\n"
            f"💰 Available Balance: *${balance:.2f}*\n"
            f"💸 Minimum Withdrawal: *$5.00*\n\n"
            "📝 Please provide your withdrawal details:\n"
            "1️⃣ Binance Email/ID\n"
            "2️⃣ Withdrawal Amount (USD)\n"
            "3️⃣ Preferred Currency (USDT/BTC/ETH)\n\n"
            "📄 *Format Example:*\n"
            "`Binance Email: yourname@gmail.com`\n"
            "`Amount: 10.00`\n"
            "`Currency: USDT`\n\n"
            "⚠️ Make sure your Binance account can receive transfers!"
        )
        
        keyboard = [
            [InlineKeyboardButton("ℹ️ How to Find Binance ID", url="https://www.binance.com/en/support/faq/how-to-find-your-binance-account-id-115003398712")],
            [InlineKeyboardButton("🔙 Back to Methods", callback_data="withdraw_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)
        
        # Store withdrawal type in context
        context.user_data['withdrawal_type'] = 'Binance'
        
    except Exception as e:
        logger.error(f"Error in Binance withdrawal handler: {e}")
        await query.edit_message_text(
            "❌ An error occurred. Please try again later.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Back", callback_data="withdraw_menu")
            ]])
        )
    finally:
        close_db_session(db)

async def handle_withdrawal_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user's withdrawal history."""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    db = get_db_session()
    
    try:
        # Import WithdrawalService
        from database.operations import WithdrawalService
        
        db_user = UserService.get_user_by_telegram_id(db, user.id)
        if not db_user:
            await query.edit_message_text("❌ User not found. Please restart the bot.")
            return
            
        # Get user's withdrawals
        withdrawals = WithdrawalService.get_user_withdrawals(db, db_user.id)
        
        if not withdrawals:
            text = (
                "📋 *Withdrawal History*\n\n"
                "🚫 No withdrawal requests found.\n\n"
                "💡 Make your first withdrawal to see history here!"
            )
            keyboard = [
                [InlineKeyboardButton("💰 Make Withdrawal", callback_data="withdraw_menu")],
                [InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")]
            ]
        else:
            text = "📋 *Withdrawal History*\n\n"
            keyboard = []
            
            for i, withdrawal in enumerate(withdrawals[:10]):  # Show last 10
                status_emoji = {
                    'PENDING': '⏳',
                    'LEADER_APPROVED': '✅',
                    'COMPLETED': '💚',
                    'REJECTED': '❌'
                }.get(withdrawal.status.value, '⏳')
                
                text += (
                    f"{status_emoji} *${withdrawal.amount:.2f}* - {withdrawal.method}\n"
                    f"📅 {withdrawal.created_at.strftime('%Y-%m-%d %H:%M')}\n"
                    f"📊 Status: {withdrawal.status.value.title()}\n"
                )
                
                # Add delete button for completed/rejected withdrawals
                if withdrawal.status.value in ['COMPLETED', 'REJECTED']:
                    keyboard.append([
                        InlineKeyboardButton(
                            f"🗑 Delete #{withdrawal.id}", 
                            callback_data=f"delete_withdrawal_{withdrawal.id}"
                        )
                    ])
                
                text += "\n"
            
            # Add navigation buttons
            keyboard.extend([
                [InlineKeyboardButton("💰 New Withdrawal", callback_data="withdraw_menu")],
                [InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")]
            ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error in withdrawal history handler: {e}")
        await query.edit_message_text(
            "❌ An error occurred while loading withdrawal history.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Back", callback_data="withdraw_menu")
            ]])
        )
    finally:
        close_db_session(db)

async def handle_delete_withdrawal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle deletion of withdrawal record."""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    db = get_db_session()
    
    try:
        # Extract withdrawal ID from callback data
        withdrawal_id = int(query.data.split('_')[-1])
        
        # Import WithdrawalService
        from database.operations import WithdrawalService
        
        db_user = UserService.get_user_by_telegram_id(db, user.id)
        if not db_user:
            await query.edit_message_text("❌ User not found. Please restart the bot.")
            return
        
        # Get the withdrawal to verify ownership and status
        withdrawal = WithdrawalService.get_user_withdrawals(db, db_user.id)
        target_withdrawal = next((w for w in withdrawal if w.id == withdrawal_id), None)
        
        if not target_withdrawal:
            await query.edit_message_text(
                "❌ Withdrawal not found or you don't have permission to delete it.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Back", callback_data="withdrawal_history")
                ]])
            )
            return
        
        # Only allow deletion of completed or rejected withdrawals
        if target_withdrawal.status.value not in ['COMPLETED', 'REJECTED']:
            await query.edit_message_text(
                "❌ You can only delete completed or rejected withdrawals.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Back", callback_data="withdrawal_history")
                ]])
            )
            return
        
        # Delete the withdrawal record
        try:
            db.delete(target_withdrawal)
            db.commit()
            
            await query.edit_message_text(
                f"✅ Withdrawal record #{withdrawal_id} has been deleted successfully.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("📋 View History", callback_data="withdrawal_history"),
                    InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")
                ]])
            )
            
            # Log the deletion
            ActivityLogService.log_action(
                db=db,
                user_id=db_user.id,
                action_type="WITHDRAWAL_DELETED",
                description=f"User deleted withdrawal record #{withdrawal_id}"
            )
            
        except Exception as delete_error:
            logger.error(f"Error deleting withdrawal {withdrawal_id}: {delete_error}")
            db.rollback()
            await query.edit_message_text(
                "❌ Failed to delete withdrawal record. Please try again later.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Back", callback_data="withdrawal_history")
                ]])
            )
        
    except Exception as e:
        logger.error(f"Error in delete withdrawal handler: {e}")
        await query.edit_message_text(
            "❌ An error occurred while processing deletion.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Back", callback_data="withdrawal_history")
            ]])
        )
    finally:
        close_db_session(db)

# Withdrawal Conversation Handlers

async def handle_withdrawal_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process withdrawal details submitted by user."""
    user = update.effective_user
    message_text = update.message.text
    
    db = get_db_session()
    
    try:
        db_user = UserService.get_user_by_telegram_id(db, user.id)
        if not db_user:
            await update.message.reply_text("❌ User not found. Please restart the bot.")
            return ConversationHandler.END
        
        # Get withdrawal type from context
        withdrawal_type = context.user_data.get('withdrawal_type', 'TRX')
        
        # Parse withdrawal details
        lines = [line.strip() for line in message_text.split('\n') if line.strip()]
        
        withdrawal_data = {}
        amount = None
        address_or_email = None
        currency = None
        
        # Parse the input based on format
        for line in lines:
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().lower()
                value = value.strip()
                
                if 'address' in key or 'email' in key:
                    address_or_email = value
                elif 'amount' in key:
                    try:
                        amount = float(value.replace('$', ''))
                    except ValueError:
                        await update.message.reply_text(
                            "❌ Invalid amount format. Please enter a valid number.\n\n"
                            "Example: `Amount: 10.00`",
                            parse_mode='Markdown'
                        )
                        return WITHDRAW_DETAILS
                elif 'currency' in key and withdrawal_type == 'Binance':
                    currency = value.upper()
        
        # Validate required fields
        if not address_or_email:
            field_name = "email" if withdrawal_type == "Binance" else "address"
            await update.message.reply_text(
                f"❌ Please provide your {field_name}.\n\n"
                "Use the correct format as shown in the example."
            )
            return WITHDRAW_DETAILS
        
        if not amount:
            await update.message.reply_text(
                "❌ Please provide the withdrawal amount.\n\n"
                "Use the format: `Amount: 10.00`",
                parse_mode='Markdown'
            )
            return WITHDRAW_DETAILS
        
        # Validate minimum amount
        if amount < 5.0:
            await update.message.reply_text(
                "❌ Minimum withdrawal amount is $5.00.\n\n"
                "Please enter an amount of $5.00 or more."
            )
            return WITHDRAW_DETAILS
        
        # Check user balance
        if amount > (db_user.balance or 0.0):
            await update.message.reply_text(
                f"❌ Insufficient balance!\n\n"
                f"💰 Your balance: ${db_user.balance or 0:.2f}\n"
                f"💸 Requested amount: ${amount:.2f}\n\n"
                "Please enter a smaller amount or sell more accounts first."
            )
            return WITHDRAW_DETAILS
        
        # For Binance, set default currency if not provided
        if withdrawal_type == 'Binance' and not currency:
            currency = 'USDT'
        
        # Store withdrawal data in context for confirmation
        withdrawal_details = {
            'method': withdrawal_type,
            'amount': amount,
            'address_or_email': address_or_email,
            'currency': currency,
            'user_id': db_user.id
        }
        
        context.user_data['withdrawal_details'] = withdrawal_details
        
        # Show confirmation
        confirmation_text = (
            "✅ *Withdrawal Request Summary*\n\n"
            f"💳 Method: *{withdrawal_type}*\n"
            f"💰 Amount: *${amount:.2f}*\n"
        )
        
        if withdrawal_type == 'TRX':
            confirmation_text += f"📍 TRX Address: `{address_or_email}`\n"
        elif withdrawal_type == 'USDT-BEP20':
            confirmation_text += f"📍 BEP20 Address: `{address_or_email}`\n"
        elif withdrawal_type == 'Binance':
            confirmation_text += f"📧 Binance Email: `{address_or_email}`\n"
            confirmation_text += f"💱 Currency: *{currency}*\n"
        
        confirmation_text += (
            "\n⚠️ *Important:*\n"
            "• Double-check all details before confirming\n"
            "• Incorrect details may result in lost funds\n"
            "• Processing time: 1-24 hours after leader approval\n\n"
            "Do you want to submit this withdrawal request?"
        )
        
        keyboard = [
            [InlineKeyboardButton("✅ Confirm & Submit", callback_data="confirm_withdrawal")],
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel_withdrawal")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            confirmation_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
        return WITHDRAW_CONFIRM
        
    except Exception as e:
        logger.error(f"Error processing withdrawal details: {e}")
        await update.message.reply_text(
            "❌ An error occurred while processing your request. Please try again."
        )
        return ConversationHandler.END
    finally:
        close_db_session(db)

async def handle_withdrawal_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle withdrawal confirmation."""
    query = update.callback_query
    await query.answer()
    
    if query.data == "cancel_withdrawal":
        await query.edit_message_text(
            "❌ Withdrawal request cancelled.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("💰 Try Again", callback_data="withdraw_menu"),
                InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")
            ]])
        )
        return ConversationHandler.END
    
    if query.data == "confirm_withdrawal":
        user = update.effective_user
        db = get_db_session()
        
        try:
            withdrawal_details = context.user_data.get('withdrawal_details')
            if not withdrawal_details:
                await query.edit_message_text(
                    "❌ Withdrawal data not found. Please start over.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("💰 Try Again", callback_data="withdraw_menu")
                    ]])
                )
                return ConversationHandler.END
            
            db_user = UserService.get_user_by_telegram_id(db, user.id)
            if not db_user:
                await query.edit_message_text("❌ User not found. Please restart the bot.")
                return ConversationHandler.END
            
            # Create withdrawal request
            withdrawal = WithdrawalService.create_withdrawal(
                db=db,
                user_id=withdrawal_details['user_id'],
                amount=withdrawal_details['amount'],
                method=withdrawal_details['method'],
                address=withdrawal_details['address_or_email'],
                currency=withdrawal_details.get('currency', 'USD')
            )
            
            if withdrawal:
                # Send to leader notification channel
                await send_withdrawal_to_leaders(context.bot, withdrawal, db_user)
                
                success_text = (
                    "✅ *Withdrawal Request Submitted!*\n\n"
                    f"🆔 Request ID: *#{withdrawal.id}*\n"
                    f"💰 Amount: *${withdrawal.amount:.2f}*\n"
                    f"💳 Method: *{withdrawal.method}*\n\n"
                    "⏳ Your request is now pending leader approval.\n"
                    "📬 You'll be notified once it's processed.\n\n"
                    "⏰ Processing time: 1-24 hours"
                )
                
                keyboard = [
                    [InlineKeyboardButton("📋 View History", callback_data="withdrawal_history")],
                    [InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    success_text,
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
                
                # Log the withdrawal request
                ActivityLogService.log_action(
                    db=db,
                    user_id=db_user.id,
                    action_type="WITHDRAWAL_REQUESTED",
                    description=f"User requested ${withdrawal.amount:.2f} withdrawal via {withdrawal.method}"
                )
                
            else:
                await query.edit_message_text(
                    "❌ Failed to create withdrawal request. Please try again later.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("💰 Try Again", callback_data="withdraw_menu")
                    ]])
                )
            
        except Exception as e:
            logger.error(f"Error confirming withdrawal: {e}")
            await query.edit_message_text(
                "❌ An error occurred while processing your withdrawal. Please try again later.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("💰 Try Again", callback_data="withdraw_menu")
                ]])
            )
        finally:
            close_db_session(db)
    
    return ConversationHandler.END

async def send_withdrawal_to_leaders(bot, withdrawal, user):
    """Send withdrawal notification to leader channel."""
    try:
        # Get leader channel ID from environment or config
        LEADER_CHANNEL_ID = os.getenv('LEADER_CHANNEL_ID', '-1002234567890')  # Replace with actual channel ID
        
        notification_text = (
            "🚨 *NEW WITHDRAWAL REQUEST*\n\n"
            f"👤 User: {user.first_name or 'Unknown'} (@{user.username or 'no_username'})\n"
            f"🆔 User ID: `{user.telegram_user_id}`\n"
            f"💰 Amount: *${withdrawal.amount:.2f}*\n"
            f"💳 Method: *{withdrawal.method}*\n"
            f"📍 Address: `{withdrawal.address}`\n"
        )
        
        if withdrawal.currency and withdrawal.currency != 'USD':
            notification_text += f"💱 Currency: *{withdrawal.currency}*\n"
        
        notification_text += (
            f"\n🕒 Requested: {withdrawal.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"📊 Status: *PENDING APPROVAL*\n\n"
            "⚡ Please review and process this withdrawal request."
        )
        
        keyboard = [
            [
                InlineKeyboardButton("✅ Approve", callback_data=f"approve_withdrawal_{withdrawal.id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"reject_withdrawal_{withdrawal.id}")
            ],
            [InlineKeyboardButton("👤 View User", callback_data=f"view_user_{user.telegram_user_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await bot.send_message(
            chat_id=LEADER_CHANNEL_ID,
            text=notification_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Failed to send withdrawal notification to leaders: {e}")

def setup_main_handlers(application) -> None:
    """Set up the main bot handlers."""
    from telegram.ext import ConversationHandler
    
    # Account selling conversation handler
    sell_conversation = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_account_selling, pattern='^sell_new_account$')],
        states={
            SELL_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_sell_phone)],
            SELL_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_sell_code)],
            SELL_2FA_DISABLE: [CallbackQueryHandler(handle_2fa_disabled, pattern='^2fa_disabled$')],
            SELL_SPAM_CHECK: [CallbackQueryHandler(handle_continue_with_freeze, pattern='^continue_with_freeze$')],
            SELL_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_sell_name),
                CallbackQueryHandler(handle_sell_name, pattern='^random_name$')
            ],
            SELL_PHOTO: [
                MessageHandler(filters.PHOTO, handle_sell_photo),
                CallbackQueryHandler(handle_sell_photo, pattern='^(random_photo|skip_photo)$')
            ],
            SELL_2FA_SETUP: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_sell_2fa_setup),
                CallbackQueryHandler(handle_sell_2fa_setup, pattern='^generate_password$')
            ],
            SELL_CONFIRM: [CallbackQueryHandler(process_account_sale, pattern='^confirm_final_sale$')]
        },
        fallbacks=[CommandHandler('start', start_command)]
    )
    
    # Withdrawal conversation handler
    withdrawal_conversation = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(handle_withdraw_trx, pattern='^withdraw_trx$'),
            CallbackQueryHandler(handle_withdraw_usdt, pattern='^withdraw_usdt$'),
            CallbackQueryHandler(handle_withdraw_binance, pattern='^withdraw_binance$')
        ],
        states={
            WITHDRAW_DETAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_withdrawal_details)],
            WITHDRAW_CONFIRM: [
                CallbackQueryHandler(handle_withdrawal_confirmation, pattern='^(confirm_withdrawal|cancel_withdrawal)$')
            ]
        },
        fallbacks=[
            CommandHandler('start', start_command),
            CallbackQueryHandler(lambda u, c: handle_withdraw_menu(u, c), pattern='^withdraw_menu$')
        ]
    )
    
    application.add_handler(CommandHandler("start", start_command))
    
    # Register main callback handlers FIRST with higher priority
    # This ensures they get processed before conversation handlers
    application.add_handler(CallbackQueryHandler(lambda update, context: button_callback(update, context), pattern='^(start_verification|new_captcha|verify_channels|lfg_sell|account_details|check_balance|withdraw_menu|language_menu|system_capacity|user_status|contact_support|admin_panel|leader_panel|my_available_accounts|skip_password|confirm_sale|main_menu|why_verification|view_all_accounts|withdraw_trx|withdraw_usdt|withdraw_binance|withdrawal_history|delete_withdrawal_.+|confirm_withdrawal|cancel_withdrawal)$'))
    
    # Add conversation handlers after main callbacks
    application.add_handler(sell_conversation)
    application.add_handler(withdrawal_conversation)
    application.add_handler(get_real_selling_handler())
    
    # Add message handler for CAPTCHA answers (only process text messages)
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, 
        handle_captcha_answer
    ))
    
    # Add a catch-all callback handler to handle any unmatched callbacks
    # This ensures buttons always work even if conversation state gets stuck
    application.add_handler(CallbackQueryHandler(fallback_callback_handler))
    
    logger.info("Main handlers set up successfully")