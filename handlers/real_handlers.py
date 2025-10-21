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
    handle_view_user_details
)


async def show_real_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display the main menu after successful verification."""
    user = update.effective_user
    if update.callback_query:
        await update.callback_query.answer()
    
    try:
        db = get_db_session()
        try:
            # Load user's language from database
            from utils.helpers import load_user_language
            load_user_language(context, user.id)
            
            db_user = UserService.get_user_by_telegram_id(db, user.id)
            reply_markup = InlineKeyboardMarkup([])
            if not db_user:
                logger.error(f"User {user.id} not found in database during main menu display")
                message_text = "⚠️ **User not found. Please restart with /start**"
            else:
                username_display = f"@{user.username}" if user.username else f"User {user.id}"
                balance = db_user.balance if hasattr(db_user, 'balance') else 0.00
                is_admin = bool(getattr(db_user, 'is_admin', False))
                
                message_text = f"""
🎉 **Welcome to Real Account Marketplace!**

👤 **User:** {username_display}
💰 **Balance:** ${balance:.2f}
✅ **Status:** Verified

**What would you like to do?**
                """
                
                main_menu_markup = get_main_menu_keyboard(is_admin=is_admin)
                if isinstance(main_menu_markup, InlineKeyboardMarkup):
                    reply_markup = main_menu_markup
                elif main_menu_markup:
                    reply_markup = InlineKeyboardMarkup(main_menu_markup)
                else:
                    logger.warning("Main menu keyboard helper returned empty value; using fallback layout")
        finally:
            close_db_session(db)
        
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
    except Exception as e:
        logger.error(f"Error in show_real_main_menu: {e}")
        error_keyboard = [[InlineKeyboardButton("🔄 Restart", callback_data="main_menu")]]
        error_text = "❌ Error loading main menu. Please try again."
        
        if update.callback_query:
            await update.callback_query.edit_message_text(
                error_text,
                reply_markup=InlineKeyboardMarkup(error_keyboard)
            )
        else:
            await update.message.reply_text(
                error_text,
                reply_markup=InlineKeyboardMarkup(error_keyboard)
            )


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Central router for button callbacks."""
    query = update.callback_query
    await query.answer()
    
    # Load user's language from database FIRST - ensures language persists everywhere
    from utils.helpers import load_user_language
    load_user_language(context, update.effective_user.id)
    
    # Check user verification status first
    db = get_db_session()
    try:
        db_user = UserService.get_user_by_telegram_id(db, update.effective_user.id)
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
    
    # Main menu handling
    if query.data == "main_menu":
        captcha_image_path = context.user_data.get('captcha_image_path')
        if captcha_image_path:
            try:
                from services.captcha import CaptchaService
                captcha_service = CaptchaService()
                captcha_service.cleanup_captcha_image(captcha_image_path)
                context.user_data.pop('captcha_image_path', None)
                logger.info(f"✅ Cleaned up CAPTCHA image file: {captcha_image_path}")
            except Exception as e:
                logger.error(f"Error cleaning up CAPTCHA image: {e}")
        
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
        """Start command - force CAPTCHA verification."""
        user = update.effective_user
        logger.info(f"🚀 START: User {user.id} starting bot - forcing CAPTCHA")
        
        context.user_data.clear()
        
        try:
            db = get_db_session()
            try:
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
                
                # Force verification reset
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
    from handlers.main_handlers import (
        handle_withdraw_menu, handle_withdraw_trx, handle_withdraw_usdt,
        handle_withdraw_binance, handle_withdrawal_history, handle_withdrawal_details,
        handle_withdrawal_confirmation, WITHDRAW_DETAILS, WITHDRAW_CONFIRM, handle_check_balance
    )
    
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
        logger.info("✅ Admin handlers registered")
    except Exception as e:
        logger.error(f"Failed to load admin handlers: {e}")
    
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
