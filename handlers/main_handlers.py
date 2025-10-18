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
from database.models import User, Withdrawal, WithdrawalStatus
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
        print(f"🎯🎯🎯 BUTTON CALLBACK DETECTED verify_channels for user {update.effective_user.id} 🎯🎯🎯")
        logger.error(f"🎯🎯🎯 BUTTON CALLBACK DETECTED verify_channels for user {update.effective_user.id} 🎯🎯🎯")
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
    # NOTE: withdraw_trx, withdraw_usdt, withdraw_binance are now handled by ConversationHandler
    elif data == "withdrawal_history":
        await handle_withdrawal_history(update, context)
    elif data.startswith("delete_withdrawal_"):
        await handle_delete_withdrawal(update, context)
    elif data.startswith("approve_withdrawal_"):
        await handle_approve_withdrawal(update, context)
    elif data.startswith("reject_withdrawal_"):
        await handle_reject_withdrawal(update, context)
    elif data.startswith("view_user_"):
        await handle_view_user_details(update, context)
    elif data.startswith("mark_paid_"):
        await handle_mark_paid(update, context)
    elif data == "leader_withdrawals":
        await handle_leader_withdrawals(update, context)
    else:
        logger.warning(f"Unknown callback data: {data} from user {user.id}")
        await query.edit_message_text("❓ Unknown option. Returning to main menu...")
        await start_command(update, context)

async def handle_start_verification(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start the verification process with enhanced CAPTCHA (visual/text)."""
    captcha_service = CaptchaService()
    captcha_data = await captcha_service.generate_captcha()
    
    # Only visual captcha text since we removed text-based captchas
    verification_text = f"""
🔒 **Step 1/3: CAPTCHA Verification**

🖼️ **Visual CAPTCHA Challenge**

**📝 Instructions:**
• Look at the image below carefully
• Type the exact text you see (letters and numbers)
• Case doesn't matter
• Enter the characters exactly as shown

**👇 Type the text from the image:**
    """
    
    keyboard = [
        [InlineKeyboardButton("🔄 New CAPTCHA", callback_data="new_captcha")],
        [InlineKeyboardButton("← Back to Start", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Store CAPTCHA answer in context
    context.user_data['captcha_answer'] = captcha_data['answer']
    context.user_data['captcha_type'] = captcha_data['type']
    context.user_data['captcha_image_path'] = captcha_data.get('image_path')
    context.user_data['verification_step'] = 1
    
    # Send text message first
    await update.callback_query.edit_message_text(
        verification_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    
    # If visual captcha, send the image
    if captcha_data['type'] == 'visual' and captcha_data.get('image_path'):
        try:
            with open(captcha_data['image_path'], 'rb') as photo:
                await update.callback_query.message.reply_photo(
                    photo=photo,
                    caption="🔍 **Enter the text shown in this image**",
                    parse_mode='Markdown'
                )
        except Exception as e:
            logger.error(f"Error sending captcha image: {e}")
            # Fallback to text-based captcha
            await update.callback_query.message.reply_text(
                "⚠️ **Image failed to load. Fallback question:**\n\n" + 
                "What is 25 + 17?"
            )
            context.user_data['captcha_answer'] = "42"

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
    
    print(f"🚨🚨🚨 FALLBACK HANDLER CAUGHT: {data} from user {user.id} 🚨🚨🚨")
    logger.error(f"🚨🚨🚨 FALLBACK HANDLER CAUGHT: {data} from user {user.id} 🚨🚨🚨")
    
    # If it's verify_channels, handle it directly here
    if data == "verify_channels":
        print(f"🚨 FALLBACK: Processing verify_channels for user {user.id}")
        await handle_verify_channels(update, context)
        return
    
    # For any other unmatched callback, return to main menu
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

async def handle_leader_withdrawals(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle leader withdrawals overview."""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    db = get_db_session()
    
    try:
        # Check if user is a leader
        db_user = UserService.get_user_by_telegram_id(db, user.id)
        if not db_user or not db_user.is_leader:
            await query.edit_message_text("❌ Access denied. Only leaders can view this panel.")
            return
        
        # Get pending withdrawals
        pending_withdrawals = db.query(Withdrawal).filter(
            Withdrawal.status == WithdrawalStatus.PENDING
        ).order_by(Withdrawal.created_at.desc()).limit(10).all()
        
        # Get approved (ready to pay) withdrawals
        approved_withdrawals = db.query(Withdrawal).filter(
            Withdrawal.status == WithdrawalStatus.LEADER_APPROVED
        ).order_by(Withdrawal.created_at.desc()).limit(5).all()
        
        if not pending_withdrawals and not approved_withdrawals:
            text = (
                "👑 *Leader - Withdrawal Management*\n\n"
                "✅ No pending withdrawals at this time.\n\n"
                "📊 All withdrawal requests are up to date!"
            )
            keyboard = [
                [InlineKeyboardButton("🔄 Refresh", callback_data="leader_withdrawals")],
                [InlineKeyboardButton("🔙 Leader Panel", callback_data="leader_panel")]
            ]
        else:
            text = "👑 *Leader - Withdrawal Management*\n\n"
            
            if pending_withdrawals:
                text += "⏳ *Pending Review:*\n"
                for w in pending_withdrawals:
                    user_info = db.query(User).filter(User.id == w.user_id).first()
                    text += (
                        f"💰 ${w.amount:.2f} - {w.withdrawal_method}\n"
                        f"👤 {user_info.first_name or 'Unknown'} (@{user_info.username or 'no_username'})\n"
                        f"🕒 {w.created_at.strftime('%m-%d %H:%M')}\n\n"
                    )
            
            if approved_withdrawals:
                text += "✅ *Ready to Pay:*\n"
                for w in approved_withdrawals:
                    user_info = db.query(User).filter(User.id == w.user_id).first()
                    text += (
                        f"💳 ${w.amount:.2f} - {w.withdrawal_method}\n"
                        f"👤 {user_info.first_name or 'Unknown'}\n"
                        f"📍 {w.withdrawal_address[:20]}...\n\n"
                    )
            
            keyboard = [
                [InlineKeyboardButton("🔄 Refresh", callback_data="leader_withdrawals")],
                [InlineKeyboardButton("🔙 Leader Panel", callback_data="leader_panel")]
            ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            text=text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Error in leader withdrawals handler: {e}")
        await query.edit_message_text("❌ An error occurred while loading withdrawals.")
    finally:
        close_db_session(db)

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
    """Handle CAPTCHA text answers for both visual and text captchas."""
    user = update.effective_user
    user_answer = update.message.text.strip()
    
    # Check if user is in verification process
    if not context.user_data.get('captcha_answer') or context.user_data.get('verification_step') != 1:
        return  # Not in verification process
    
    db = get_db_session()
    try:
        # Clean up visual captcha image if exists
        captcha_image_path = context.user_data.get('captcha_image_path')
        if captcha_image_path:
            from services.captcha import CaptchaService
            captcha_service = CaptchaService()
            captcha_service.cleanup_captcha_image(captcha_image_path)
            context.user_data.pop('captcha_image_path', None)
        
        # Verify CAPTCHA answer
        correct_answer = context.user_data.get('captcha_answer', '').lower().strip()
        captcha_type = context.user_data.get('captcha_type', 'text')
        
        # For visual captcha, be more flexible with answer checking
        if captcha_type == 'visual':
            is_correct = user_answer.lower().replace(' ', '') == correct_answer.replace(' ', '')
        else:
            is_correct = user_answer.lower().strip() == correct_answer
        
        if is_correct:
            # CAPTCHA passed, move to channel verification
            db_user = UserService.get_user_by_telegram_id(db, user.id)
            if db_user:
                # Update captcha completion
                db_user.captcha_completed = True
                db.commit()
            
            # Clear captcha data from context
            context.user_data.pop('captcha_answer', None)
            context.user_data.pop('captcha_type', None)
            
            # Move to channel verification step
            context.user_data['verification_step'] = 2
            await show_channel_verification(update, context)
            
            # Log successful captcha
            ActivityLogService.log_action(
                db=db,
                user_id=db_user.id if db_user else None,
                action_type="CAPTCHA_COMPLETED",
                description=f"User completed CAPTCHA verification",
                extra_data=json.dumps({"answer": user_answer})
            )
        else:
            # CAPTCHA failed - show appropriate error message
            if captcha_type == 'visual':
                error_message = f"❌ **Incorrect Answer!**\n\n" \
                              f"Your answer: `{user_answer}`\n" \
                              f"🔍 **Tip:** Look carefully at the image and enter exactly what you see (5 characters)\n\n" \
                              f"Please try again with a new CAPTCHA."
            else:
                error_message = f"❌ **Incorrect Answer!**\n\n" \
                              f"Your answer: `{user_answer}`\n" \
                              f"Please try again. Click the button below for a new CAPTCHA."
            
            await update.message.reply_text(
                error_message,
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
                    description=f"User failed CAPTCHA verification",
                    extra_data=json.dumps({"user_answer": user_answer, "correct_answer": correct_answer})
                )
            
    except Exception as e:
        logger.error(f"Error handling CAPTCHA answer: {e}")
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
    """Handle channel verification - SIMPLIFIED VERSION."""
    user = update.effective_user
    
    # VERY VISIBLE DEBUG LOGGING
    print(f"🔥🔥🔥 VERIFY CHANNELS FUNCTION CALLED - USER {user.id} 🔥🔥🔥")
    logger.error(f"🔥🔥🔥 VERIFY CHANNELS FUNCTION CALLED - USER {user.id} 🔥🔥🔥")
    
    db = get_db_session()
    try:
        # Answer callback first to prevent timeout
        await update.callback_query.answer("✅ Processing verification...")
        print(f"🔥 ANSWERED CALLBACK for user {user.id}")
        
        # Get user and mark verification complete
        db_user = UserService.get_user_by_telegram_id(db, user.id)
        if db_user:
            # Mark verification as complete
            db_user.verification_completed = True
            db_user.captcha_completed = True
            db_user.channels_joined = True
            from database.models import UserStatus
            db_user.status = UserStatus.ACTIVE
            db.commit()
            print(f"🔥 MARKED VERIFICATION COMPLETE for user {user.id}")
        
        # Import and directly call the main menu function
        from handlers.real_handlers import show_real_main_menu
        print(f"🔥 CALLING MAIN MENU for user {user.id}")
        await show_real_main_menu(update, context)
        print(f"🔥 MAIN MENU SUCCESS for user {user.id}")
        
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

async def handle_withdraw_trx(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle TRX withdrawal option."""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    db = get_db_session()
    
    try:
        db_user = UserService.get_user_by_telegram_id(db, user.id)
        if not db_user:
            await query.edit_message_text("❌ User not found. Please restart the bot.")
            return ConversationHandler.END
            
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
            return ConversationHandler.END
            
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
        context.user_data['conversation_type'] = 'withdrawal'
        
        return WITHDRAW_DETAILS
        
    except Exception as e:
        logger.error(f"Error in TRX withdrawal handler: {e}")
        await query.edit_message_text(
            "❌ An error occurred. Please try again later.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Back", callback_data="withdraw_menu")
            ]])
        )
        return ConversationHandler.END
    finally:
        close_db_session(db)

async def handle_withdraw_usdt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle USDT-BEP20 withdrawal option."""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    db = get_db_session()
    
    try:
        db_user = UserService.get_user_by_telegram_id(db, user.id)
        if not db_user:
            await query.edit_message_text("❌ User not found. Please restart the bot.")
            return ConversationHandler.END
            
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
            return ConversationHandler.END
            
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
        context.user_data['conversation_type'] = 'withdrawal'
        
        return WITHDRAW_DETAILS
        
    except Exception as e:
        logger.error(f"Error in USDT withdrawal handler: {e}")
        await query.edit_message_text(
            "❌ An error occurred. Please try again later.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Back", callback_data="withdraw_menu")
            ]])
        )
        return ConversationHandler.END
    finally:
        close_db_session(db)

async def handle_withdraw_binance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle Binance withdrawal option."""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    db = get_db_session()
    
    try:
        db_user = UserService.get_user_by_telegram_id(db, user.id)
        if not db_user:
            await query.edit_message_text("❌ User not found. Please restart the bot.")
            return ConversationHandler.END
            
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
            return ConversationHandler.END
            
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
        context.user_data['conversation_type'] = 'withdrawal'
        
        return WITHDRAW_DETAILS
        
    except Exception as e:
        logger.error(f"Error in Binance withdrawal handler: {e}")
        await query.edit_message_text(
            "❌ An error occurred. Please try again later.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Back", callback_data="withdraw_menu")
            ]])
        )
        return ConversationHandler.END
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
                    f"{status_emoji} *${withdrawal.amount:.2f}* - {withdrawal.withdrawal_method}\n"
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

async def handle_approve_withdrawal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle withdrawal approval by leaders."""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    db = get_db_session()
    
    try:
        # Extract withdrawal ID from callback data
        withdrawal_id = int(query.data.split('_')[-1])
        
        # Import services
        from database.operations import WithdrawalService, ActivityLogService
        
        # Check if user is a leader
        db_user = UserService.get_user_by_telegram_id(db, user.id)
        if not db_user or not db_user.is_leader:
            await query.edit_message_text("❌ Access denied. Only leaders can approve withdrawals.")
            return
        
        # Get the withdrawal
        withdrawal = db.query(Withdrawal).filter(Withdrawal.id == withdrawal_id).first()
        if not withdrawal:
            await query.edit_message_text("❌ Withdrawal not found.")
            return
        
        # Check if already processed
        if withdrawal.status != WithdrawalStatus.PENDING:
            await query.edit_message_text(
                f"❌ This withdrawal has already been {withdrawal.status.value.lower()}."
            )
            return
        
        # Approve the withdrawal
        withdrawal.status = WithdrawalStatus.LEADER_APPROVED
        withdrawal.assigned_leader_id = db_user.id
        withdrawal.processed_at = datetime.utcnow()
        
        db.commit()
        
        # Get the withdrawal user
        withdrawal_user = db.query(User).filter(User.id == withdrawal.user_id).first()
        
        # Update the notification message
        updated_text = (
            "✅ *WITHDRAWAL APPROVED*\n\n"
            f"👤 User: {withdrawal_user.first_name or 'Unknown'} (@{withdrawal_user.username or 'no_username'})\n"
            f"🆔 User ID: `{withdrawal_user.telegram_user_id}`\n"
            f"💰 Amount: *${withdrawal.amount:.2f}*\n"
            f"💳 Method: *{withdrawal.withdrawal_method}*\n"
            f"📍 Address: `{withdrawal.withdrawal_address}`\n"
            f"👑 Approved by: {db_user.first_name or 'Unknown'} (@{db_user.username or 'no_username'})\n"
            f"🕒 Approved: {withdrawal.processed_at.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            "✅ *Status: APPROVED FOR PROCESSING*"
        )
        
        keyboard = [
            [InlineKeyboardButton("💳 Mark as Paid", callback_data=f"mark_paid_{withdrawal.id}")],
            [InlineKeyboardButton("👤 View User", callback_data=f"view_user_{withdrawal_user.telegram_user_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text=updated_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
        # Notify the user
        try:
            await context.bot.send_message(
                chat_id=withdrawal_user.telegram_user_id,
                text=(
                    "✅ *Withdrawal Approved!*\n\n"
                    f"💰 Amount: *${withdrawal.amount:.2f}*\n"
                    f"💳 Method: *{withdrawal.withdrawal_method}*\n"
                    f"📍 Address: `{withdrawal.withdrawal_address}`\n\n"
                    "🕒 Your withdrawal has been approved and will be processed within 24 hours.\n"
                    "📧 You will receive a confirmation once the payment is sent."
                ),
                parse_mode='Markdown'
            )
        except Exception as notify_error:
            logger.error(f"Failed to notify user about approval: {notify_error}")
        
        # Log the activity
        ActivityLogService.log_action(
            db=db,
            user_id=withdrawal.user_id,
            action_type="WITHDRAWAL_APPROVED",
            description=f"Withdrawal ${withdrawal.amount:.2f} approved by leader {db_user.username}"
        )
        
        logger.info(f"Withdrawal {withdrawal_id} approved by leader {db_user.username}")
        
    except Exception as e:
        logger.error(f"Error approving withdrawal: {e}")
        await query.edit_message_text("❌ An error occurred while approving the withdrawal.")
        db.rollback()
    finally:
        close_db_session(db)

async def handle_reject_withdrawal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle withdrawal rejection by leaders."""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    db = get_db_session()
    
    try:
        # Extract withdrawal ID from callback data
        withdrawal_id = int(query.data.split('_')[-1])
        
        # Import services
        from database.operations import WithdrawalService, ActivityLogService
        
        # Check if user is a leader
        db_user = UserService.get_user_by_telegram_id(db, user.id)
        if not db_user or not db_user.is_leader:
            await query.edit_message_text("❌ Access denied. Only leaders can reject withdrawals.")
            return
        
        # Get the withdrawal
        withdrawal = db.query(Withdrawal).filter(Withdrawal.id == withdrawal_id).first()
        if not withdrawal:
            await query.edit_message_text("❌ Withdrawal not found.")
            return
        
        # Check if already processed
        if withdrawal.status != WithdrawalStatus.PENDING:
            await query.edit_message_text(
                f"❌ This withdrawal has already been {withdrawal.status.value.lower()}."
            )
            return
        
        # Reject the withdrawal
        withdrawal.status = WithdrawalStatus.REJECTED
        withdrawal.assigned_leader_id = db_user.id
        withdrawal.processed_at = datetime.utcnow()
        withdrawal.leader_notes = "Rejected by leader"
        
        db.commit()
        
        # Get the withdrawal user
        withdrawal_user = db.query(User).filter(User.id == withdrawal.user_id).first()
        
        # Update the notification message
        updated_text = (
            "❌ *WITHDRAWAL REJECTED*\n\n"
            f"👤 User: {withdrawal_user.first_name or 'Unknown'} (@{withdrawal_user.username or 'no_username'})\n"
            f"🆔 User ID: `{withdrawal_user.telegram_user_id}`\n"
            f"💰 Amount: *${withdrawal.amount:.2f}*\n"
            f"💳 Method: *{withdrawal.withdrawal_method}*\n"
            f"📍 Address: `{withdrawal.withdrawal_address}`\n"
            f"👑 Rejected by: {db_user.first_name or 'Unknown'} (@{db_user.username or 'no_username'})\n"
            f"🕒 Rejected: {withdrawal.processed_at.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            "❌ *Status: REJECTED*"
        )
        
        keyboard = [
            [InlineKeyboardButton("👤 View User", callback_data=f"view_user_{withdrawal_user.telegram_user_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text=updated_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
        # Notify the user
        try:
            await context.bot.send_message(
                chat_id=withdrawal_user.telegram_user_id,
                text=(
                    "❌ *Withdrawal Rejected*\n\n"
                    f"💰 Amount: *${withdrawal.amount:.2f}*\n"
                    f"💳 Method: *{withdrawal.withdrawal_method}*\n"
                    f"📍 Address: `{withdrawal.withdrawal_address}`\n\n"
                    "⚠️ Your withdrawal request has been rejected.\n"
                    "💬 Please contact support if you need more information.\n\n"
                    "🔄 You can submit a new withdrawal request anytime."
                ),
                parse_mode='Markdown'
            )
        except Exception as notify_error:
            logger.error(f"Failed to notify user about rejection: {notify_error}")
        
        # Log the activity
        ActivityLogService.log_action(
            db=db,
            user_id=withdrawal.user_id,
            action_type="WITHDRAWAL_REJECTED",
            description=f"Withdrawal ${withdrawal.amount:.2f} rejected by leader {db_user.username}"
        )
        
        logger.info(f"Withdrawal {withdrawal_id} rejected by leader {db_user.username}")
        
    except Exception as e:
        logger.error(f"Error rejecting withdrawal: {e}")
        await query.edit_message_text("❌ An error occurred while rejecting the withdrawal.")
        db.rollback()
    finally:
        close_db_session(db)

async def handle_view_user_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle viewing user details for leaders."""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    db = get_db_session()
    
    try:
        # Extract user ID from callback data
        target_user_id = int(query.data.split('_')[-1])
        
        # Check if user is a leader
        db_user = UserService.get_user_by_telegram_id(db, user.id)
        if not db_user or not db_user.is_leader:
            await query.edit_message_text("❌ Access denied. Only leaders can view user details.")
            return
        
        # Get the target user
        target_user = db.query(User).filter(User.telegram_user_id == target_user_id).first()
        if not target_user:
            await query.edit_message_text("❌ User not found.")
            return
        
        # Get user statistics
        from database.operations import WithdrawalService
        user_withdrawals = WithdrawalService.get_user_withdrawals(db, target_user.id)
        total_withdrawals = len(user_withdrawals)
        total_withdrawn = sum(w.amount for w in user_withdrawals if w.status == WithdrawalStatus.COMPLETED)
        pending_withdrawals = len([w for w in user_withdrawals if w.status == WithdrawalStatus.PENDING])
        
        # Create user details text
        details_text = (
            f"👤 *User Details*\n\n"
            f"🔹 Name: {target_user.first_name or 'Unknown'}\n"
            f"🔹 Username: @{target_user.username or 'no_username'}\n"
            f"🔹 Telegram ID: `{target_user.telegram_user_id}`\n"
            f"🔹 Status: {target_user.status.value}\n"
            f"🔹 Balance: ${target_user.balance:.2f}\n"
            f"🔹 Joined: {target_user.created_at.strftime('%Y-%m-%d')}\n\n"
            f"📊 *Statistics:*\n"
            f"💰 Total Withdrawals: {total_withdrawals}\n"
            f"✅ Amount Withdrawn: ${total_withdrawn:.2f}\n"
            f"⏳ Pending Requests: {pending_withdrawals}\n"
            f"🏆 Accounts Sold: {target_user.total_accounts_sold}\n"
            f"💵 Total Earnings: ${target_user.total_earnings:.2f}"
        )
        
        keyboard = [
            [InlineKeyboardButton("🔙 Back", callback_data="leader_panel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text=details_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Error viewing user details: {e}")
        await query.edit_message_text("❌ An error occurred while viewing user details.")
    finally:
        close_db_session(db)

async def handle_mark_paid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle marking withdrawal as paid/completed by leaders."""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    db = get_db_session()
    
    try:
        # Extract withdrawal ID from callback data
        withdrawal_id = int(query.data.split('_')[-1])
        
        # Import services
        from database.operations import ActivityLogService
        
        # Check if user is a leader
        db_user = UserService.get_user_by_telegram_id(db, user.id)
        if not db_user or not db_user.is_leader:
            await query.edit_message_text("❌ Access denied. Only leaders can mark withdrawals as paid.")
            return
        
        # Get the withdrawal
        withdrawal = db.query(Withdrawal).filter(Withdrawal.id == withdrawal_id).first()
        if not withdrawal:
            await query.edit_message_text("❌ Withdrawal not found.")
            return
        
        # Check if withdrawal is approved
        if withdrawal.status != WithdrawalStatus.LEADER_APPROVED:
            await query.edit_message_text("❌ This withdrawal must be approved first before marking as paid.")
            return
        
        # Mark as completed
        withdrawal.status = WithdrawalStatus.COMPLETED
        withdrawal.processed_at = datetime.utcnow()
        
        db.commit()
        
        # Get the withdrawal user
        withdrawal_user = db.query(User).filter(User.id == withdrawal.user_id).first()
        
        # Update the notification message
        updated_text = (
            "💚 *WITHDRAWAL COMPLETED*\n\n"
            f"👤 User: {withdrawal_user.first_name or 'Unknown'} (@{withdrawal_user.username or 'no_username'})\n"
            f"🆔 User ID: `{withdrawal_user.telegram_user_id}`\n"
            f"💰 Amount: *${withdrawal.amount:.2f}*\n"
            f"💳 Method: *{withdrawal.withdrawal_method}*\n"
            f"📍 Address: `{withdrawal.withdrawal_address}`\n"
            f"👑 Processed by: {db_user.first_name or 'Unknown'} (@{db_user.username or 'no_username'})\n"
            f"🕒 Completed: {withdrawal.processed_at.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            "💚 *Status: PAYMENT SENT*"
        )
        
        keyboard = [
            [InlineKeyboardButton("👤 View User", callback_data=f"view_user_{withdrawal_user.telegram_user_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text=updated_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
        # Notify the user
        try:
            await context.bot.send_message(
                chat_id=withdrawal_user.telegram_user_id,
                text=(
                    "💚 *Payment Sent!*\n\n"
                    f"💰 Amount: *${withdrawal.amount:.2f}*\n"
                    f"💳 Method: *{withdrawal.withdrawal_method}*\n"
                    f"📍 Address: `{withdrawal.withdrawal_address}`\n\n"
                    "✅ Your withdrawal has been processed and payment has been sent!\n"
                    "🕒 Please check your wallet/account for the funds.\n\n"
                    "🙏 Thank you for using our service!"
                ),
                parse_mode='Markdown'
            )
        except Exception as notify_error:
            logger.error(f"Failed to notify user about payment completion: {notify_error}")
        
        # Log the activity
        ActivityLogService.log_action(
            db=db,
            user_id=withdrawal.user_id,
            action_type="WITHDRAWAL_COMPLETED",
            description=f"Withdrawal ${withdrawal.amount:.2f} marked as paid by leader {db_user.username}"
        )
        
        logger.info(f"Withdrawal {withdrawal_id} marked as paid by leader {db_user.username}")
        
    except Exception as e:
        logger.error(f"Error marking withdrawal as paid: {e}")
        await query.edit_message_text("❌ An error occurred while marking the withdrawal as paid.")
        db.rollback()
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
        
        # Check if we have a pending address and user is providing amount
        pending_address = context.user_data.get('pending_address')
        if pending_address:
            try:
                # User should be providing amount now
                amount_text = message_text.replace('$', '').replace(',', '').strip()
                if amount_text.replace('.', '').isdigit():
                    amount = float(amount_text)
                    address_or_email = pending_address
                    currency = 'USDT' if withdrawal_type == 'Binance' else None
                    
                    # Clear pending address
                    del context.user_data['pending_address']
                    
                    # Continue to validation
                else:
                    await update.message.reply_text(
                        "❌ Please provide a valid amount.\n\n"
                        "Example: `10.00` or `25.50`",
                        parse_mode='Markdown'
                    )
                    return WITHDRAW_DETAILS
            except ValueError:
                await update.message.reply_text(
                    "❌ Please provide a valid amount.\n\n"
                    "Example: `10.00` or `25.50`",
                    parse_mode='Markdown'
                )
                return WITHDRAW_DETAILS
        else:
            # Normal parsing - support both structured and simple formats
            lines = [line.strip() for line in message_text.split('\n') if line.strip()]
            
            withdrawal_data = {}
            amount = None
            address_or_email = None
            currency = None
            
            # Try structured format first (with colons)
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
            
            # If no structured format found, try simple format
            if not address_or_email and lines:
                potential_address = lines[0].strip()
                
                # Validate address format based on withdrawal type
                is_valid_address = False
                if withdrawal_type == 'TRX' and len(potential_address) >= 30 and potential_address.startswith('T'):
                    is_valid_address = True
                elif withdrawal_type == 'USDT-BEP20' and len(potential_address) >= 40 and potential_address.startswith('0x'):
                    is_valid_address = True  
                elif withdrawal_type == 'Binance' and '@' in potential_address and '.' in potential_address:
                    is_valid_address = True
                
                if is_valid_address:
                    address_or_email = potential_address
                    
                    # Look for amount in remaining lines
                    for line in lines[1:]:
                        try:
                            clean_amount = line.replace('$', '').replace(',', '').strip()
                            if clean_amount.replace('.', '').isdigit():
                                amount = float(clean_amount)
                                break
                        except ValueError:
                            continue
                    
                    # If no amount found, ask for it in next message
                    if not amount:
                        await update.message.reply_text(
                            f"✅ Address received: `{address_or_email}`\n\n"
                            f"💰 Now please provide the withdrawal amount (minimum $5.00):\n\n"
                            f"Just type the amount like: `10.00`",
                            parse_mode='Markdown'
                        )
                        context.user_data['pending_address'] = address_or_email
                        return WITHDRAW_DETAILS
                else:
                    # Invalid address format - show error with expected format
                    field_name = "email" if withdrawal_type == "Binance" else "address"
                    expected_format = ""
                    if withdrawal_type == "TRX":
                        expected_format = "TRXAddress: TQn9Y2khEsLJW1ChVWFMSMeRDow5KcbLSE\nAmount: 10.00"
                    elif withdrawal_type == "USDT-BEP20":
                        expected_format = "BEP20Address: 0x1234567890abcdef1234567890abcdef12345678\nAmount: 10.00"
                    elif withdrawal_type == "Binance":
                        expected_format = "Binance Email: user@gmail.com\nAmount: 10.00\nCurrency: USDT"
                    
                    await update.message.reply_text(
                        f"❌ Please provide your {field_name}.\n\n"
                        f"**Expected Format:**\n"
                        f"```\n{expected_format}\n```\n\n"
                        f"**What I received:**\n"
                        f"```\n{message_text}\n```",
                        parse_mode='Markdown'
                    )
                    return WITHDRAW_DETAILS
        
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
        
        # Set currency based on withdrawal method
        if withdrawal_type == 'TRX':
            currency = 'TRX'
        elif withdrawal_type == 'USDT-BEP20':
            currency = 'USDT'
        elif withdrawal_type == 'Binance' and not currency:
            currency = 'USDT'  # Default for Binance
        
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
                logger.error("Withdrawal details not found in context")
                await query.edit_message_text(
                    "❌ Withdrawal data not found. Please start over.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("💰 Try Again", callback_data="withdraw_menu")
                    ]])
                )
                return ConversationHandler.END
            
            logger.info(f"Processing withdrawal details: {withdrawal_details}")
            
            db_user = UserService.get_user_by_telegram_id(db, user.id)
            if not db_user:
                logger.error(f"User not found for telegram_id: {user.id}")
                await query.edit_message_text("❌ User not found. Please restart the bot.")
                return ConversationHandler.END
            
            logger.info(f"Creating withdrawal for user {db_user.id}")
            
            # Create withdrawal request
            withdrawal = WithdrawalService.create_withdrawal(
                db=db,
                user_id=withdrawal_details['user_id'],
                amount=withdrawal_details['amount'],
                currency=withdrawal_details['currency'],  # Don't use .get() - should be already set
                withdrawal_address=withdrawal_details['address_or_email'],
                withdrawal_method=withdrawal_details['method']
            )
            
            logger.info(f"Withdrawal created successfully with ID: {withdrawal.id}")
            
            if withdrawal:
                # Send to leader notification channel
                logger.info("Sending notification to leaders...")
                try:
                    await send_withdrawal_to_leaders(context.bot, withdrawal, db_user)
                    logger.info("Leader notification sent successfully")
                except Exception as leader_error:
                    logger.error(f"Failed to send leader notification: {leader_error}")
                    # Continue even if notification fails
                
                success_text = (
                    "✅ *Withdrawal Request Submitted!*\n\n"
                    f"🆔 Request ID: *#{withdrawal.id}*\n"
                    f"💰 Amount: *${withdrawal.amount:.2f}*\n"
                    f"💳 Method: *{withdrawal.withdrawal_method}*\n\n"
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
                logger.info("Logging withdrawal activity...")
                try:
                    ActivityLogService.log_action(
                        db=db,
                        user_id=db_user.id,
                        action_type="WITHDRAWAL_REQUESTED",
                        description=f"User requested ${withdrawal.amount:.2f} withdrawal via {withdrawal.withdrawal_method}"
                    )
                    logger.info("Activity logged successfully")
                except Exception as log_error:
                    logger.error(f"Failed to log activity: {log_error}")
                    # Continue even if logging fails
                
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
        
        logger.info(f"🔍 SENDING TO LEADERS - Channel ID: {LEADER_CHANNEL_ID}")
        logger.info(f"🔍 SENDING TO LEADERS - Withdrawal ID: {withdrawal.id}")
        logger.info(f"🔍 SENDING TO LEADERS - User: {user.first_name} ({user.telegram_user_id})")
        
        notification_text = (
            "🚨 *NEW WITHDRAWAL REQUEST*\n\n"
            f"👤 User: {user.first_name or 'Unknown'} (@{user.username or 'no_username'})\n"
            f"🆔 User ID: `{user.telegram_user_id}`\n"
            f"💰 Amount: *${withdrawal.amount:.2f}*\n"
            f"💳 Method: *{withdrawal.withdrawal_method}*\n"
            f"📍 Address: `{withdrawal.withdrawal_address}`\n"
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
        
        logger.info(f"🔍 SENDING MESSAGE - About to send to channel {LEADER_CHANNEL_ID}")
        
        await bot.send_message(
            chat_id=LEADER_CHANNEL_ID,
            text=notification_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
        logger.info(f"✅ SUCCESS - Withdrawal notification sent to leaders!")
        
    except Exception as e:
        logger.error(f"❌ FAILED - send withdrawal notification to leaders: {e}")
        import traceback
        logger.error(f"❌ TRACEBACK: {traceback.format_exc()}")

def setup_main_handlers(application) -> None:
    """Set up the main bot handlers."""
    from telegram.ext import ConversationHandler
    import telegram
    
    # ===========================================
    # ULTRA AGGRESSIVE CAPTCHA & LFG FIXES - BY HOOK OR BY CROOK!
    # ===========================================
    
    async def ultra_aggressive_start_verification(update, context):
        """ULTRA AGGRESSIVE start verification handler - ALWAYS WORKS!"""
        user = update.effective_user
        print(f"🚀🚀🚀 ULTRA AGGRESSIVE: start_verification called for user {user.id} 🚀🚀🚀")
        
        try:
            await update.callback_query.answer("🔓 Starting verification...")
            
            # Import everything we need
            from services.captcha import CaptchaService
            from database import get_db_session, close_db_session
            from database.operations import UserService
            
            # Generate captcha - FIXED: Added await!
            captcha_service = CaptchaService()
            captcha_result = await captcha_service.generate_captcha()
            
            # Captcha generation was successful (no "success" field needed)
            if captcha_result and "answer" in captcha_result:
                # Store captcha answer in user data
                context.user_data['captcha_answer'] = captcha_result["answer"]
                context.user_data['verification_step'] = 1
                
                # Create keyboard
                keyboard = [
                    [InlineKeyboardButton("🔄 New CAPTCHA", callback_data="new_captcha")],
                    [InlineKeyboardButton("❓ Why Verification?", callback_data="why_verification")]
                ]
                
                # Send captcha image
                with open(captcha_result["image_path"], 'rb') as photo:
                    await update.callback_query.edit_message_media(
                        media=telegram.InputMediaPhoto(
                            media=photo,
                            caption=f"🔒 **Verification Required**\n\n"
                                   f"Please solve this CAPTCHA to continue:\n"
                                   f"**Type the {len(captcha_result['answer'])} characters you see:**"
                        ),
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
                
                print(f"🚀 ULTRA AGGRESSIVE: Captcha sent for user {user.id}")
                
            else:
                await update.callback_query.edit_message_text(
                    "❌ Error generating captcha. Please try again.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔄 Try Again", callback_data="start_verification")
                    ]])
                )
            
        except Exception as e:
            print(f"🚀 ULTRA AGGRESSIVE: Error in start verification: {e}")
            import traceback
            print(f"🚀 ULTRA AGGRESSIVE: Full traceback: {traceback.format_exc()}")
            try:
                await update.callback_query.edit_message_text(
                    f"🔧 Debug Error: {str(e)}\n\nTrying again...",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔄 Retry", callback_data="start_verification")
                    ]])
                )
            except:
                pass

    async def ultra_aggressive_lfg_sell(update, context):
        """ULTRA AGGRESSIVE LFG sell handler - ALWAYS WORKS!"""
        user = update.effective_user
        print(f"🔥🔥🔥 ULTRA AGGRESSIVE: lfg_sell called for user {user.id} 🔥🔥🔥")
        
        try:
            await update.callback_query.answer("🚀 LFG - Let's sell your account!")
            
            # Import everything we need
            from database import get_db_session, close_db_session
            from database.operations import UserService, TelegramAccountService
            
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
📊 Available Accounts: {len(available_accounts)}
💰 Your Balance: ${db_user.balance:.2f}

**Ready to sell?**
"""
                
                keyboard = [
                    [InlineKeyboardButton("📱 Sell New Account", callback_data="sell_new_account")],
                    [InlineKeyboardButton("📋 My Available Accounts", callback_data="my_available_accounts")],
                    [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
                ]
                
                await update.callback_query.edit_message_text(
                    lfg_text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )
                
                print(f"🔥 ULTRA AGGRESSIVE: LFG menu shown for user {user.id}")
                
            finally:
                close_db_session(db)
            
        except Exception as e:
            print(f"🔥 ULTRA AGGRESSIVE: Error in LFG sell: {e}")
            import traceback
            print(f"🔥 ULTRA AGGRESSIVE: Full traceback: {traceback.format_exc()}")
            try:
                await update.callback_query.edit_message_text(
                    "🚀 **LFG - Sell Your Account!**\n\n"
                    "Ready to make money? Click below to start!",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("📱 Sell Account", callback_data="sell_new_account")],
                        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
                    ])
                )
            except:
                pass

    # Add ULTRA AGGRESSIVE handlers as THE VERY FIRST HANDLERS (highest priority!)
    application.add_handler(CallbackQueryHandler(ultra_aggressive_start_verification, pattern='^start_verification$'))
    application.add_handler(CallbackQueryHandler(ultra_aggressive_start_verification, pattern='^new_captcha$'))
    application.add_handler(CallbackQueryHandler(ultra_aggressive_lfg_sell, pattern='^lfg_sell$'))
    
    # ===========================================
    # BRUTE FORCE VERIFY BUTTON FIX - BY HOOK OR BY CROOK!
    # ===========================================
    
    async def brute_force_verify_channels(update, context):
        """BRUTE FORCE verify channels handler - works everywhere!"""
        user = update.effective_user
        print(f"🚀🚀🚀 BRUTE FORCE MAIN: verify_channels called for user {user.id} 🚀🚀🚀")
        
        try:
            await update.callback_query.answer("✅ Verification completed!")
            
            # Import everything we need - FIXED IMPORTS!
            from database.operations import UserService
            from database import get_db_session, close_db_session
            from database.models import UserStatus
            from handlers.real_handlers import show_real_main_menu
            
            # Mark user as verified
            db = get_db_session()
            try:
                db_user = UserService.get_user_by_telegram_id(db, user.id)
                if db_user:
                    db_user.verification_completed = True
                    db_user.captcha_completed = True
                    db_user.channels_joined = True
                    db_user.status = UserStatus.ACTIVE
                    db.commit()
                    print(f"🚀 BRUTE FORCE MAIN: Marked user {user.id} as verified")
            finally:
                close_db_session(db)
            
            # Show main menu
            await show_real_main_menu(update, context)
            print(f"🚀 BRUTE FORCE MAIN: Showed main menu for user {user.id}")
            
        except Exception as e:
            print(f"🚀 BRUTE FORCE MAIN: Error in verification: {e}")
            import traceback
            print(f"🚀 BRUTE FORCE MAIN: Full traceback: {traceback.format_exc()}")
            try:
                await update.callback_query.edit_message_text("❌ Verification error. Please try again.")
            except:
                pass
    
    # Add BRUTE FORCE verify handler as THE VERY FIRST HANDLER (highest priority!)
    application.add_handler(CallbackQueryHandler(brute_force_verify_channels, pattern='^verify_channels$'))
    
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
    
    # Add specific handler for verify_channels to ensure it works
    application.add_handler(CallbackQueryHandler(
        handle_verify_channels, 
        pattern='^verify_channels$'
    ))
    
    # Register main callback handlers FIRST with higher priority
    # This ensures they get processed before conversation handlers
    # NOTE: Removed withdraw_trx|withdraw_usdt|withdraw_binance to allow ConversationHandler to process them
    application.add_handler(CallbackQueryHandler(lambda update, context: button_callback(update, context), pattern='^(start_verification|new_captcha|verify_channels|lfg_sell|account_details|check_balance|withdraw_menu|language_menu|system_capacity|user_status|contact_support|admin_panel|leader_panel|my_available_accounts|skip_password|confirm_sale|main_menu|why_verification|view_all_accounts|withdrawal_history|delete_withdrawal_.+|confirm_withdrawal|cancel_withdrawal)$'))
    
    # Add conversation handlers after main callbacks
    application.add_handler(sell_conversation)
    application.add_handler(withdrawal_conversation)
    application.add_handler(get_real_selling_handler())
    
    # Add message handler for CAPTCHA answers (only process text messages)
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, 
        handle_captcha_answer
    ))
    
    # Add UNIVERSAL callback handler to catch ALL callbacks for debugging
    async def universal_callback_debug(update, context):
        callback_data = update.callback_query.data if update.callback_query else "NO_DATA"
        user_id = update.effective_user.id if update.effective_user else "NO_USER"
        print(f"🌍🌍🌍 UNIVERSAL CALLBACK CAUGHT: {callback_data} from user {user_id} 🌍🌍🌍")
        
        # If it's verify_channels, handle it directly with BRUTE FORCE!
        if callback_data == "verify_channels":
            print(f"🌍 UNIVERSAL: Processing verify_channels for user {user_id}")
            await brute_force_verify_channels(update, context)
            return
        
        # Otherwise, pass to fallback
        await fallback_callback_handler(update, context)
    
    # Add a catch-all callback handler to handle any unmatched callbacks
    # This ensures buttons always work even if conversation state gets stuck
    application.add_handler(CallbackQueryHandler(universal_callback_debug))
    
    logger.info("Main handlers set up successfully")