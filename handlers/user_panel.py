"""
User Panel Handlers
Handles user-facing menu options: balance, account details, language, help sections
"""
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import get_db_session, close_db_session
from database.operations import UserService, TelegramAccountService
from database.models import Withdrawal, WithdrawalStatus, User
from services.translation_service import translation_service

logger = logging.getLogger(__name__)


def get_status_emoji(status: str) -> str:
    """Get emoji for user status."""
    status_emojis = {
        "ACTIVE": "✅",
        "FROZEN": "❄️",
        "BANNED": "🚫",
        "PENDING": "⏳"
    }
    return status_emojis.get(status, "❓")


async def handle_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user's balance and recent transactions."""
    user = update.effective_user
    db = get_db_session()
    
    try:
        db_user = UserService.get_user_by_telegram_id(db, user.id)
        
        if not db_user:
            await update.callback_query.edit_message_text("❌ User not found.")
            return
        
        # Get recent withdrawals
        withdrawals = db.query(Withdrawal).filter(
            Withdrawal.user_id == db_user.id
        ).order_by(Withdrawal.created_at.desc()).limit(5).all()
        
        balance_text = f"""
💳 **Your Balance**

**Current Balance:** `${db_user.balance:.2f}`
**Total Earnings:** `${db_user.total_earnings:.2f}`
**Total Withdrawn:** `${db_user.total_withdrawn:.2f}`

**Account Statistics:**
• Total Accounts Sold: {db_user.total_accounts_sold}
• Average Earning per Account: `${(db_user.total_earnings / max(db_user.total_accounts_sold, 1)):.2f}`

**Recent Transactions:**
"""
        
        if withdrawals:
            for w in withdrawals:
                status_icon = "✅" if w.status == WithdrawalStatus.COMPLETED else "⏳"
                balance_text += f"\n{status_icon} Withdrawal: `${w.amount:.2f}` - {w.created_at.strftime('%b %d')}"
        else:
            balance_text += "\n_No recent transactions_"
        
        keyboard = [
            [InlineKeyboardButton("💸 Withdraw Funds", callback_data="withdraw")],
            [InlineKeyboardButton("← Back to Menu", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            balance_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    except Exception as e:
        logger.error(f"Error in handle_balance: {e}")
        await update.callback_query.edit_message_text("❌ Error loading balance.")
    
    finally:
        close_db_session(db)


async def handle_sales_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user's account sales history."""
    user = update.effective_user
    db = get_db_session()
    
    try:
        db_user = UserService.get_user_by_telegram_id(db, user.id)
        accounts = TelegramAccountService.get_user_accounts(db, db_user.id)
        
        sold_accounts = [a for a in accounts if a.status.value == 'SOLD']
        
        history_text = f"""
📊 **Sales History**

**Total Sales:** {len(sold_accounts)} accounts
**Total Earned:** `${db_user.total_earnings:.2f}`
**Success Rate:** {((len(sold_accounts) / max(len(accounts), 1)) * 100):.1f}%

**Recent Sales:**
"""
        
        if sold_accounts:
            recent_sold = sorted(sold_accounts, key=lambda x: x.sold_at or datetime.min, reverse=True)[:5]
            for acc in recent_sold:
                sale_date = acc.sold_at.strftime('%b %d') if acc.sold_at else "N/A"
                history_text += f"\n• +{acc.phone_number} - ${acc.sale_price:.2f} - {sale_date}"
        else:
            history_text += "\n_No sales yet. Start selling to see your history!_"
        
        keyboard = [
            [InlineKeyboardButton("📱 Sell Account", callback_data="start_real_selling")],
            [InlineKeyboardButton("← Back to Menu", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            history_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    except Exception as e:
        logger.error(f"Error in handle_sales_history: {e}")
        await update.callback_query.edit_message_text("❌ Error loading sales history.")
    
    finally:
        close_db_session(db)


async def handle_account_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user's account details and statistics."""
    user = update.effective_user
    db = get_db_session()
    
    # Get user's language preference
    user_lang = translation_service.get_user_language(context)
    
    try:
        db_user = UserService.get_user_by_telegram_id(db, user.id)
        accounts = TelegramAccountService.get_user_accounts(db, db_user.id)
        
        details_text = f"""
{translation_service.get_text('account_details_title', user_lang)}

{translation_service.get_text('user_information', user_lang)}
{translation_service.get_text('name_label', user_lang)} {user.first_name or 'N/A'} {user.last_name or ''}
{translation_service.get_text('username_label', user_lang)} @{user.username or translation_service.get_text('no_username', user_lang)}
{translation_service.get_text('user_id_label', user_lang)} `{user.id}`
{translation_service.get_text('member_since_label', user_lang)} {db_user.created_at.strftime('%Y-%m-%d')}

{translation_service.get_text('account_statistics', user_lang)}
{translation_service.get_text('total_accounts', user_lang)} {len(accounts)}
{translation_service.get_text('available_to_sell', user_lang)} {len([a for a in accounts if a.status.value == 'AVAILABLE'])}
{translation_service.get_text('already_sold', user_lang)} {len([a for a in accounts if a.status.value == 'SOLD'])}
{translation_service.get_text('on_hold', user_lang)} {len([a for a in accounts if a.status.value == '24_HOUR_HOLD'])}

{translation_service.get_text('financial_summary', user_lang)}
{translation_service.get_text('current_balance', user_lang)} `${db_user.balance:.2f}`
{translation_service.get_text('total_sold', user_lang)} {db_user.total_accounts_sold} accounts
{translation_service.get_text('total_earnings', user_lang)} `${db_user.total_earnings:.2f}`
{translation_service.get_text('average_per_account', user_lang)} `${(db_user.total_earnings / max(db_user.total_accounts_sold, 1)):.2f}`

{translation_service.get_text('performance', user_lang)}
{translation_service.get_text('success_rate', user_lang)} {((db_user.total_accounts_sold / max(len(accounts), 1)) * 100):.1f}%
{translation_service.get_text('status_label', user_lang)} {get_status_emoji(db_user.status.value)} {db_user.status.value}
        """
        
        keyboard = [
            [InlineKeyboardButton(translation_service.get_text('view_all_accounts', user_lang), callback_data="view_all_accounts")],
            [InlineKeyboardButton(translation_service.get_text('withdrawal_history', user_lang), callback_data="withdrawal_history")],
            [InlineKeyboardButton(translation_service.get_text('back_menu', user_lang), callback_data="main_menu")]
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
            translation_service.get_text('error_loading', user_lang)
        )
    finally:
        close_db_session(db)


async def handle_language_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show language selection menu."""
    # Get user's current language
    user_lang = translation_service.get_user_language(context)
    
    language_text = f"""
{translation_service.get_text('language_title', user_lang)}

{translation_service.get_text('choose_language', user_lang)}

{translation_service.get_text('available_languages', user_lang)}
• 🇺🇸 English
• 🇪🇸 Español  
• 🇫🇷 Français
• 🇩🇪 Deutsch
• 🇷🇺 Русский
• 🇨🇳 中文
• 🇮🇳 हिंदी
• 🇦🇪 العربية

{translation_service.get_text('language_applied', user_lang)}
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
        [InlineKeyboardButton(translation_service.get_text('back_menu', user_lang), callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        language_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )


async def handle_language_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle individual language selection."""
    query = update.callback_query
    data = query.data
    
    # Language mapping
    languages = {
        'lang_en': ('🇺🇸 English', 'en'),
        'lang_es': ('🇪🇸 Español', 'es'), 
        'lang_fr': ('🇫🇷 Français', 'fr'),
        'lang_de': ('🇩🇪 Deutsch', 'de'),
        'lang_ru': ('🇷🇺 Русский', 'ru'),
        'lang_zh': ('🇨🇳 中文', 'zh'),
        'lang_hi': ('🇮🇳 हिंदी', 'hi'),
        'lang_ar': ('🇦🇪 العربية', 'ar')
    }
    
    if data in languages:
        lang_name, lang_code = languages[data]
        
        # Save language preference in context
        translation_service.set_user_language(context, lang_code)

        # Persist language preference in the database
        db = get_db_session()
        try:
            user = UserService.get_user_by_telegram_id(db, update.effective_user.id)
            if user:
                user.language_code = lang_code
                db.commit()
        except Exception as e:
            logger.error(f"Error saving language preference: {e}")
        finally:
            close_db_session(db)        # Get localized success message
        success_text = f"""
{translation_service.get_text('language_updated', lang_code)}

{translation_service.get_text('language_changed_to', lang_code)} {lang_name}

{translation_service.get_text('language_active', lang_code)} {lang_name}.

🔄 **Interface has been updated to your selected language.**
        """
        
        keyboard = [
            [InlineKeyboardButton(translation_service.get_text('main_menu', lang_code), callback_data="main_menu")],
            [InlineKeyboardButton(translation_service.get_text('change_language', lang_code), callback_data="language_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            success_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    else:
        await query.answer(translation_service.get_text('invalid_selection', translation_service.get_user_language(context)))


async def show_how_it_works(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show detailed explanation of how the platform works."""
    how_text = """
🔬 **How Real Account Selling Works**

**1. Real OTP Sending**
• We use Telethon (official Telegram library)
• Connect to real Telegram API
• Send actual verification codes via SMS/Telegram

**2. Real Account Login**
• Actually login to your Telegram account
• Real session creation using your credentials
• Full access to account settings

**3. Real Modifications**
• Actually change your name, username
• Really set new profile settings
• Actually configure new 2FA password

**4. Real Ownership Transfer**
• Terminate all your sessions
• New owner gets fresh credentials
• You completely lose access

**⚠️ This is 100% REAL - not a simulation!**
    """
    
    keyboard = [
        [InlineKeyboardButton("✅ I Understand", callback_data="start_real_selling")],
        [InlineKeyboardButton("← Back to Menu", callback_data="main_menu")]
    ]
    
    await update.callback_query.edit_message_text(
        how_text,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def show_2fa_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show instructions for disabling 2FA."""
    help_text = """
🆘 **How to Disable 2FA**

**Step-by-step:**

1. **Open Telegram App**
2. **Tap Settings** (⚙️)
3. **Tap Privacy and Security**
4. **Tap Two-Step Verification**
5. **Tap Turn Off**
6. **Enter your current 2FA password**
7. **Confirm disable**

**✅ You'll see "Two-Step Verification is off"**

Then come back and click "I Disabled 2FA"!
    """
    
    keyboard = [
        [InlineKeyboardButton("✅ I Disabled 2FA", callback_data="2fa_disabled")],
        [InlineKeyboardButton("← Back to Menu", callback_data="main_menu")]
    ]
    
    await update.callback_query.edit_message_text(
        help_text,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
