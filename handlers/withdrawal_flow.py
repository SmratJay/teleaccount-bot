"""
Withdrawal Flow Handlers
Handles withdrawal requests and leader approval workflows
"""
import logging
import os
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from database import get_db_session, close_db_session
from database.operations import UserService, ActivityLogService, WithdrawalService
from database.models import Withdrawal, WithdrawalStatus, User
from services.translation_service import translation_service

logger = logging.getLogger(__name__)


WITHDRAW_DETAILS, WITHDRAW_CONFIRM = range(20, 22)


async def handle_withdraw_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display withdrawal options menu."""
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

    await update.callback_query.edit_message_text(
        withdraw_text,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


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

        balance = db_user.balance or 0.0
        if balance <= 0:
            await query.edit_message_text(
                "❌ *Insufficient Balance*\n\n"
                "Your current balance is $0.00. You need to sell accounts first to earn money for withdrawal.\n\n"
                "💡 Sell accounts to build your balance!",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🚀 Sell Account", callback_data="lfg_sell"),
                     InlineKeyboardButton("🔙 Back", callback_data="withdraw_menu")]
                ])
            )
            return ConversationHandler.END

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
            [InlineKeyboardButton(
                "ℹ️ How to Get TRX Address",
                url="https://support.tronlink.org/hc/en-us/articles/4403161972617-How-to-create-a-TRON-wallet-"
            )],
            [InlineKeyboardButton("🔙 Back to Methods", callback_data="withdraw_menu")]
        ]

        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

        context.user_data['withdrawal_type'] = 'TRX'
        context.user_data['conversation_type'] = 'withdrawal'

        return WITHDRAW_DETAILS

    except Exception as e:
        logger.error(f"Error in TRX withdrawal handler: {e}")
        await query.edit_message_text(
            "❌ An error occurred. Please try again later.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="withdraw_menu")]])
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

        balance = db_user.balance or 0.0
        if balance <= 0:
            await query.edit_message_text(
                "❌ *Insufficient Balance*\n\n"
                "Your current balance is $0.00. You need to sell accounts first to earn money for withdrawal.\n\n"
                "💡 Sell accounts to build your balance!",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🚀 Sell Account", callback_data="lfg_sell"),
                     InlineKeyboardButton("🔙 Back", callback_data="withdraw_menu")]
                ])
            )
            return ConversationHandler.END

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
            [InlineKeyboardButton(
                "ℹ️ How to Get BEP20 Address",
                url="https://academy.binance.com/en/articles/how-to-add-binance-smart-chain-bsc-to-metamask"
            )],
            [InlineKeyboardButton("🔙 Back to Methods", callback_data="withdraw_menu")]
        ]

        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

        context.user_data['withdrawal_type'] = 'USDT-BEP20'
        context.user_data['conversation_type'] = 'withdrawal'

        return WITHDRAW_DETAILS

    except Exception as e:
        logger.error(f"Error in USDT withdrawal handler: {e}")
        await query.edit_message_text(
            "❌ An error occurred. Please try again later.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="withdraw_menu")]])
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

        balance = db_user.balance or 0.0
        if balance <= 0:
            await query.edit_message_text(
                "❌ *Insufficient Balance*\n\n"
                "Your current balance is $0.00. You need to sell accounts first to earn money for withdrawal.\n\n"
                "💡 Sell accounts to build your balance!",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🚀 Sell Account", callback_data="lfg_sell"),
                     InlineKeyboardButton("🔙 Back", callback_data="withdraw_menu")]
                ])
            )
            return ConversationHandler.END

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
            [InlineKeyboardButton(
                "ℹ️ How to Find Binance ID",
                url="https://www.binance.com/en/support/faq/how-to-find-your-binance-account-id-115003398712"
            )],
            [InlineKeyboardButton("🔙 Back to Methods", callback_data="withdraw_menu")]
        ]

        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

        context.user_data['withdrawal_type'] = 'Binance'
        context.user_data['conversation_type'] = 'withdrawal'

        return WITHDRAW_DETAILS

    except Exception as e:
        logger.error(f"Error in Binance withdrawal handler: {e}")
        await query.edit_message_text(
            "❌ An error occurred. Please try again later.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="withdraw_menu")]])
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
        db_user = UserService.get_user_by_telegram_id(db, user.id)
        if not db_user:
            await query.edit_message_text("❌ User not found. Please restart the bot.")
            return

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

            for withdrawal in withdrawals[:10]:
                status_emoji = {
                    'PENDING': '⏳',
                    'LEADER_APPROVED': '✅',
                    'COMPLETED': '💚',
                    'REJECTED': '❌'
                }.get(withdrawal.status.value, '⏳')

                text += (
                    f"{status_emoji} *${withdrawal.amount:.2f}* - {withdrawal.currency}\n"
                    f"📅 {withdrawal.created_at.strftime('%Y-%m-%d %H:%M')}\n"
                    f"📊 Status: {withdrawal.status.value.title()}\n\n"
                )

                if withdrawal.status.value in ['COMPLETED', 'REJECTED']:
                    keyboard.append([
                        InlineKeyboardButton(
                            f"🗑 Delete #{withdrawal.id}",
                            callback_data=f"delete_withdrawal_{withdrawal.id}"
                        )
                    ])

            keyboard.extend([
                [InlineKeyboardButton("💰 New Withdrawal", callback_data="withdraw_menu")],
                [InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")]
            ])

        await query.edit_message_text(
            text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    except Exception as e:
        logger.error(f"Error in withdrawal history handler: {e}")
        await query.edit_message_text(
            "❌ An error occurred while loading withdrawal history.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="withdraw_menu")]])
        )
    finally:
        close_db_session(db)


async def handle_delete_withdrawal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Allow users to delete completed or rejected withdrawal records."""
    query = update.callback_query
    await query.answer()

    user = update.effective_user
    db = get_db_session()

    try:
        withdrawal_id = int(query.data.split('_')[-1])

        db_user = UserService.get_user_by_telegram_id(db, user.id)
        if not db_user:
            await query.edit_message_text("❌ User not found. Please restart the bot.")
            return

        user_withdrawals = WithdrawalService.get_user_withdrawals(db, db_user.id)
        target_withdrawal = next((w for w in user_withdrawals if w.id == withdrawal_id), None)

        if not target_withdrawal:
            await query.edit_message_text(
                "❌ Withdrawal not found or you don't have permission to delete it.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="withdrawal_history")]])
            )
            return

        if target_withdrawal.status.value not in ['COMPLETED', 'REJECTED']:
            await query.edit_message_text(
                "❌ You can only delete completed or rejected withdrawals.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="withdrawal_history")]])
            )
            return

        try:
            db.delete(target_withdrawal)
            db.commit()

            await query.edit_message_text(
                f"✅ Withdrawal record #{withdrawal_id} has been deleted successfully.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📋 View History", callback_data="withdrawal_history"),
                     InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")]
                ])
            )

            ActivityLogService.log_action(
                db=db,
                user_id=db_user.id,
                action="WITHDRAWAL_DELETED",
                details=f"User deleted withdrawal record #{withdrawal_id}"
            )

        except Exception as delete_error:
            logger.error(f"Error deleting withdrawal {withdrawal_id}: {delete_error}")
            db.rollback()
            await query.edit_message_text(
                "❌ Failed to delete withdrawal record. Please try again later.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="withdrawal_history")]])
            )

    except Exception as e:
        logger.error(f"Error in delete withdrawal handler: {e}")
        await query.edit_message_text(
            "❌ An error occurred while processing deletion.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="withdrawal_history")]])
        )
    finally:
        close_db_session(db)


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

        withdrawal_type = context.user_data.get('withdrawal_type', 'TRX')
        pending_address = context.user_data.get('pending_address')

        amount = None
        address_or_email = None
        currency = None

        if pending_address:
            try:
                amount_text = message_text.replace('$', '').replace(',', '').strip()
                if amount_text.replace('.', '').isdigit():
                    amount = float(amount_text)
                    address_or_email = pending_address
                    currency = 'USDT' if withdrawal_type == 'Binance' else None
                    del context.user_data['pending_address']
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
            lines = [line.strip() for line in message_text.split('\n') if line.strip()]

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

            if not address_or_email and lines:
                potential_address = lines[0].strip()
                is_valid_address = False

                if withdrawal_type == 'TRX' and len(potential_address) >= 30 and potential_address.startswith('T'):
                    is_valid_address = True
                elif withdrawal_type == 'USDT-BEP20' and len(potential_address) >= 40 and potential_address.startswith('0x'):
                    is_valid_address = True
                elif withdrawal_type == 'Binance' and '@' in potential_address and '.' in potential_address:
                    is_valid_address = True

                if is_valid_address:
                    address_or_email = potential_address

                    for line in lines[1:]:
                        try:
                            clean_amount = line.replace('$', '').replace(',', '').strip()
                            if clean_amount.replace('.', '').isdigit():
                                amount = float(clean_amount)
                                break
                        except ValueError:
                            continue

                    if not amount:
                        await update.message.reply_text(
                            f"✅ Address received: `{address_or_email}`\n\n"
                            "💰 Now please provide the withdrawal amount (minimum $5.00):\n\n"
                            "Just type the amount like: `10.00`",
                            parse_mode='Markdown'
                        )
                        context.user_data['pending_address'] = address_or_email
                        return WITHDRAW_DETAILS
                else:
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
                        "**Expected Format:**\n"
                        "```\n"
                        f"{expected_format}\n"
                        "```\n\n"
                        "**What I received:**\n"
                        "```\n"
                        f"{message_text}\n"
                        "```",
                        parse_mode='Markdown'
                    )
                    return WITHDRAW_DETAILS

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

        if amount < 5.0:
            await update.message.reply_text(
                "❌ Minimum withdrawal amount is $5.00.\n\n"
                "Please enter an amount of $5.00 or more."
            )
            return WITHDRAW_DETAILS

        if amount > (db_user.balance or 0.0):
            await update.message.reply_text(
                f"❌ Insufficient balance!\n\n"
                f"💰 Your balance: ${db_user.balance or 0:.2f}\n"
                f"💸 Requested amount: ${amount:.2f}\n\n"
                "Please enter a smaller amount or sell more accounts first."
            )
            return WITHDRAW_DETAILS

        if withdrawal_type == 'TRX':
            currency = 'TRX'
        elif withdrawal_type == 'USDT-BEP20':
            currency = 'USDT'
        elif withdrawal_type == 'Binance' and not currency:
            currency = 'USDT'

        withdrawal_details = {
            'method': withdrawal_type,
            'amount': amount,
            'address_or_email': address_or_email,
            'currency': currency,
            'user_id': db_user.id
        }

        context.user_data['withdrawal_details'] = withdrawal_details

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

        await update.message.reply_text(
            confirmation_text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
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

            db_user = UserService.get_user_by_telegram_id(db, user.id)
            if not db_user:
                await query.edit_message_text("❌ User not found. Please restart the bot.")
                return ConversationHandler.END

            withdrawal = WithdrawalService.create_withdrawal(
                db=db,
                user_id=withdrawal_details['user_id'],
                amount=withdrawal_details['amount'],
                currency=withdrawal_details['currency'],
                withdrawal_address=withdrawal_details['address_or_email'],
                withdrawal_method=withdrawal_details['method']
            )

            if withdrawal:
                try:
                    await send_withdrawal_to_leaders(context.bot, withdrawal, db_user)
                except Exception as leader_error:
                    logger.error(f"Failed to send leader notification: {leader_error}")

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

                await query.edit_message_text(
                    success_text,
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )

                try:
                    ActivityLogService.log_action(
                        db=db,
                        user_id=db_user.id,
                        action_type="WITHDRAWAL_REQUESTED",
                        description=f"User requested ${withdrawal.amount:.2f} withdrawal via {withdrawal.currency}"
                    )
                except Exception as log_error:
                    logger.error(f"Failed to log activity: {log_error}")

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
        leader_channel_id = os.getenv('LEADER_CHANNEL_ID', '-1002234567890')

        notification_text = (
            "🚨 *NEW WITHDRAWAL REQUEST*\n\n"
            f"👤 User: {user.first_name or 'Unknown'} (@{user.username or 'no_username'})\n"
            f"🆔 User ID: `{user.telegram_user_id}`\n"
            f"💰 Amount: *${withdrawal.amount:.2f}*\n"
            f"💳 Method: *{withdrawal.currency}*\n"
            f"📍 Address: `{withdrawal.withdrawal_address}`\n"
        )

        if withdrawal.currency and withdrawal.currency != 'USD':
            notification_text += f"💱 Currency: *{withdrawal.currency}*\n"

        notification_text += (
            f"\n🕒 Requested: {withdrawal.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
            "📊 Status: *PENDING APPROVAL*\n\n"
            "⚡ Please review and process this withdrawal request."
        )

        keyboard = [
            [
                InlineKeyboardButton("✅ Approve", callback_data=f"approve_withdrawal_{withdrawal.id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"reject_withdrawal_{withdrawal.id}")
            ],
            [InlineKeyboardButton("👤 View User", callback_data=f"view_user_{user.telegram_user_id}")]
        ]

        await bot.send_message(
            chat_id=leader_channel_id,
            text=notification_text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    except Exception as e:
        logger.error(f"Failed to send withdrawal notification to leaders: {e}")
        import traceback
        logger.error(traceback.format_exc())


async def handle_approve_withdrawal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle withdrawal approval by leaders."""
    query = update.callback_query
    user = update.effective_user
    
    # Extract withdrawal ID from callback data
    withdrawal_id = int(query.data.split("_")[-1])
    
    db = get_db_session()
    try:
        # Check if user is a leader
        db_user = UserService.get_user_by_telegram_id(db, user.id)
        if not db_user or not db_user.is_leader:
            await query.edit_message_text("❌ Access denied. Only leaders can approve withdrawals.")
            return
        
        # Get withdrawal
        withdrawal = WithdrawalService.get_withdrawal(db, withdrawal_id)
        if not withdrawal:
            await query.edit_message_text("❌ Withdrawal not found.")
            return
        
        if withdrawal.status != WithdrawalStatus.PENDING:
            await query.edit_message_text(f"❌ Withdrawal already {withdrawal.status.value.lower()}.")
            return
        
        # Get withdrawal user
        withdrawal_user = UserService.get_user(db, withdrawal.user_id)
        if not withdrawal_user:
            await query.edit_message_text("❌ User not found.")
            return
        
        # Check balance
        if withdrawal_user.balance < withdrawal.amount:
            await query.edit_message_text("❌ Error: User has insufficient balance for this withdrawal.")
            return
        
        # Update withdrawal status
        WithdrawalService.update_withdrawal_status(
            db, withdrawal_id, WithdrawalStatus.LEADER_APPROVED,
            admin_notes=f"Approved by {db_user.first_name}"
        )
        
        # Deduct the amount from user's balance
        UserService.update_balance(db, withdrawal_user.id, withdrawal_user.balance - withdrawal.amount)
        
        # Refresh withdrawal object
        withdrawal = WithdrawalService.get_withdrawal(db, withdrawal_id)
        withdrawal_user = UserService.get_user(db, withdrawal.user_id)
        
        # Update the message to show approval
        approval_text = (
            f"✅ **WITHDRAWAL APPROVED**\n\n"
            f"👤 User: {withdrawal_user.first_name or 'Unknown'} (@{withdrawal_user.username or 'no_username'})\n"
            f"💰 Amount: *${withdrawal.amount:.2f}*\n"
            f"💳 Method: *{withdrawal.withdrawal_method}*\n"
            f"📍 Address: `{withdrawal.withdrawal_address}`\n"
            f"👑 Approved by: {db_user.first_name} (@{db_user.username})\n"
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
        
        # Notify user of approval
        try:
            user_lang = 'en'
            
            approval_user_text = (
                f"✅ **Withdrawal Approved!**\n\n"
                f"💰 **Amount:** ${withdrawal.amount:.2f}\n"
                f"💳 **Method:** {withdrawal.withdrawal_method}\n"
                f"📍 **Address:** {withdrawal.withdrawal_address}\n"
                f"💸 **Amount deducted from balance**\n"
                f"💰 **New Balance:** ${withdrawal_user.balance:.2f}\n\n"
                f"🚀 **Status:** LEADER APPROVED ✅\n\n"
                f"⏳ Your payment is being processed and will be sent to your address shortly."
            )
            await context.bot.send_message(
                chat_id=withdrawal_user.telegram_user_id,
                text=approval_user_text,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Failed to notify user of withdrawal approval: {e}")
        
        # Log activity
        ActivityLogService.log_action(
            db, withdrawal.user_id, "WITHDRAWAL_APPROVED",
            f"Withdrawal ${withdrawal.amount:.2f} approved by leader {db_user.first_name}"
        )
            
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
        db_user = UserService.get_user_by_telegram_id(db, user.id)
        if not db_user or not db_user.is_leader:
            await query.edit_message_text("❌ Access denied. Only leaders can reject withdrawals.")
            return
        
        # Get withdrawal
        withdrawal = WithdrawalService.get_withdrawal(db, withdrawal_id)
        if not withdrawal:
            await query.edit_message_text("❌ Withdrawal not found.")
            return
        
        if withdrawal.status != WithdrawalStatus.PENDING:
            await query.edit_message_text(f"❌ Withdrawal already {withdrawal.status.value.lower()}.")
            return
        
        # Update withdrawal status
        WithdrawalService.update_withdrawal_status(
            db, withdrawal_id, WithdrawalStatus.REJECTED,
            admin_notes=f"Rejected by {db_user.first_name}"
        )
        
        # Get user who made the withdrawal
        withdrawal_user = UserService.get_user(db, withdrawal.user_id)
        
        # Update the message to show rejection
        rejection_text = (
            f"❌ **WITHDRAWAL REJECTED**\n\n"
            f"👤 User: {withdrawal_user.first_name or 'Unknown'} (@{withdrawal_user.username or 'no_username'})\n"
            f"💰 Amount: *${withdrawal.amount:.2f}*\n"
            f"💳 Method: *{withdrawal.withdrawal_method}*\n"
            f"📍 Address: `{withdrawal.withdrawal_address}`\n"
            f"👑 Rejected by: {db_user.first_name} (@{db_user.username})\n\n"
            f"❌ **Status:** REJECTED"
        )
        
        await query.edit_message_text(rejection_text, parse_mode='Markdown')
        
        # Notify user of rejection
        try:
            rejection_user_text = (
                f"❌ **Withdrawal Rejected**\n\n"
                f"💰 **Amount:** ${withdrawal.amount:.2f}\n"
                f"💳 **Method:** {withdrawal.withdrawal_method}\n"
                f"📍 **Address:** {withdrawal.withdrawal_address}\n\n"
                f"❌ **Status:** REJECTED ❌\n"
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
        ActivityLogService.log_action(
            db, withdrawal.user_id, "WITHDRAWAL_REJECTED",
            f"Withdrawal ${withdrawal.amount:.2f} rejected by leader {db_user.first_name}"
        )
            
    except Exception as e:
        logger.error(f"Error rejecting withdrawal: {e}")
        await query.edit_message_text("❌ Error processing rejection. Please try again.")
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
        db_user = UserService.get_user_by_telegram_id(db, user.id)
        if not db_user or not db_user.is_leader:
            await query.edit_message_text("❌ Access denied. Only leaders can mark withdrawals as paid.")
            return
        
        # Get withdrawal
        withdrawal = WithdrawalService.get_withdrawal(db, withdrawal_id)
        if not withdrawal:
            await query.edit_message_text("❌ Withdrawal not found.")
            return
        
        if withdrawal.status != WithdrawalStatus.LEADER_APPROVED:
            await query.edit_message_text(f"❌ Withdrawal must be approved first. Current status: {withdrawal.status.value}")
            return
        
        # Update withdrawal status
        WithdrawalService.update_withdrawal_status(
            db, withdrawal_id, WithdrawalStatus.COMPLETED,
            admin_notes=f"Payment completed by {db_user.first_name}"
        )
        
        # Get user who made the withdrawal
        withdrawal_user = UserService.get_user(db, withdrawal.user_id)
        
        # Update user's total withdrawn
        if withdrawal_user:
            UserService.update_user(
                db, withdrawal_user.id,
                total_withdrawn=withdrawal_user.total_withdrawn + withdrawal.amount
            )
        
        # Update the message to show completion
        completion_text = (
            f"✅ **WITHDRAWAL COMPLETED**\n\n"
            f"👤 User: {withdrawal_user.first_name or 'Unknown'} (@{withdrawal_user.username or 'no_username'})\n"
            f"💰 Amount: *${withdrawal.amount:.2f}*\n"
            f"💳 Method: *{withdrawal.withdrawal_method}*\n"
            f"📍 Address: `{withdrawal.withdrawal_address}`\n"
            f"💳 Completed by: {db_user.first_name} (@{db_user.username})\n\n"
            f"✅ **Status:** PAID & COMPLETED"
        )
        
        await query.edit_message_text(completion_text, parse_mode='Markdown')
        
        # Notify user of completion
        try:
            completion_user_text = (
                f"🎉 **Withdrawal Completed!**\n\n"
                f"💰 **Amount:** ${withdrawal.amount:.2f}\n"
                f"💳 **Method:** {withdrawal.withdrawal_method}\n"
                f"📍 **Address:** {withdrawal.withdrawal_address}\n\n"
                f"✅ **Status:** PAYMENT SENT! 🚀\n"
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
        ActivityLogService.log_action(
            db, withdrawal.user_id, "WITHDRAWAL_COMPLETED",
            f"Withdrawal ${withdrawal.amount:.2f} completed by leader {db_user.first_name}"
        )
            
    except Exception as e:
        logger.error(f"Error marking withdrawal as paid: {e}")
        await query.edit_message_text("❌ Error processing payment confirmation. Please try again.")
    finally:
        close_db_session(db)


async def handle_view_user_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle viewing user details from withdrawal context."""
    query = update.callback_query
    user = update.effective_user
    
    # Extract user telegram ID from callback data
    user_telegram_id = int(query.data.split("_")[-1])
    
    db = get_db_session()
    try:
        # Check if requester is a leader
        db_user = UserService.get_user_by_telegram_id(db, user.id)
        if not db_user or not db_user.is_leader:
            await query.edit_message_text("❌ Access denied. Only leaders can view user details.")
            return
        
        # Get target user
        target_user = UserService.get_user_by_telegram_id(db, user_telegram_id)
        if not target_user:
            await query.edit_message_text("❌ User not found.")
            return
        
        # Get user's withdrawals
        withdrawals = WithdrawalService.get_user_withdrawals(db, target_user.id, limit=5)
        
        details_text = f"""
👤 **User Details**

**Profile:**
• Name: {target_user.first_name or 'N/A'} {target_user.last_name or ''}
• Username: @{target_user.username or 'no_username'}
• User ID: `{target_user.telegram_user_id}`
• Status: {target_user.status.value}

**Financial:**
• Balance: ${target_user.balance:.2f}
• Total Earnings: ${target_user.total_earnings:.2f}
• Total Withdrawn: ${target_user.total_withdrawn:.2f}
• Accounts Sold: {target_user.total_accounts_sold}

**Recent Withdrawals:**
"""
        
        if withdrawals:
            for w in withdrawals:
                status_icon = "✅" if w.status == WithdrawalStatus.COMPLETED else "⏳"
                details_text += f"\n{status_icon} ${w.amount:.2f} - {w.status.value} - {w.created_at.strftime('%b %d')}"
        else:
            details_text += "\n_No withdrawals yet_"
        
        keyboard = [[InlineKeyboardButton("← Back", callback_data="leader_panel")]]
        await query.edit_message_text(
            details_text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        logger.error(f"Error viewing user details: {e}")
        await query.edit_message_text("❌ Error loading user details. Please try again.")
    finally:
        close_db_session(db)
