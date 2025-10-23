"""
Real Telegram Account Selling Handlers - Streamlined Core Module
Imports handlers from modular architecture: verification_flow, user_panel, selling_flow, withdrawal_flow
"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CallbackQueryHandler, MessageHandler, filters, CommandHandler
from keyboard_layout_fix import get_main_menu_keyboard
from database import get_db_session, close_db_session
from database.operations import UserService
import os

logger = logging.getLogger(__name__)

# Import modular handlers
from handlers.verification_flow import (
    start_verification_process,
    handle_start_verification,
    handle_captcha_answer,
    show_channel_verification,
    handle_verify_channels
)
from handlers.user_panel import (
    handle_balance,
    handle_sales_history,
    handle_account_details,
    handle_language_menu,
    handle_language_selection,
    show_how_it_works,
    show_2fa_help
)
from handlers.selling_flow import (
    get_real_selling_handler,
    cancel_sale
)
from handlers.withdrawal_flow import (
    handle_approve_withdrawal,
    handle_reject_withdrawal,
    handle_mark_paid,
    handle_view_user_details,
    handle_withdraw_menu,
    handle_withdraw_trx,
    handle_withdraw_usdt,
    handle_withdraw_binance,
    handle_withdrawal_history,
    handle_delete_withdrawal,
    handle_withdrawal_details,
    handle_withdrawal_confirmation,
    WITHDRAW_DETAILS,
    WITHDRAW_CONFIRM
)


async def show_real_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, db_user_cached=None) -> None:
    """Display the main menu after successful verification.
    
    Args:
        update: Telegram update object
        context: Bot context
        db_user_cached: Optional pre-fetched user object (optimization to avoid redundant DB query)
    """
    user = update.effective_user
    if update.callback_query:
        await update.callback_query.answer()
    
    db = None
    db_needs_close = False
    try:
        # Only fetch user from DB if not provided (optimization)
        if db_user_cached is None:
            db = get_db_session()
            db_needs_close = True
            db_user = UserService.get_user_by_telegram_id(db, user.id)
        else:
            db_user = db_user_cached
        
        # Load language directly from fetched user (avoid duplicate query)
        if db_user and db_user.language_code:
            try:
                from services.translation_service import translation_service
                translation_service.set_user_language(context, db_user.language_code)
            except Exception as lang_error:
                logger.warning(f"Could not set user language: {lang_error}")
        
        if not db_user:
            logger.error(f"User {user.id} not found in database during main menu display")
            error_keyboard = [[InlineKeyboardButton("🔄 Restart", callback_data="start")]]
            message_text = "⚠️ **User not found. Please restart with /start or click the button below.**"
            reply_markup = InlineKeyboardMarkup(error_keyboard)
        else:
            username_display = f"@{user.username}" if user.username else f"User {user.id}"
            balance = getattr(db_user, 'balance', 0.00)
            is_admin = bool(getattr(db_user, 'is_admin', False))
            
            message_text = f"""
🎉 **Welcome to teleflare_bot_io**

👤 **User:** {username_display}
💰 **Balance:** ${balance:.2f}
✅ **Status:** Verified

**What would you like to do?**
            """
            
            try:
                main_menu_markup = get_main_menu_keyboard(is_admin=is_admin)
                if isinstance(main_menu_markup, InlineKeyboardMarkup):
                    reply_markup = main_menu_markup
                elif main_menu_markup:
                    reply_markup = InlineKeyboardMarkup(main_menu_markup)
                else:
                    logger.warning("Main menu keyboard helper returned empty value; using fallback layout")
                    reply_markup = InlineKeyboardMarkup([
                        [InlineKeyboardButton("🚀 Sell Account", callback_data="start_real_selling")],
                        [InlineKeyboardButton("💰 Balance", callback_data="check_balance")],
                        [InlineKeyboardButton("← Back", callback_data="start")]
                    ])
            except Exception as keyboard_error:
                logger.error(f"Error building keyboard: {keyboard_error}")
                reply_markup = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 Retry", callback_data="main_menu")]
                ])
        
        try:
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    message_text,
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
            else:
                await update.message.reply_text(
                    message_text,
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
        except Exception as send_error:
            logger.error(f"Failed to send main menu message: {send_error}")
            try:
                if update.message:
                    await update.message.reply_text(
                        "⚠️ Error displaying menu. Please try /start again.",
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Restart", callback_data="start")]])
                    )
            except Exception:
                pass
                
    except Exception as e:
        logger.error(f"Critical error in show_real_main_menu: {e}", exc_info=True)
        error_keyboard = [[InlineKeyboardButton("🔄 Restart", callback_data="start")]]
        error_text = """
❌ **Error Loading Menu**

Something went wrong. Please try restarting the bot.

**What to do:**
• Click "Restart" below
• If issue persists, send /start
        """
        
        try:
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    error_text,
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup(error_keyboard)
                )
            else:
                await update.message.reply_text(
                    error_text,
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup(error_keyboard)
                )
        except Exception as fallback_error:
            logger.error(f"Failed to show error message: {fallback_error}")
    finally:
        if db and db_needs_close:
            close_db_session(db)


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Central router for button callbacks."""
    query = update.callback_query
    await query.answer()
    
    # Fetch user once and load language from the same object (optimization)
    db = get_db_session()
    try:
        db_user = UserService.get_user_by_telegram_id(db, update.effective_user.id)
        
        # Load language directly from user object (avoid separate DB query)
        if db_user and db_user.language_code:
            try:
                from services.translation_service import translation_service
                translation_service.set_user_language(context, db_user.language_code)
            except Exception as lang_error:
                logger.warning(f"Could not set user language: {lang_error}")
        
        user_verified = bool(
            getattr(db_user, 'verification_completed', False)
            or getattr(db_user, 'is_verified', False)
        ) if db_user else False
    finally:
        close_db_session(db)
    
    # If user is not verified, force them through verification
    if not user_verified and not context.user_data.get('verified'):
        if query.data in ["balance", "sales_history", "how_it_works", "2fa_help", "cancel_sale", "withdraw_menu", "language_menu", "status", "start_real_selling", "check_balance", "withdrawal_history"]:
            logger.info(f"User {update.effective_user.id} not verified, routing to verification")
            db = get_db_session()
            try:
                db_user = UserService.get_user_by_telegram_id(db, update.effective_user.id)
                await start_verification_process(update, context, db_user)
            finally:
                close_db_session(db)
            return
    
    # Main menu handling (optimized - no file cleanup needed)
    if query.data == "main_menu":
        context.user_data.pop('captcha_answer', None)
        context.user_data.pop('captcha_type', None)
        context.user_data.pop('verification_step', None)
        
        captcha_photo_message_id = context.user_data.pop('captcha_photo_message_id', None)
        captcha_chat_id = context.user_data.pop('captcha_chat_id', None)
        
        if captcha_photo_message_id and captcha_chat_id:
            try:
                await context.bot.delete_message(
                    chat_id=captcha_chat_id,
                    message_id=captcha_photo_message_id
                )
                logger.info(f"✅ Deleted CAPTCHA photo message")
            except Exception as e:
                logger.error(f"Could not delete CAPTCHA photo: {e}")
        
        db = get_db_session()
        try:
            db_user = UserService.get_user_by_telegram_id(db, update.effective_user.id)
            await start_verification_process(update, context, db_user)
        finally:
            close_db_session(db)
    
    # Route to modular handlers
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
    elif query.data == "start_real_selling":
        # This should be handled by the selling conversation handler
        pass
    elif query.data.startswith("approve_withdrawal_"):
        await handle_approve_withdrawal(update, context)
    elif query.data.startswith("reject_withdrawal_"):
        await handle_reject_withdrawal(update, context)
    elif query.data.startswith("view_user_"):
        await handle_view_user_details(update, context)
    elif query.data.startswith("mark_paid_"):
        await handle_mark_paid(update, context)


def setup_real_handlers(application) -> None:
    """Setup all bot handlers with modular architecture."""
    from telegram.ext import CommandHandler, CallbackQueryHandler, MessageHandler, filters
    
    logger.info("🚀 Initializing modular handler system...")
    
    # ========================================
    # START COMMAND
    # ========================================
    async def start_handler(update, context):
        """Start command - smart CAPTCHA verification with 7-day cache."""
        user = update.effective_user
        logger.info(f"🚀 START: User {user.id} starting bot")
        
        context.user_data.clear()
        
        try:
            db = get_db_session()
            try:
                from datetime import datetime, timedelta, timezone
                
                db_user = UserService.get_user_by_telegram_id(db, user.id)
                if not db_user:
                    from database.models import User
                    db_user = User(
                        telegram_user_id=user.id,
                        username=user.username,
                        first_name=user.first_name,
                        last_name=user.last_name
                    )
                    db.add(db_user)
                    db.commit()
                    db.refresh(db_user)
                    logger.info(f"✨ New user created: {user.id}")
                
                # Check 7-day CAPTCHA cache
                captcha_verified_at = getattr(db_user, 'captcha_verified_at', None)
                if captcha_verified_at:
                    # Check if CAPTCHA was verified within last 7 days
                    # Make captcha_verified_at timezone-aware (it's stored as UTC but naive)
                    if captcha_verified_at.tzinfo is None:
                        captcha_verified_at = captcha_verified_at.replace(tzinfo=timezone.utc)
                    days_since_verification = (datetime.now(timezone.utc) - captcha_verified_at).days
                    
                    if days_since_verification < 7:
                        # CAPTCHA still valid! Skip verification, go to main menu
                        logger.info(f"✅ CAPTCHA cache hit for user {user.id} ({days_since_verification} days old)")
                        
                        # Mark as verified
                        db_user.captcha_completed = True
                        db_user.verification_completed = True
                        context.user_data['verified'] = True
                        db.commit()
                        
                        # Show main menu directly (pass cached user to avoid redundant query)
                        await show_real_main_menu(update, context, db_user_cached=db_user)
                        return ConversationHandler.END
                    else:
                        logger.info(f"⏰ CAPTCHA expired for user {user.id} ({days_since_verification} days old)")
                
                # Fallback: If user was verified before captcha_verified_at column existed
                # Backfill the timestamp and skip verification
                elif getattr(db_user, 'verification_completed', False) or getattr(db_user, 'is_verified', False):
                    logger.info(f"🔧 Backfilling CAPTCHA timestamp for previously verified user {user.id}")
                    db_user.captcha_verified_at = datetime.now(timezone.utc)
                    db_user.captcha_completed = True
                    db_user.verification_completed = True
                    context.user_data['verified'] = True
                    db.commit()
                    
                    # Show main menu directly (pass cached user to avoid redundant query)
                    await show_real_main_menu(update, context, db_user_cached=db_user)
                    return ConversationHandler.END
                
                # CAPTCHA not verified or expired - start verification
                logger.info(f"🔒 Starting verification for user {user.id}")
                db_user.captcha_completed = False
                db_user.verification_completed = False
                db_user.channels_joined = False
                db.commit()
                
                await start_verification_process(update, context, db_user)
                
            finally:
                close_db_session(db)
                
        except Exception as e:
            logger.error(f"Error in start_handler: {e}")
            await start_verification_process(update, context, None)
        
        return ConversationHandler.END
    
    application.add_handler(CommandHandler("start", start_handler))
    
    # ========================================
    # WITHDRAWAL CONVERSATION
    # ========================================
    from handlers.user_panel import handle_check_balance
    
    async def cancel_withdrawal(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel withdrawal conversation."""
        if update.callback_query:
            await update.callback_query.answer()
        context.user_data.pop('conversation_type', None)
        context.user_data.pop('withdrawal_currency', None)
        context.user_data.pop('withdrawal_amount', None)
        context.user_data.pop('withdrawal_address', None)
        return ConversationHandler.END
    
    async def isolated_withdrawal_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle withdrawal wallet address input."""
        user = update.effective_user
        logger.info(f"💸 Withdrawal handler - processing wallet address from user {user.id}")
        
        try:
            result = await handle_withdrawal_details(update, context)
            return result
        except Exception as e:
            logger.error(f"Withdrawal handler error: {e}")
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
            CommandHandler("start", start_handler),
            MessageHandler(filters.COMMAND, cancel_withdrawal)
        ],
        per_message=False,
        per_user=True
    )
    application.add_handler(withdrawal_conversation)
    logger.info("✅ Withdrawal ConversationHandler registered")
    
    # ========================================
    # SELLING CONVERSATION
    # ========================================
    application.add_handler(get_real_selling_handler())
    logger.info("✅ Selling ConversationHandler registered")
    
    # ========================================
    # ADMIN HANDLERS
    # ========================================
    try:
        from handlers.admin_handlers import setup_admin_handlers
        setup_admin_handlers(application)
        logger.info("✅ Admin handlers registered successfully")
    except Exception as e:
        logger.error(f"❌ CRITICAL: Failed to load admin handlers: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
    
    # ========================================
    # CALLBACK QUERY HANDLERS
    # ========================================
    
    # Main menu callback
    async def handle_main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle 'Back to Start' button."""
        query = update.callback_query
        await query.answer()
    
        captcha_image_path = context.user_data.get('captcha_image_path')
        if captcha_image_path:
            try:
                from services.captcha import CaptchaService
                captcha_service = CaptchaService()
                captcha_service.cleanup_captcha_image(captcha_image_path)
                context.user_data.pop('captcha_image_path', None)
            except Exception as e:
                logger.error(f"Error cleaning up CAPTCHA: {e}")
    
        context.user_data.pop('captcha_answer', None)
        context.user_data.pop('captcha_type', None)
        context.user_data.pop('verification_step', None)
    
        db_user = None
        user_verified = False
        db = get_db_session()
        try:
            db_user = UserService.get_user_by_telegram_id(db, update.effective_user.id)
            if db_user:
                user_verified = bool(
                    getattr(db_user, 'verification_completed', False)
                    or getattr(db_user, 'is_verified', False)
                )
        finally:
            close_db_session(db)

        if user_verified or context.user_data.get('verified'):
            logger.info("Routing user %s to real main menu", update.effective_user.id)
            await show_real_main_menu(update, context)
        else:
            logger.info("Routing user %s to verification start", update.effective_user.id)
            await start_verification_process(update, context, db_user)
    
    application.add_handler(CallbackQueryHandler(handle_main_menu_callback, pattern='^main_menu$'))
    
    # Channel verification handlers
    async def handle_show_channels_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.callback_query:
            await update.callback_query.answer()
        await show_channel_verification(update, context)

    application.add_handler(CallbackQueryHandler(handle_show_channels_callback, pattern='^show_channels$'))
    application.add_handler(CallbackQueryHandler(handle_verify_channels, pattern='^verify_channels$'))
    
    # Other callback handlers
    async def handle_check_balance_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle balance check with verification enforcement."""
        # Check verification first
        db = get_db_session()
        try:
            db_user = UserService.get_user_by_telegram_id(db, update.effective_user.id)
            user_verified = bool(
                getattr(db_user, 'verification_completed', False)
                or getattr(db_user, 'is_verified', False)
            ) if db_user else False
        finally:
            close_db_session(db)
        
        if not user_verified and not context.user_data.get('verified'):
            logger.info(f"User {update.effective_user.id} not verified, routing to verification for balance check")
            db = get_db_session()
            try:
                db_user = UserService.get_user_by_telegram_id(db, update.effective_user.id)
                await start_verification_process(update, context, db_user)
            finally:
                close_db_session(db)
            return
        
        await handle_check_balance(update, context)

    async def handle_withdraw_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle withdrawal menu with verification enforcement."""
        # Check verification first
        db = get_db_session()
        try:
            db_user = UserService.get_user_by_telegram_id(db, update.effective_user.id)
            user_verified = bool(
                getattr(db_user, 'verification_completed', False)
                or getattr(db_user, 'is_verified', False)
            ) if db_user else False
        finally:
            close_db_session(db)
        
        if not user_verified and not context.user_data.get('verified'):
            logger.info(f"User {update.effective_user.id} not verified, routing to verification for withdrawal")
            db = get_db_session()
            try:
                db_user = UserService.get_user_by_telegram_id(db, update.effective_user.id)
                await start_verification_process(update, context, db_user)
            finally:
                close_db_session(db)
            return
        
        await handle_withdraw_menu(update, context)

    async def handle_withdrawal_history_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle withdrawal history with verification enforcement."""
        # Check verification first
        db = get_db_session()
        try:
            db_user = UserService.get_user_by_telegram_id(db, update.effective_user.id)
            user_verified = bool(
                getattr(db_user, 'verification_completed', False)
                or getattr(db_user, 'is_verified', False)
            ) if db_user else False
        finally:
            close_db_session(db)
        
        if not user_verified and not context.user_data.get('verified'):
            logger.info(f"User {update.effective_user.id} not verified, routing to verification for withdrawal history")
            db = get_db_session()
            try:
                db_user = UserService.get_user_by_telegram_id(db, update.effective_user.id)
                await start_verification_process(update, context, db_user)
            finally:
                close_db_session(db)
            return
        
        await handle_withdrawal_history(update, context)

    async def handle_language_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle language menu - allow without verification."""
        await handle_language_menu(update, context)

    async def handle_language_selection_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle language selection - allow without verification."""
        await handle_language_selection(update, context)
    
    application.add_handler(CallbackQueryHandler(handle_check_balance_callback, pattern='^check_balance$'))
    application.add_handler(CallbackQueryHandler(handle_withdraw_menu_callback, pattern='^withdraw_menu$'))
    application.add_handler(CallbackQueryHandler(handle_withdrawal_history_callback, pattern='^withdrawal_history$'))
    application.add_handler(CallbackQueryHandler(handle_delete_withdrawal, pattern='^delete_withdrawal_'))
    application.add_handler(CallbackQueryHandler(handle_language_menu_callback, pattern='^language_menu$'))
    application.add_handler(CallbackQueryHandler(handle_language_selection_callback, pattern='^lang_(en|es|fr|de|ru|zh|hi|ar)$'))
    
    # Admin panel callback
    async def handle_admin_panel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Route admin panel clicks to admin handlers."""
        try:
            from handlers.admin_handlers import handle_admin_panel
            await handle_admin_panel(update, context)
        except Exception as e:
            logger.error(f"Error in admin panel: {e}")
            if update.callback_query:
                await update.callback_query.answer("❌ Error loading admin panel", show_alert=True)
    
    application.add_handler(CallbackQueryHandler(handle_admin_panel_callback, pattern='^admin_panel$'))
    
    # Verification handlers
    application.add_handler(CallbackQueryHandler(handle_start_verification, pattern='^start_verification$'))
    application.add_handler(CallbackQueryHandler(handle_start_verification, pattern='^new_captcha$'))
    application.add_handler(CallbackQueryHandler(show_real_main_menu, pattern='^real_main_menu$'))
    
    # ========================================
    # MESSAGE HANDLERS
    # ========================================
    
    # CAPTCHA answer handler
    async def isolated_captcha_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle CAPTCHA answers when in verification process."""
        user = update.effective_user
        text = update.message.text if update.message else ""
        
        # Check database for verification state
        db = get_db_session()
        try:
            db_user = UserService.get_user_by_telegram_id(db, user.id)
            user_in_verification = db_user and getattr(db_user, 'verification_step', 0) == 1 and db_user.captcha_answer
        finally:
            close_db_session(db)
        
        # Also check context as fallback
        context_verification = context.user_data.get('captcha_answer') and context.user_data.get('verification_step') == 1
        
        if user_in_verification or context_verification:
            logger.info(f"Processing CAPTCHA answer from user {user.id}")
            return await handle_captcha_answer(update, context)
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, isolated_captcha_handler))
    logger.info("✅ CAPTCHA answer handler registered")
    
    # ========================================
    # GENERAL BUTTON CALLBACK (LAST)
    # ========================================
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # ========================================
    # LEADER AND ANALYTICS HANDLERS
    # ========================================
    try:
        from handlers.leader_handlers import setup_leader_handlers
        setup_leader_handlers(application)
        logger.info("✅ Leader panel handlers loaded")
    except Exception as e:
        logger.error(f"Failed to load leader handlers: {e}")
    
    try:
        from handlers.analytics_handlers import setup_analytics_handlers
        setup_analytics_handlers(application)
        logger.info("✅ Analytics dashboard handlers loaded")
    except Exception as e:
        logger.error(f"Failed to load analytics handlers: {e}")
    
    logger.info("✅ All modular handlers registered successfully")
