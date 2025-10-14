"""
User-facing command handlers (balance, withdraw, accounts).
"""
import os
import logging
from typing import Dict, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, ConversationHandler, MessageHandler, CallbackQueryHandler, filters
from database import get_db_session, close_db_session
from database.operations import UserService, AccountService, WithdrawalService, SystemSettingsService
from utils.helpers import MessageUtils

logger = logging.getLogger(__name__)

# Conversation states for withdrawal
WITHDRAW_AMOUNT, WITHDRAW_CURRENCY, WITHDRAW_ADDRESS = range(3)

async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /balance command."""
    user = update.effective_user
    
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
        
        # Get user accounts for additional stats
        accounts = AccountService.get_user_accounts(db, db_user.id)
        active_accounts = [acc for acc in accounts if acc.status == 'ACTIVE']
        
        # Get recent withdrawals
        recent_withdrawals = WithdrawalService.get_user_withdrawals(db, db_user.id)[:5]
        
        balance_text = f"""
💰 **Your Balance Overview**

👤 **User:** {user.first_name or 'User'} ({user.id})
💵 **Current Balance:** `{db_user.balance:.2f}` credits

📊 **Account Statistics:**
• 📱 Total Accounts: {len(accounts)}
• ✅ Active Accounts: {len(active_accounts)}
• ❄️ Frozen/Held: {len(accounts) - len(active_accounts)}

💸 **Withdrawal History:**
        """
        
        if recent_withdrawals:
            for withdrawal in recent_withdrawals:
                status_emoji = {'PENDING': '⏳', 'COMPLETED': '✅', 'REJECTED': '❌', 'FAILED': '💥'}
                balance_text += f"\n• {status_emoji.get(withdrawal.status, '❓')} {withdrawal.amount} {withdrawal.currency} - {withdrawal.status}"
        else:
            balance_text += "\n• No withdrawal history yet"
        
        balance_text += f"""

📅 **Member Since:** {db_user.created_at.strftime('%Y-%m-%d')}
🔄 **Last Updated:** {db_user.updated_at.strftime('%Y-%m-%d %H:%M:%S')}

**Want to withdraw?** Use `/withdraw` to cash out your earnings! 💸
        """
        
        keyboard = [
            [InlineKeyboardButton("💸 Withdraw Funds", callback_data="start_withdrawal")],
            [InlineKeyboardButton("📱 My Accounts", callback_data="my_accounts")],
            [InlineKeyboardButton("🔄 Refresh Balance", callback_data="refresh_balance")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.callback_query:
            await update.callback_query.edit_message_text(
                balance_text,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                balance_text,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        
        logger.info(f"Balance command handled for user {user.id}")
        
    except Exception as e:
        logger.error(f"Error in balance command: {e}")
        error_msg = "❌ An error occurred while fetching your balance. Please try again later."
        
        if update.callback_query:
            await update.callback_query.edit_message_text(error_msg)
        else:
            await update.message.reply_text(error_msg)
    finally:
        close_db_session(db)

async def accounts_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /accounts command."""
    user = update.effective_user
    
    db = get_db_session()
    try:
        # Get user
        db_user = UserService.get_user_by_telegram_id(db, user.id)
        
        if not db_user:
            await update.message.reply_text(
                "❌ User not found. Please use /start to initialize your account."
            )
            return
        
        # Get user accounts
        accounts = AccountService.get_user_accounts(db, db_user.id)
        
        if not accounts:
            no_accounts_text = """
📱 **Your Accounts**

You haven't added any accounts yet! 

🚀 **Ready to get started?**

Use `/lfg` to add your first Telegram account and start earning!

**Benefits of adding accounts:**
• 💰 Automatic earnings
• 🔐 Advanced security protection
• 📊 Detailed account management
• 💸 Withdrawal capabilities
            """
            
            keyboard = [
                [InlineKeyboardButton("✅ Add Account (LFG)", callback_data="start_lfg")],
                [InlineKeyboardButton("❓ How it Works", callback_data="how_it_works")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    no_accounts_text,
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
            else:
                await update.message.reply_text(
                    no_accounts_text,
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
            return
        
        # Format accounts list
        accounts_text = f"""
📱 **Your Accounts ({len(accounts)})**

👤 **User:** {user.first_name or 'User'}
📊 **Total Balance:** `{db_user.balance:.2f}` credits

**Account Details:**
        """
        
        status_emojis = {
            'ACTIVE': '✅',
            'FROZEN': '❄️', 
            'BANNED': '🚫',
            '24_HOUR_HOLD': '⏳'
        }
        
        for i, account in enumerate(accounts, 1):
            status_emoji = status_emojis.get(account.status, '❓')
            accounts_text += f"""
**{i}. {account.phone_number}**
├ Status: {status_emoji} {account.status}
├ Country: {account.country_code or 'Unknown'}
├ 2FA: {'✅ Enabled' if account.two_fa_enabled else '❌ Disabled'}
├ Added: {account.created_at.strftime('%Y-%m-%d')}
└ Last Active: {account.last_activity_at.strftime('%Y-%m-%d') if account.last_activity_at else 'Never'}
            """
        
        accounts_text += f"""

📈 **Statistics:**
• Active: {len([a for a in accounts if a.status == 'ACTIVE'])}
• Issues: {len([a for a in accounts if a.status != 'ACTIVE'])}

**Need help?** Contact support if you have questions about your accounts.
        """
        
        keyboard = [
            [InlineKeyboardButton("➕ Add Another Account", callback_data="start_lfg")],
            [InlineKeyboardButton("💰 Check Balance", callback_data="check_balance")],
            [InlineKeyboardButton("🔄 Refresh Status", callback_data="refresh_accounts")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.callback_query:
            await update.callback_query.edit_message_text(
                accounts_text,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                accounts_text,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        
        logger.info(f"Accounts command handled for user {user.id}")
        
    except Exception as e:
        logger.error(f"Error in accounts command: {e}")
        error_msg = "❌ An error occurred while fetching your accounts. Please try again later."
        
        if update.callback_query:
            await update.callback_query.edit_message_text(error_msg)
        else:
            await update.message.reply_text(error_msg)
    finally:
        close_db_session(db)

async def start_withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start withdrawal process."""
    user = update.effective_user
    
    db = get_db_session()
    try:
        # Get user
        db_user = UserService.get_user_by_telegram_id(db, user.id)
        
        if not db_user:
            await update.callback_query.edit_message_text(
                "❌ User not found. Please use /start to initialize your account."
            )
            return ConversationHandler.END
        
        # Check minimum balance
        minimum_withdrawal = 10.0  # Example minimum
        
        if db_user.balance < minimum_withdrawal:
            await update.callback_query.edit_message_text(
                f"❌ **Insufficient Balance**\n\n"
                f"💰 Your balance: `{db_user.balance:.2f}` credits\n"
                f"📊 Minimum withdrawal: `{minimum_withdrawal:.2f}` credits\n\n"
                f"Keep earning to reach the minimum withdrawal amount! 💪"
            )
            return ConversationHandler.END
        
        # Check if withdrawals are enabled
        usdt_enabled = SystemSettingsService.is_withdrawal_enabled(db, 'USDT-BEP20')
        trx_enabled = SystemSettingsService.is_withdrawal_enabled(db, 'TRX')
        
        if not (usdt_enabled or trx_enabled):
            await update.callback_query.edit_message_text(
                "❌ **Withdrawals Temporarily Disabled**\n\n"
                "Withdrawals are currently disabled for maintenance.\n"
                "Please try again later or contact support for more information."
            )
            return ConversationHandler.END
        
        withdraw_text = f"""
💸 **Withdrawal Request**

💰 **Available Balance:** `{db_user.balance:.2f}` credits
📊 **Minimum Withdrawal:** `{minimum_withdrawal:.2f}` credits

**Step 1: Enter Amount**

Please enter the amount you want to withdraw:
• Must be at least {minimum_withdrawal:.2f} credits
• Cannot exceed your current balance
• Amount will be converted to your chosen currency

**Enter withdrawal amount:**
        """
        
        context.user_data['user_balance'] = db_user.balance
        context.user_data['minimum_withdrawal'] = minimum_withdrawal
        
        keyboard = [
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel_withdrawal")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            withdraw_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
        return WITHDRAW_AMOUNT
        
    except Exception as e:
        logger.error(f"Error starting withdrawal: {e}")
        await update.callback_query.edit_message_text(
            "❌ An error occurred. Please try again later."
        )
        return ConversationHandler.END
    finally:
        close_db_session(db)

async def handle_withdraw_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle withdrawal amount input."""
    try:
        amount_text = update.message.text.strip()
        amount = float(amount_text)
        
        user_balance = context.user_data.get('user_balance', 0)
        minimum_withdrawal = context.user_data.get('minimum_withdrawal', 10)
        
        if amount < minimum_withdrawal:
            await update.message.reply_text(
                f"❌ **Amount too low!**\n\n"
                f"Minimum withdrawal: `{minimum_withdrawal:.2f}` credits\n"
                f"You entered: `{amount:.2f}` credits\n\n"
                f"**Please enter a valid amount:**"
            )
            return WITHDRAW_AMOUNT
        
        if amount > user_balance:
            await update.message.reply_text(
                f"❌ **Insufficient balance!**\n\n"
                f"Your balance: `{user_balance:.2f}` credits\n"
                f"You requested: `{amount:.2f}` credits\n\n"
                f"**Please enter a valid amount:**"
            )
            return WITHDRAW_AMOUNT
        
        # Store amount and proceed to currency selection
        context.user_data['withdraw_amount'] = amount
        
        # Check available currencies
        db = get_db_session()
        try:
            usdt_enabled = SystemSettingsService.is_withdrawal_enabled(db, 'USDT-BEP20')
            trx_enabled = SystemSettingsService.is_withdrawal_enabled(db, 'TRX')
        finally:
            close_db_session(db)
        
        currency_text = f"""
💸 **Withdrawal Request**

✅ **Amount:** `{amount:.2f}` credits

**Step 2: Choose Currency**

Please select your preferred withdrawal currency:
        """
        
        keyboard = []
        if usdt_enabled:
            keyboard.append([InlineKeyboardButton("💎 USDT (BEP20)", callback_data="currency_USDT-BEP20")])
        if trx_enabled:
            keyboard.append([InlineKeyboardButton("🔷 TRX (Tron)", callback_data="currency_TRX")])
        
        keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel_withdrawal")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            currency_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
        return WITHDRAW_CURRENCY
        
    except ValueError:
        await update.message.reply_text(
            "❌ **Invalid amount format!**\n\n"
            "Please enter a valid number (e.g., 10, 25.5, 100)\n\n"
            "**Enter withdrawal amount:**"
        )
        return WITHDRAW_AMOUNT
    except Exception as e:
        logger.error(f"Error handling withdrawal amount: {e}")
        await update.message.reply_text(
            "❌ An error occurred. Please try again or use /cancel"
        )
        return ConversationHandler.END

async def handle_currency_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle currency selection."""
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("currency_"):
        currency = query.data.replace("currency_", "")
        context.user_data['withdraw_currency'] = currency
        
        amount = context.user_data.get('withdraw_amount', 0)
        
        address_text = f"""
💸 **Withdrawal Request**

✅ **Amount:** `{amount:.2f}` credits
✅ **Currency:** {currency}

**Step 3: Destination Address**

Please enter your {currency} wallet address:

**Important:**
• Double-check the address is correct
• Wrong addresses cannot be recovered
• Only send {currency} addresses
• Do not include any extra text

**Enter your {currency} address:**
        """
        
        keyboard = [
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel_withdrawal")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            address_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
        return WITHDRAW_ADDRESS
    
    return WITHDRAW_CURRENCY

async def handle_withdraw_address(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle withdrawal address input."""
    user = update.effective_user
    address = update.message.text.strip()
    
    # Basic address validation
    amount = context.user_data.get('withdraw_amount', 0)
    currency = context.user_data.get('withdraw_currency', '')
    
    if len(address) < 25 or len(address) > 100:
        await update.message.reply_text(
            "❌ **Invalid address format!**\n\n"
            "Please check your address:\n"
            "• Should be 25-100 characters long\n"
            "• Should not contain spaces\n"
            "• Should be a valid wallet address\n\n"
            "**Please enter a valid address:**"
        )
        return WITHDRAW_ADDRESS
    
    # Create withdrawal request
    db = get_db_session()
    try:
        # Get user
        db_user = UserService.get_user_by_telegram_id(db, user.id)
        
        if not db_user or db_user.balance < amount:
            await update.message.reply_text(
                "❌ **Invalid request or insufficient balance.**\n"
                "Please start over with /withdraw"
            )
            return ConversationHandler.END
        
        # Create withdrawal record
        withdrawal = WithdrawalService.create_withdrawal(
            db=db,
            user_id=db_user.id,
            amount=amount,
            currency=currency,
            destination_address=address
        )
        
        # Deduct amount from user balance (pending withdrawal)
        UserService.update_user_balance(db, db_user.id, -amount)
        
        success_text = f"""
✅ **Withdrawal Request Submitted!**

🎫 **Request ID:** `#{withdrawal.id}`
💰 **Amount:** `{amount:.2f}` credits
💎 **Currency:** {currency}
🎯 **Address:** `{address[:10]}...{address[-10:]}`
📅 **Submitted:** {withdrawal.created_at.strftime('%Y-%m-%d %H:%M:%S')}

⏳ **Status:** PENDING

**What's Next?**
• Your request is being reviewed
• Processing typically takes 24-48 hours
• You'll be notified when completed
• Contact support if you have questions

**Important:** The amount has been deducted from your balance and is now pending withdrawal.

Thank you for using our service! 🙏
        """
        
        keyboard = [
            [InlineKeyboardButton("💰 Check Balance", callback_data="check_balance")],
            [InlineKeyboardButton("📝 Withdrawal History", callback_data="withdrawal_history")],
            [InlineKeyboardButton("📞 Contact Support", callback_data="contact_support")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            success_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
        # Notify admin
        admin_chat_id = os.getenv('ADMIN_CHAT_ID')
        if admin_chat_id:
            try:
                admin_text = f"""
💸 **New Withdrawal Request**

🎫 **ID:** #{withdrawal.id}
👤 **User:** {user.id} (@{user.username or 'N/A'})
💰 **Amount:** {amount:.2f} credits
💎 **Currency:** {currency}
🎯 **Address:** `{address}`
📅 **Time:** {withdrawal.created_at.strftime('%Y-%m-%d %H:%M:%S')}

Use /admin to manage this request.
                """
                
                await context.bot.send_message(
                    chat_id=admin_chat_id,
                    text=admin_text,
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.warning(f"Failed to notify admin of withdrawal: {e}")
        
        logger.info(f"Withdrawal request created: ID {withdrawal.id}, User {user.id}, Amount {amount} {currency}")
        
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"Error creating withdrawal request: {e}")
        await update.message.reply_text(
            "❌ **Error processing your request.**\n"
            "Please try again later or contact support."
        )
        return ConversationHandler.END
    finally:
        close_db_session(db)

async def cancel_withdrawal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel withdrawal process."""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "❌ **Withdrawal Cancelled**\n\n"
        "Your withdrawal request has been cancelled.\n"
        "No funds were deducted from your balance.\n\n"
        "You can start a new withdrawal anytime with `/withdraw`"
    )
    
    context.user_data.clear()
    return ConversationHandler.END

def setup_user_handlers(application) -> None:
    """Set up user command handlers."""
    # Basic commands
    application.add_handler(CommandHandler("balance", balance_command))
    application.add_handler(CommandHandler("accounts", accounts_command))
    
    # Withdrawal conversation handler
    withdraw_handler = ConversationHandler(
        entry_points=[
            CommandHandler("withdraw", start_withdraw),
            CallbackQueryHandler(start_withdraw, pattern="^start_withdrawal$")
        ],
        states={
            WITHDRAW_AMOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_withdraw_amount)
            ],
            WITHDRAW_CURRENCY: [
                CallbackQueryHandler(handle_currency_selection, pattern="^currency_")
            ],
            WITHDRAW_ADDRESS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_withdraw_address)
            ]
        },
        fallbacks=[
            CallbackQueryHandler(cancel_withdrawal, pattern="^cancel_withdrawal$"),
            CommandHandler("cancel", cancel_withdrawal)
        ],
        allow_reentry=True
    )
    
    application.add_handler(withdraw_handler)
    
    # Additional callback handlers for inline buttons
    application.add_handler(CallbackQueryHandler(balance_command, pattern="^(check_balance|refresh_balance)$"))
    application.add_handler(CallbackQueryHandler(accounts_command, pattern="^(my_accounts|refresh_accounts)$"))
    
    logger.info("User handlers set up successfully")