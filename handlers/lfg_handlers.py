"""
LFG (Let's F***ing Go) flow handlers for account creation.
"""
import os
import logging
import asyncio
from typing import Dict, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    ContextTypes, CommandHandler, MessageHandler, ConversationHandler, 
    CallbackQueryHandler, filters
)
from database import get_db_session, close_db_session
from database.operations import UserService, AccountService
from services.telethon_manager import telethon_manager
from services.proxy_manager import proxy_manager
from utils.helpers import CaptchaUtils, PhoneUtils, SecurityUtils
from utils.helpers import MessageUtils, get_session_file_path

logger = logging.getLogger(__name__)

# Conversation states
(CAPTCHA_VERIFICATION, PHONE_INPUT, CODE_INPUT, 
 PASSWORD_INPUT, ACCOUNT_SETUP) = range(5)

async def start_lfg_flow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the LFG (account creation) flow."""
    user = update.effective_user
    
    # Clear any existing conversation data
    context.user_data.clear()
    
    # Generate captcha
    question, answer = CaptchaUtils.generate_math_captcha()
    context.user_data['captcha_answer'] = answer
    context.user_data['captcha_attempts'] = 0
    
    welcome_text = f"""
🚀 **Let's Get Started! (LFG)**

Welcome to the account setup process! We'll help you add a new Telegram account securely.

**Step 1: Security Verification** 🛡️

To ensure security, please solve this simple captcha:

❓ **Question:** {question}

**Please enter your answer:**
    """
    
    keyboard = [
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel_lfg")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            welcome_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            welcome_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    logger.info(f"LFG flow started for user {user.id}")
    return CAPTCHA_VERIFICATION

async def handle_captcha(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle captcha verification."""
    user = update.effective_user
    user_answer = update.message.text.strip()
    
    # Check attempts
    context.user_data['captcha_attempts'] += 1
    
    try:
        correct_answer = context.user_data.get('captcha_answer')
        
        if str(user_answer) == str(correct_answer):
            # Captcha correct, proceed to phone input
            phone_text = """
✅ **Captcha Verified Successfully!**

**Step 2: Phone Number** 📱

Please enter the phone number for the Telegram account you want to add.

**Format:** International format with country code
**Example:** +1234567890

**Important Notes:**
• Each phone number can only be used once
• Make sure you have access to this number for SMS/calls
• The number will be used for verification

**Enter your phone number:**
            """
            
            keyboard = [
                [KeyboardButton("📱 Share My Contact", request_contact=True)],
                [InlineKeyboardButton("❌ Cancel", callback_data="cancel_lfg")]
            ]
            reply_markup = ReplyKeyboardMarkup(
                [[keyboard[0][0]]], 
                one_time_keyboard=True, 
                resize_keyboard=True
            )
            
            await update.message.reply_text(
                phone_text,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            
            logger.info(f"Captcha verified for user {user.id}")
            return PHONE_INPUT
            
        else:
            # Captcha incorrect
            if context.user_data['captcha_attempts'] >= 3:
                await update.message.reply_text(
                    "❌ **Too many failed attempts!**\n\n"
                    "Please try again later or contact support if you need help.\n\n"
                    "Use /lfg to start over."
                )
                return ConversationHandler.END
            
            # Generate new captcha
            question, answer = CaptchaUtils.generate_math_captcha()
            context.user_data['captcha_answer'] = answer
            
            await update.message.reply_text(
                f"❌ **Incorrect answer!**\n\n"
                f"Attempts remaining: {3 - context.user_data['captcha_attempts']}\n\n"
                f"**New question:** {question}\n\n"
                f"Please try again:"
            )
            
            return CAPTCHA_VERIFICATION
            
    except Exception as e:
        logger.error(f"Error in captcha verification: {e}")
        await update.message.reply_text(
            "❌ An error occurred. Please try again with /lfg"
        )
        return ConversationHandler.END

async def handle_phone_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle phone number input."""
    user = update.effective_user
    
    # Get phone number from message or contact
    if update.message.contact:
        phone_number = update.message.contact.phone_number
        if not phone_number.startswith('+'):
            phone_number = '+' + phone_number
    else:
        phone_number = update.message.text.strip()
    
    # Validate phone number
    is_valid, formatted_phone = PhoneUtils.validate_phone_number(phone_number)
    
    if not is_valid:
        await update.message.reply_text(
            "❌ **Invalid phone number format!**\n\n"
            "Please enter a valid international phone number:\n"
            "• Include country code (e.g., +1, +44, +49)\n"
            "• Use correct format: +1234567890\n\n"
            "**Try again:**",
            reply_markup=ReplyKeyboardMarkup(
                [[KeyboardButton("📱 Share My Contact", request_contact=True)]],
                one_time_keyboard=True,
                resize_keyboard=True
            )
        )
        return PHONE_INPUT
    
    # Check if phone number already exists
    db = get_db_session()
    try:
        existing_account = AccountService.get_account_by_phone(db, formatted_phone)
        
        if existing_account:
            if existing_account.status == 'ACTIVE':
                await update.message.reply_text(
                    f"❌ **Phone number already registered!**\n\n"
                    f"The number `{formatted_phone}` is already associated with an active account.\n\n"
                    f"📋 **Account Status:** {existing_account.status}\n"
                    f"📅 **Registered:** {existing_account.created_at.strftime('%Y-%m-%d')}\n\n"
                    f"If this is your account and you're having issues, please contact support."
                )
                return ConversationHandler.END
            else:
                # Account exists but not active - put on hold
                AccountService.update_account_status(db, existing_account.id, '24_HOUR_HOLD')
                
                # Notify admin
                admin_chat_id = os.getenv('ADMIN_CHAT_ID')
                if admin_chat_id:
                    try:
                        await context.bot.send_message(
                            chat_id=admin_chat_id,
                            text=f"⚠️ **Duplicate Login Attempt**\n\n"
                                 f"📱 Phone: `{formatted_phone}`\n"
                                 f"👤 User: {user.id} (@{user.username or 'N/A'})\n"
                                 f"📊 Existing Status: {existing_account.status}\n"
                                 f"🔒 Action: Set to 24_HOUR_HOLD",
                            parse_mode='Markdown'
                        )
                    except Exception as e:
                        logger.warning(f"Failed to notify admin: {e}")
                
                await update.message.reply_text(
                    "⚠️ **Account Conflict Detected**\n\n"
                    "This phone number has an existing registration with a different status.\n"
                    "The account has been placed on a 24-hour hold for security review.\n\n"
                    "An admin has been notified and will review the situation.\n\n"
                    "Please contact support if you need immediate assistance."
                )
                return ConversationHandler.END
        
        # Store phone number and proceed
        context.user_data['phone_number'] = formatted_phone
        context.user_data['country_code'] = PhoneUtils.get_country_code(formatted_phone)
        
        # Create Telethon client with proxy
        loading_message = await update.message.reply_text(
            "🔄 **Setting up secure connection...**\n\n"
            "Please wait while we:\n"
            "• Assign a unique proxy\n"
            "• Establish secure connection\n"
            "• Prepare for verification",
            parse_mode='Markdown'
        )
        
        client, proxy_config = await telethon_manager.create_client_with_proxy(formatted_phone)
        
        if not client:
            await loading_message.edit_text(
                "❌ **Connection Failed**\n\n"
                "Unable to establish a secure connection.\n"
                "This might be due to:\n"
                "• Network issues\n"
                "• Proxy unavailability\n\n"
                "Please try again later or contact support."
            )
            return ConversationHandler.END
        
        # Send code request
        try:
            phone_code_hash = await telethon_manager.send_code_request(client, formatted_phone)
            
            if not phone_code_hash:
                await loading_message.edit_text(
                    "❌ **Code Request Failed**\n\n"
                    "Unable to send verification code.\n"
                    "Please check:\n"
                    "• Phone number is correct\n"
                    "• Number can receive SMS/calls\n"
                    "• Try again in a few minutes"
                )
                await telethon_manager.disconnect_client(formatted_phone)
                return ConversationHandler.END
            
            # Store session data
            context.user_data['phone_code_hash'] = phone_code_hash
            context.user_data['proxy_config'] = proxy_manager.get_proxy_json(proxy_config) if proxy_config else ""
            
            await loading_message.edit_text(
                f"✅ **Code Sent Successfully!**\n\n"
                f"📱 **Phone:** `{formatted_phone}`\n"
                f"🌍 **Country:** {context.user_data.get('country_code', 'Unknown')}\n"
                f"🔐 **Proxy:** {'✅ Secured' if proxy_config else '❌ Direct'}\n\n"
                f"📨 **A verification code has been sent to your phone.**\n\n"
                f"**Step 3: Enter the code you received**\n"
                f"Format: Just the numbers (e.g., 12345)",
                parse_mode='Markdown'
            )
            
            logger.info(f"Code sent successfully for {formatted_phone}")
            return CODE_INPUT
            
        except Exception as e:
            logger.error(f"Error sending code: {e}")
            await loading_message.edit_text(
                "❌ **Error sending verification code**\n\n"
                "Please try again or contact support if the problem persists."
            )
            await telethon_manager.disconnect_client(formatted_phone)
            return ConversationHandler.END
    
    except Exception as e:
        logger.error(f"Error in phone input: {e}")
        await update.message.reply_text(
            "❌ An error occurred. Please try again with /lfg"
        )
        return ConversationHandler.END
    finally:
        close_db_session(db)

async def handle_code_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle verification code input."""
    user = update.effective_user
    code = update.message.text.strip()
    
    # Validate code format (should be numbers only)
    if not code.isdigit() or len(code) < 4:
        await update.message.reply_text(
            "❌ **Invalid code format!**\n\n"
            "Please enter only the numbers from the code you received.\n"
            "Example: 12345\n\n"
            "**Enter the verification code:**"
        )
        return CODE_INPUT
    
    phone_number = context.user_data.get('phone_number')
    phone_code_hash = context.user_data.get('phone_code_hash')
    
    if not phone_number or not phone_code_hash:
        await update.message.reply_text(
            "❌ Session expired. Please start over with /lfg"
        )
        return ConversationHandler.END
    
    # Get the client
    client = telethon_manager.get_client(phone_number)
    if not client:
        await update.message.reply_text(
            "❌ Connection lost. Please start over with /lfg"
        )
        return ConversationHandler.END
    
    loading_message = await update.message.reply_text(
        "🔄 **Verifying code...**\n\n"
        "Please wait while we verify your code and establish the session."
    )
    
    try:
        # Attempt to sign in with code
        success, error_msg = await telethon_manager.sign_in_with_code(
            client, phone_number, code, phone_code_hash
        )
        
        if success:
            # Login successful, proceed to account setup
            await loading_message.edit_text(
                "✅ **Login Successful!**\n\n"
                "🔄 Setting up your account security...\n"
                "• Retrieving account information\n"
                "• Setting up 2FA protection\n"
                "• Configuring security settings"
            )
            
            # Get account info
            account_info = await telethon_manager.get_account_info(client)
            if account_info:
                context.user_data['account_info'] = account_info
            
            return await setup_account_security(update, context, client, loading_message)
            
        elif error_msg == "2FA_REQUIRED":
            # 2FA password required
            await loading_message.edit_text(
                "🔐 **2FA Password Required**\n\n"
                "This account has two-factor authentication enabled.\n\n"
                "**Please enter your 2FA password:**"
            )
            return PASSWORD_INPUT
            
        elif error_msg == "INVALID_CODE":
            await loading_message.edit_text(
                "❌ **Invalid Code**\n\n"
                "The verification code you entered is incorrect.\n\n"
                "Please check:\n"
                "• Code was entered correctly\n"
                "• Code hasn't expired\n"
                "• You're using the latest code received\n\n"
                "**Enter the correct code:**"
            )
            return CODE_INPUT
            
        else:
            await loading_message.edit_text(
                f"❌ **Login Failed**\n\n"
                f"Error: {error_msg}\n\n"
                f"Please try again or contact support if the problem persists."
            )
            await telethon_manager.disconnect_client(phone_number)
            return ConversationHandler.END
    
    except Exception as e:
        logger.error(f"Error in code verification: {e}")
        await loading_message.edit_text(
            "❌ **Verification Error**\n\n"
            "An error occurred during code verification.\n"
            "Please try again or contact support."
        )
        await telethon_manager.disconnect_client(phone_number)
        return ConversationHandler.END

async def handle_password_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle 2FA password input."""
    user = update.effective_user
    password = update.message.text
    phone_number = context.user_data.get('phone_number')
    
    if not phone_number:
        await update.message.reply_text(
            "❌ Session expired. Please start over with /lfg"
        )
        return ConversationHandler.END
    
    client = telethon_manager.get_client(phone_number)
    if not client:
        await update.message.reply_text(
            "❌ Connection lost. Please start over with /lfg"
        )
        return ConversationHandler.END
    
    loading_message = await update.message.reply_text(
        "🔄 **Verifying 2FA password...**"
    )
    
    try:
        success = await telethon_manager.sign_in_with_password(client, password)
        
        if success:
            await loading_message.edit_text(
                "✅ **2FA Verified Successfully!**\n\n"
                "🔄 Setting up account security..."
            )
            
            # Get account info
            account_info = await telethon_manager.get_account_info(client)
            if account_info:
                context.user_data['account_info'] = account_info
            
            return await setup_account_security(update, context, client, loading_message)
            
        else:
            await loading_message.edit_text(
                "❌ **Invalid 2FA Password**\n\n"
                "The password you entered is incorrect.\n\n"
                "**Please try again:**"
            )
            return PASSWORD_INPUT
    
    except Exception as e:
        logger.error(f"Error in password verification: {e}")
        await loading_message.edit_text(
            "❌ **2FA Verification Error**\n\n"
            "An error occurred during password verification.\n"
            "Please try again or contact support."
        )
        return PASSWORD_INPUT

async def setup_account_security(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                client, loading_message) -> int:
    """Set up account security (2FA, logout other sessions, etc.)."""
    user = update.effective_user
    phone_number = context.user_data.get('phone_number')
    account_info = context.user_data.get('account_info', {})
    
    try:
        # Step 1: Set up 2FA if not already enabled
        await loading_message.edit_text(
            "🔐 **Setting up 2FA protection...**\n\n"
            "This may take a moment..."
        )
        
        twofa_password = await telethon_manager.setup_2fa(client)
        twofa_enabled = twofa_password is not None
        
        # Step 2: Logout other sessions
        await loading_message.edit_text(
            "🔒 **Securing session...**\n\n"
            "Logging out from other devices for security..."
        )
        
        logout_success = await telethon_manager.logout_other_sessions(client)
        
        # Step 3: Save to database
        await loading_message.edit_text(
            "💾 **Saving account data...**\n\n"
            "Almost done!"
        )
        
        db = get_db_session()
        try:
            # Get or create user
            db_user = UserService.get_or_create_user(
                db=db,
                telegram_user_id=user.id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name
            )
            
            # Create account record
            session_file_path = get_session_file_path(phone_number)
            
            account = AccountService.create_account(
                db=db,
                user_id=db_user.id,
                phone_number=phone_number,
                session_file_path=session_file_path,
                country_code=context.user_data.get('country_code'),
                proxy_config=context.user_data.get('proxy_config', "")
            )
            
            # Update account with details
            if account_info:
                AccountService.update_account_details(
                    db=db,
                    account_id=account.id,
                    telegram_user_id=account_info.get('user_id'),
                    username=account_info.get('username'),
                    first_name=account_info.get('first_name'),
                    last_name=account_info.get('last_name')
                )
            
            # Enable 2FA if password was set
            if twofa_enabled and twofa_password:
                password_hash = SecurityUtils.hash_password(twofa_password)
                AccountService.enable_2fa(db, account.id, password_hash)
            
            # Mark logout other sessions
            if logout_success:
                AccountService.update_account_details(
                    db=db,
                    account_id=account.id,
                    logout_other_sessions=True
                )
            
            # Update balance (example: 10 credits for successful setup)
            UserService.update_user_balance(db, db_user.id, 10.0)
            
            # Success message
            success_text = f"""
🎉 **Account Setup Complete!**

✅ **Account successfully added and secured!**

📱 **Account Details:**
• Phone: `{phone_number}`
• Country: {context.user_data.get('country_code', 'Unknown')}
• User ID: {account_info.get('user_id', 'N/A')}
• Username: @{account_info.get('username') or 'Not set'}

🔐 **Security Features:**
• 2FA Protection: {'✅ Enabled' if twofa_enabled else '⚠️ Failed to enable'}
• Session Security: {'✅ Other sessions logged out' if logout_success else '⚠️ Warning: Other sessions active'}
• Proxy Protection: {'✅ Enabled' if context.user_data.get('proxy_config') else '❌ Direct connection'}

💰 **Welcome Bonus:** +10 credits added to your balance!

**What's Next?**
• Your account is now active and earning
• Check `/balance` to see your earnings
• Use `/accounts` to manage your accounts
• Use `/withdraw` when ready to cash out

**Important:** Keep your login credentials safe and don't share them with anyone!
            """
            
            keyboard = [
                [InlineKeyboardButton("💰 Check Balance", callback_data="check_balance")],
                [InlineKeyboardButton("📱 My Accounts", callback_data="my_accounts")],
                [InlineKeyboardButton("➕ Add Another Account", callback_data="start_lfg")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await loading_message.edit_text(
                success_text,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            
            logger.info(f"Account setup completed for user {user.id}, phone {phone_number}")
            
            # Disconnect client
            await telethon_manager.disconnect_client(phone_number)
            
            return ConversationHandler.END
            
        except Exception as e:
            logger.error(f"Database error during account creation: {e}")
            await loading_message.edit_text(
                "❌ **Database Error**\n\n"
                "Account was logged in successfully but there was an error saving to database.\n"
                "Please contact support with this error."
            )
            return ConversationHandler.END
        finally:
            close_db_session(db)
    
    except Exception as e:
        logger.error(f"Error in account security setup: {e}")
        await loading_message.edit_text(
            "❌ **Security Setup Error**\n\n"
            "There was an error setting up account security.\n"
            "The account may still be functional but please contact support."
        )
        return ConversationHandler.END

async def cancel_lfg(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the LFG flow."""
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text(
            "❌ **Account setup cancelled.**\n\n"
            "No worries! You can start again anytime with /lfg\n\n"
            "Need help? Use /help or /support"
        )
    
    # Clean up any active connections
    phone_number = context.user_data.get('phone_number')
    if phone_number:
        await telethon_manager.disconnect_client(phone_number)
    
    context.user_data.clear()
    return ConversationHandler.END

def setup_lfg_handlers(application) -> None:
    """Set up LFG conversation handlers."""
    
    lfg_handler = ConversationHandler(
        entry_points=[
            CommandHandler("lfg", start_lfg_flow),
            CallbackQueryHandler(start_lfg_flow, pattern="^start_lfg$")
        ],
        states={
            CAPTCHA_VERIFICATION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_captcha)
            ],
            PHONE_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_phone_input),
                MessageHandler(filters.CONTACT, handle_phone_input)
            ],
            CODE_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_code_input)
            ],
            PASSWORD_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_password_input)
            ]
        },
        fallbacks=[
            CallbackQueryHandler(cancel_lfg, pattern="^cancel_lfg$"),
            CommandHandler("cancel", cancel_lfg)
        ],
        allow_reentry=True
    )
    
    application.add_handler(lfg_handler)
    logger.info("LFG handlers set up successfully")