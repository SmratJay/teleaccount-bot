"""Admin command handlers for the Telegram Account Bot."""
import logging
import json
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ConversationHandler

from database import get_db_session, close_db_session
from database.operations import UserService, SystemSettingsService, ActivityLogService
from database.models import User, Withdrawal, AccountSale, UserStatus, SessionLog
from services.translation_service import translation_service

logger = logging.getLogger(__name__)

# Conversation states
BROADCAST_TEXT = 1
EDIT_USER_DATA = 2
USER_ID_INPUT = 3
USER_FIELD_SELECT = 4
USER_FIELD_VALUE = 5
BALANCE_USERNAME_INPUT = 6
BALANCE_AMOUNT_INPUT = 7

async def handle_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Main admin panel with all specified features."""
    user = update.effective_user
    
    # Load user's language from database
    from utils.helpers import load_user_language
    load_user_language(context, user.id)
    
    # Check if user is admin
    if not is_admin(user.id):
        await update.callback_query.answer("❌ Access denied.", show_alert=True)
        return
    
    admin_text = """
🔧 **ADMIN CONTROL PANEL**

**📢 Communication & Broadcasting:**
• Send messages to all users or targeted groups
• System announcements and updates

**👥 User Management:**
• Manually edit any user's data or status
• Update user status (Active, Frozen, Banned)
• View comprehensive user information

**📊 System Controls:**
• Account manipulation and configuration
• Monitor frozen/spam/OTP reports
• Session management and security

**🔧 Advanced Features:**
• IP/Proxy configuration management
• Activity logs and monitoring
• Security control settings

**Current System Status:** 🟢 All systems operational
    """
    
    keyboard = [
        [InlineKeyboardButton("📢 Mailing Mode", callback_data="admin_mailing")],
        [InlineKeyboardButton("👥 Manual User Edit", callback_data="admin_user_edit")],
        [InlineKeyboardButton("🛠️ Account Manipulation", callback_data="account_manipulation")],
        [InlineKeyboardButton("❄️ Account Freeze Management", callback_data="admin_freeze_panel")],
        [InlineKeyboardButton("📋 Sale Logs & Approval", callback_data="sale_logs_panel")],
        [InlineKeyboardButton("🔐 Session Management", callback_data="admin_sessions")],
        [InlineKeyboardButton("⚠️ Reports & Logs", callback_data="admin_reports")],
        [InlineKeyboardButton("🌐 IP/Proxy Config", callback_data="admin_proxy")],
        [InlineKeyboardButton("⚙️ System Settings", callback_data="admin_settings")],
        [InlineKeyboardButton("🔙 Back", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        admin_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def handle_admin_mailing(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle mailing mode - broadcast messages to all users."""
    await update.callback_query.answer()
    
    mailing_text = """
📢 **MAILING MODE - BROADCAST SYSTEM**

Send messages to all bot users or specific groups.

**Available Options:**
• 📡 **Broadcast to All Users** - Send to every user
• 🎯 **Target Active Users** - Send only to active users  
• ❄️ **Target Frozen Users** - Send to frozen users only
• 👑 **Leaders Only** - Send to leaders only

**Message Types:**
• System updates and announcements
• Maintenance notifications
• Feature updates
• Security alerts

Choose your broadcast option:
    """
    
    keyboard = [
        [InlineKeyboardButton("📡 Broadcast to All", callback_data="broadcast_all")],
        [InlineKeyboardButton("🎯 Active Users Only", callback_data="broadcast_active")],
        [InlineKeyboardButton("❄️ Frozen Users Only", callback_data="broadcast_frozen")],
        [InlineKeyboardButton("👑 Leaders Only", callback_data="broadcast_leaders")],
        [InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_panel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        mailing_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def start_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start broadcast process - prompt for message."""
    query = update.callback_query
    await query.answer()
    
    logger.info(f"🎯 BROADCAST: start_broadcast called by user {update.effective_user.id}")
    logger.info(f"🎯 BROADCAST: Callback data: {query.data}")
    
    broadcast_type = query.data.split("_")[1]  # Extract type from callback
    context.user_data['broadcast_type'] = broadcast_type
    
    logger.info(f"🎯 BROADCAST: Set broadcast_type to {broadcast_type} in context")
    
    type_names = {
        'all': 'All Users',
        'active': 'Active Users Only',
        'frozen': 'Frozen Users Only', 
        'leaders': 'Leaders Only'
    }
    
    target_name = type_names.get(broadcast_type, 'Users')
    
    input_text = f"""
📝 **COMPOSE BROADCAST MESSAGE**

**Target Audience:** {target_name}

**Instructions:**
• Type your message in the next message
• Use Markdown formatting if needed (**bold**, *italic*)
• Message will be sent to all {target_name.lower()}
• Be clear and professional

**Type your broadcast message now:**
    """
    
    keyboard = [
        [InlineKeyboardButton("❌ Cancel Broadcast", callback_data="admin_mailing")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        input_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    
    return BROADCAST_TEXT

async def process_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process and send broadcast message."""
    logger.info(f"🎯 BROADCAST: process_broadcast called by user {update.effective_user.id}")
    logger.info(f"🎯 BROADCAST: Message text: {update.message.text if update.message else 'NO MESSAGE'}")
    logger.info(f"🎯 BROADCAST: Context data: {context.user_data}")
    
    # 🔥 CRITICAL: Check if user is actually in broadcast mode
    broadcast_type = context.user_data.get('broadcast_type')
    if not broadcast_type:
        logger.warning(f"⚠️ BROADCAST: User {update.effective_user.id} not in broadcast mode, ignoring")
        return ConversationHandler.END
    
    broadcast_message = update.message.text
    
    # Show processing message
    processing_msg = await update.message.reply_text(
        "📡 **Processing Broadcast...**\n\n⏳ Preparing to send message...",
        parse_mode='Markdown'
    )
    
    db = get_db_session()
    try:
        # Get target users based on broadcast type
        if broadcast_type == 'all':
            users = db.query(User).all()
            target_desc = "all users"
        elif broadcast_type == 'active':
            users = db.query(User).filter(User.status == 'ACTIVE').all()
            target_desc = "active users"
        elif broadcast_type == 'frozen':
            users = db.query(User).filter(User.status == 'FROZEN').all()
            target_desc = "frozen users"
        elif broadcast_type == 'leaders':
            users = db.query(User).filter(User.is_leader == True).all()
            target_desc = "leaders"
        else:
            users = []
            target_desc = "no users"
        
        total_users = len(users)
        sent_count = 0
        failed_count = 0
        
        await processing_msg.edit_text(
            f"📡 **Broadcasting Message...**\n\n"
            f"📊 **Target:** {total_users} {target_desc}\n"
            f"✅ **Sent:** {sent_count}\n"
            f"❌ **Failed:** {failed_count}\n\n"
            f"⏳ Sending messages...",
            parse_mode='Markdown'
        )
        
        # Send message to all target users
        for i, user in enumerate(users):
            try:
                await context.bot.send_message(
                    chat_id=user.telegram_user_id,
                    text=f"📢 **System Announcement**\n\n{broadcast_message}",
                    parse_mode='Markdown'
                )
                sent_count += 1
                
                # Update progress every 10 users
                if i % 10 == 0:
                    await processing_msg.edit_text(
                        f"📡 **Broadcasting Message...**\n\n"
                        f"📊 **Target:** {total_users} {target_desc}\n"
                        f"✅ **Sent:** {sent_count}\n"
                        f"❌ **Failed:** {failed_count}\n\n"
                        f"⏳ Progress: {i+1}/{total_users}",
                        parse_mode='Markdown'
                    )
                
                # Rate limiting
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Failed to send broadcast to user {user.telegram_user_id}: {e}")
                failed_count += 1
        
        # Show final results
        success_text = f"""
✅ **BROADCAST COMPLETED**

📊 **Results Summary:**
• **Target Group:** {target_desc.title()}
• **Total Users:** {total_users}
• **Successfully Sent:** {sent_count}
• **Failed Deliveries:** {failed_count}
• **Success Rate:** {(sent_count/max(total_users,1)*100):.1f}%

**Message Sent:**
"{broadcast_message[:100]}{'...' if len(broadcast_message) > 100 else ''}"

🕒 **Completed at:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        keyboard = [
            [InlineKeyboardButton("📢 Send Another", callback_data="admin_mailing")],
            [InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_panel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await processing_msg.edit_text(
            success_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
        # Log admin activity
        admin_user = UserService.get_user_by_telegram_id(db, update.effective_user.id)
        if admin_user:
            ActivityLogService.log_action(
                db, admin_user.id, "ADMIN_BROADCAST",
                f"Broadcast sent to {sent_count} {target_desc}",
                extra_data=json.dumps({
                    "target_type": broadcast_type,
                    "message": broadcast_message[:200],
                    "sent_count": sent_count,
                    "failed_count": failed_count
                })
            )
        
        context.user_data.clear()
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"Error in broadcast: {e}")
        await processing_msg.edit_text(
            f"❌ **Broadcast Failed**\n\nError: {str(e)}\n\nPlease try again.",
            parse_mode='Markdown'
        )
        return ConversationHandler.END
    finally:
        close_db_session(db)

async def handle_admin_user_edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle manual user balance adjustment."""
    await update.callback_query.answer()
    
    edit_text = """
💰 **ADJUST USER BALANCE**

**Adjust Balance** - Add or subtract from user balance

Click the button below to start:
    """
    
    keyboard = [
        [InlineKeyboardButton("💰 Add/Subtract Balance", callback_data="adjust_balance_start")],
        [InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_panel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        edit_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    
    return ConversationHandler.END

# ========================================
# BALANCE ADJUSTMENT CONVERSATION
# ========================================

async def start_balance_adjustment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start balance adjustment conversation - ask for username."""
    await update.callback_query.answer()
    
    username_prompt = """
💰 **ADJUST USER BALANCE**

**Step 1/2:** Enter the username

Please enter the username (with @ symbol):

**Example:** `@johndoe`
    """
    
    keyboard = [[InlineKeyboardButton("❌ Cancel", callback_data="admin_user_edit")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        username_prompt,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    
    return BALANCE_USERNAME_INPUT

async def process_balance_username(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process username and ask for amount."""
    username_input = update.message.text.strip()
    
    # Remove @ if present
    if username_input.startswith('@'):
        username = username_input[1:]
    else:
        username = username_input
    
    # Find user in database
    db = get_db_session()
    try:
        target_user = db.query(User).filter(User.username == username).first()
        
        if not target_user:
            await update.message.reply_text(
                f"❌ **User Not Found**\n\nNo user found with username: `@{username}`\n\nPlease try again:",
                parse_mode='Markdown'
            )
            return BALANCE_USERNAME_INPUT
        
        # Store user info in context
        context.user_data['balance_adjust_user_id'] = target_user.telegram_user_id
        context.user_data['balance_adjust_username'] = username
        context.user_data['balance_adjust_current_balance'] = float(target_user.balance)
        
        amount_prompt = f"""
💰 **ADJUST BALANCE FOR @{username}**

**Current Balance:** \\${target_user.balance:.2f}

**Step 2/2:** Enter the amount

• Use **+** to add (e.g., `+50` adds $50)
• Use **-** to subtract (e.g., `-25` subtracts $25)

**Examples:**
• `+100` → Add $100
• `-50` → Subtract $50

**Enter amount:**
        """
        
        await update.message.reply_text(
            amount_prompt,
            parse_mode='Markdown'
        )
        
        return BALANCE_AMOUNT_INPUT
        
    except Exception as e:
        logger.error(f"Error finding user for balance adjustment: {e}")
        await update.message.reply_text(
            "❌ **Database Error**\n\nError occurred while searching for user. Try again.",
            parse_mode='Markdown'
        )
        return BALANCE_USERNAME_INPUT
    finally:
        close_db_session(db)

async def process_balance_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process amount and update balance in database."""
    amount_input = update.message.text.strip()
    
    # Parse amount (handle +/- prefix)
    try:
        if amount_input.startswith('+') or amount_input.startswith('-'):
            adjustment = float(amount_input)
            is_add = amount_input.startswith('+')
        else:
            await update.message.reply_text(
                "❌ **Invalid Format**\n\nPlease use **+** or **-** prefix.\n\n"
                "Examples: `+100` or `-50`\n\nTry again:",
                parse_mode='Markdown'
            )
            return BALANCE_AMOUNT_INPUT
    except ValueError:
        await update.message.reply_text(
            "❌ **Invalid Amount**\n\nPlease enter a valid number with + or - prefix.\n\n"
            "Examples: `+100` or `-50`\n\nTry again:",
            parse_mode='Markdown'
        )
        return BALANCE_AMOUNT_INPUT
    
    # Get user data from context
    target_user_id = context.user_data.get('balance_adjust_user_id')
    username = context.user_data.get('balance_adjust_username')
    current_balance = context.user_data.get('balance_adjust_current_balance', 0.0)
    
    if not target_user_id:
        await update.message.reply_text(
            "❌ **Session Error**\n\nPlease start again.",
            parse_mode='Markdown'
        )
        return ConversationHandler.END
    
    # Update balance in database
    db = get_db_session()
    try:
        target_user = UserService.get_user_by_telegram_id(db, target_user_id)
        
        if not target_user:
            await update.message.reply_text(
                "❌ **User Not Found**\n\nUser no longer exists.",
                parse_mode='Markdown'
            )
            return ConversationHandler.END
        
        # Calculate new balance
        old_balance = float(target_user.balance)
        new_balance = old_balance + adjustment
        
        # Prevent negative balance
        if new_balance < 0:
            await update.message.reply_text(
                f"❌ **Invalid Operation**\n\n"
                f"Cannot subtract \\${abs(adjustment):.2f} from \\${old_balance:.2f}\n"
                f"This would result in negative balance (\\${new_balance:.2f})\n\n"
                f"Please try a different amount.",
                parse_mode='Markdown'
            )
            return BALANCE_AMOUNT_INPUT
        
        # Update balance
        target_user.balance = new_balance
        db.commit()
        
        # Log admin activity
        admin_user = UserService.get_user_by_telegram_id(db, update.effective_user.id)
        if admin_user:
            action_type = "BALANCE_ADD" if is_add else "BALANCE_SUBTRACT"
            ActivityLogService.log_action(
                db, admin_user.id, action_type,
                f"Adjusted @{username}'s balance by ${adjustment:+.2f}",
                extra_data=json.dumps({
                    "target_user_id": target_user_id,
                    "username": username,
                    "old_balance": old_balance,
                    "adjustment": adjustment,
                    "new_balance": new_balance
                })
            )
        
        # Show success message
        action_word = "added" if is_add else "subtracted"
        success_text = f"""
✅ **BALANCE UPDATED SUCCESSFULLY**

**User:** @{username}
**Action:** {action_word.title()} \\${abs(adjustment):.2f}

**Balance Changes:**
• **Previous:** \\${old_balance:.2f}
• **Adjustment:** ${adjustment:+.2f}
• **New Balance:** \\${new_balance:.2f}

✅ Database updated in real-time!
        """
        
        keyboard = [
            [InlineKeyboardButton("💰 Adjust Another", callback_data="adjust_balance_start")],
            [InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_panel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            success_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
        # Clear context
        context.user_data.pop('balance_adjust_user_id', None)
        context.user_data.pop('balance_adjust_username', None)
        context.user_data.pop('balance_adjust_current_balance', None)
        
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"Error updating balance: {e}")
        await update.message.reply_text(
            f"❌ **Update Failed**\n\nError: {str(e)}\n\nPlease try again.",
            parse_mode='Markdown'
        )
        return ConversationHandler.END
    finally:
        close_db_session(db)

async def cancel_balance_adjustment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel balance adjustment conversation."""
    context.user_data.pop('balance_adjust_user_id', None)
    context.user_data.pop('balance_adjust_username', None)
    context.user_data.pop('balance_adjust_current_balance', None)
    
    await update.message.reply_text(
        "❌ **Balance Adjustment Cancelled**",
        parse_mode='Markdown'
    )
    return ConversationHandler.END

async def process_user_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process user ID input for editing."""
    user_input = update.message.text.strip()
    
    # Try to extract user ID (handle @username or plain ID)
    if user_input.startswith('@'):
        username = user_input[1:]
        context.user_data['search_username'] = username
        user_id = None
    else:
        try:
            user_id = int(user_input)
            context.user_data['edit_user_id'] = user_id
        except ValueError:
            await update.message.reply_text(
                "❌ **Invalid Input**\n\nPlease enter a valid Telegram User ID (numbers only) or @username.",
                parse_mode='Markdown'
            )
            return USER_ID_INPUT
    
    # Find user in database
    db = get_db_session()
    try:
        if user_id:
            target_user = UserService.get_user_by_telegram_id(db, user_id)
        else:
            target_user = db.query(User).filter(User.username == username).first()
        
        if not target_user:
            await update.message.reply_text(
                f"❌ **User Not Found**\n\nNo user found with ID/username: `{user_input}`\n\nTry again:",
                parse_mode='Markdown'
            )
            return USER_ID_INPUT
        
        context.user_data['edit_user_id'] = target_user.telegram_user_id
        
        # Show user details and edit options
        user_details = f"""
👤 **USER FOUND - EDIT OPTIONS**

**Current User Details:**
• **Name:** {target_user.first_name or 'N/A'} {target_user.last_name or ''}
• **Username:** @{target_user.username or 'none'}
• **Telegram ID:** `{target_user.telegram_user_id}`
• **Balance:** ${target_user.balance:.2f}
• **Status:** {target_user.status.value}
• **Is Admin:** {'✅ Yes' if target_user.is_admin else '❌ No'}
• **Is Leader:** {'✅ Yes' if target_user.is_leader else '❌ No'}
• **Accounts Sold:** {target_user.total_accounts_sold}
• **Total Earnings:** ${target_user.total_earnings:.2f}
• **Member Since:** {target_user.created_at.strftime('%Y-%m-%d')}

**What would you like to edit?**
        """
        
        keyboard = [
            [InlineKeyboardButton("💰 Edit Balance", callback_data="edit_balance")],
            [InlineKeyboardButton("📊 Change Status", callback_data="edit_status")],
            [InlineKeyboardButton("👤 Edit Name", callback_data="edit_name")],
            [InlineKeyboardButton("👑 Admin Rights", callback_data="edit_admin")],
            [InlineKeyboardButton("🏆 Leader Rights", callback_data="edit_leader")],
            [InlineKeyboardButton("🔄 Reset Stats", callback_data="edit_reset")],
            [InlineKeyboardButton("🔙 Back", callback_data="admin_user_edit")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            user_details,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
        return USER_FIELD_SELECT
        
    except Exception as e:
        logger.error(f"Error finding user: {e}")
        await update.message.reply_text(
            "❌ **Database Error**\n\nError occurred while searching for user. Try again.",
            parse_mode='Markdown'
        )
        return USER_ID_INPUT
    finally:
        close_db_session(db)

async def handle_field_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle user field selection for editing."""
    await update.callback_query.answer()
    
    field = update.callback_query.data.replace('edit_', '')
    context.user_data['edit_field'] = field
    
    if field == 'balance':
        await update.callback_query.edit_message_text(
            "💰 **EDIT BALANCE**\n\n"
            "Enter the new balance amount:\n"
            "• Enter a positive number to set balance\n"
            "• Use `+50` to add $50\n"
            "• Use `-50` to subtract $50\n\n"
            "Example: `100` or `+50` or `-25`",
            parse_mode='Markdown'
        )
        return USER_FIELD_VALUE
    
    elif field == 'status':
        keyboard = [
            [InlineKeyboardButton("✅ ACTIVE", callback_data="status_ACTIVE")],
            [InlineKeyboardButton("❄️ FROZEN", callback_data="status_FROZEN")],
            [InlineKeyboardButton("🚫 BANNED", callback_data="status_BANNED")],
            [InlineKeyboardButton("⏸️ SUSPENDED", callback_data="status_SUSPENDED")],
            [InlineKeyboardButton("🔙 Back", callback_data="admin_user_edit")]
        ]
        await update.callback_query.edit_message_text(
            "📊 **CHANGE USER STATUS**\n\nSelect new status:",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return USER_FIELD_VALUE
    
    elif field == 'name':
        await update.callback_query.edit_message_text(
            "👤 **EDIT NAME**\n\n"
            "Enter the new first name and last name separated by space:\n\n"
            "Example: `John Doe`",
            parse_mode='Markdown'
        )
        return USER_FIELD_VALUE
    
    elif field == 'admin':
        keyboard = [
            [InlineKeyboardButton("✅ Grant Admin", callback_data="toggle_admin_true")],
            [InlineKeyboardButton("❌ Revoke Admin", callback_data="toggle_admin_false")],
            [InlineKeyboardButton("🔙 Back", callback_data="admin_user_edit")]
        ]
        await update.callback_query.edit_message_text(
            "👑 **ADMIN RIGHTS**\n\nGrant or revoke admin privileges:",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return USER_FIELD_VALUE
    
    elif field == 'leader':
        keyboard = [
            [InlineKeyboardButton("✅ Grant Leader", callback_data="toggle_leader_true")],
            [InlineKeyboardButton("❌ Revoke Leader", callback_data="toggle_leader_false")],
            [InlineKeyboardButton("🔙 Back", callback_data="admin_user_edit")]
        ]
        await update.callback_query.edit_message_text(
            "🏆 **LEADER RIGHTS**\n\nGrant or revoke leader privileges:",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return USER_FIELD_VALUE
    
    elif field == 'reset':
        db = get_db_session()
        try:
            user_id = context.user_data.get('edit_user_id')
            target_user = UserService.get_user_by_telegram_id(db, user_id)
            if target_user:
                target_user.total_accounts_sold = 0
                target_user.total_earnings = 0.0
                db.commit()
                
                await update.callback_query.edit_message_text(
                    f"✅ **STATS RESET**\n\n"
                    f"User @{target_user.username} statistics have been reset to zero.",
                    parse_mode='Markdown'
                )
                
                # Log action
                admin_user = UserService.get_user_by_telegram_id(db, update.effective_user.id)
                if admin_user:
                    ActivityLogService.log_action(
                        db, admin_user.id, "ADMIN_USER_EDIT",
                        f"Reset stats for user {user_id}",
                        extra_data=json.dumps({"target_user_id": user_id, "field": "stats_reset"})
                    )
            return ConversationHandler.END
        finally:
            close_db_session(db)

async def process_field_value(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process the new field value."""
    field = context.user_data.get('edit_field')
    user_id = context.user_data.get('edit_user_id')
    new_value = update.message.text.strip()
    
    db = get_db_session()
    try:
        target_user = UserService.get_user_by_telegram_id(db, user_id)
        if not target_user:
            await update.message.reply_text("❌ User not found.")
            return ConversationHandler.END
        
        if field == 'balance':
            try:
                if new_value.startswith('+'):
                    # Add to balance
                    amount = float(new_value[1:])
                    target_user.balance += amount
                    action_desc = f"Added ${amount:.2f} to balance"
                elif new_value.startswith('-'):
                    # Subtract from balance
                    amount = float(new_value[1:])
                    target_user.balance -= amount
                    action_desc = f"Subtracted ${amount:.2f} from balance"
                else:
                    # Set balance
                    target_user.balance = float(new_value)
                    action_desc = f"Set balance to ${float(new_value):.2f}"
                
                db.commit()
                
                await update.message.reply_text(
                    f"✅ **BALANCE UPDATED**\n\n"
                    f"User: @{target_user.username}\n"
                    f"New Balance: ${target_user.balance:.2f}\n\n"
                    f"{action_desc}",
                    parse_mode='Markdown'
                )
                
                # Log action
                admin_user = UserService.get_user_by_telegram_id(db, update.effective_user.id)
                if admin_user:
                    ActivityLogService.log_action(
                        db, admin_user.id, "ADMIN_USER_EDIT",
                        f"Updated balance for user {user_id}: {action_desc}",
                        extra_data=json.dumps({
                            "target_user_id": user_id,
                            "field": "balance",
                            "new_value": target_user.balance
                        })
                    )
                    
            except ValueError:
                await update.message.reply_text(
                    "❌ Invalid amount. Please enter a valid number.",
                    parse_mode='Markdown'
                )
                return USER_FIELD_VALUE
        
        elif field == 'name':
            parts = new_value.split(' ', 1)
            target_user.first_name = parts[0]
            target_user.last_name = parts[1] if len(parts) > 1 else ''
            db.commit()
            
            await update.message.reply_text(
                f"✅ **NAME UPDATED**\n\n"
                f"User: @{target_user.username}\n"
                f"New Name: {target_user.first_name} {target_user.last_name}",
                parse_mode='Markdown'
            )
            
            # Log action
            admin_user = UserService.get_user_by_telegram_id(db, update.effective_user.id)
            if admin_user:
                ActivityLogService.log_action(
                    db, admin_user.id, "ADMIN_USER_EDIT",
                    f"Updated name for user {user_id}",
                    extra_data=json.dumps({
                        "target_user_id": user_id,
                        "field": "name",
                        "new_value": f"{target_user.first_name} {target_user.last_name}"
                    })
                )
        
        context.user_data.clear()
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"Error updating field: {e}")
        await update.message.reply_text(
            f"❌ **Error**\n\n{str(e)}",
            parse_mode='Markdown'
        )
        return ConversationHandler.END
    finally:
        close_db_session(db)

async def handle_status_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle status selection."""
    await update.callback_query.answer()
    
    status = update.callback_query.data.replace('status_', '')
    user_id = context.user_data.get('edit_user_id')
    
    db = get_db_session()
    try:
        target_user = UserService.get_user_by_telegram_id(db, user_id)
        if target_user:
            old_status = target_user.status
            target_user.status = status
            db.commit()
            
            await update.callback_query.edit_message_text(
                f"✅ **STATUS UPDATED**\n\n"
                f"User: @{target_user.username}\n"
                f"Old Status: {old_status}\n"
                f"New Status: {status}",
                parse_mode='Markdown'
            )
            
            # Log action
            admin_user = UserService.get_user_by_telegram_id(db, update.effective_user.id)
            if admin_user:
                ActivityLogService.log_action(
                    db, admin_user.id, "ADMIN_USER_EDIT",
                    f"Changed status for user {user_id} from {old_status} to {status}",
                    extra_data=json.dumps({
                        "target_user_id": user_id,
                        "field": "status",
                        "old_value": old_status,
                        "new_value": status
                    })
                )
        
        context.user_data.clear()
        return ConversationHandler.END
    finally:
        close_db_session(db)

async def handle_toggle_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle admin/leader toggle."""
    await update.callback_query.answer()
    
    action = update.callback_query.data  # toggle_admin_true, toggle_admin_false, etc.
    parts = action.split('_')
    privilege_type = parts[1]  # 'admin' or 'leader'
    new_value = parts[2] == 'true'  # True or False
    
    user_id = context.user_data.get('edit_user_id')
    
    db = get_db_session()
    try:
        target_user = UserService.get_user_by_telegram_id(db, user_id)
        if target_user:
            if privilege_type == 'admin':
                target_user.is_admin = new_value
                field_name = "Admin Rights"
            else:
                target_user.is_leader = new_value
                field_name = "Leader Rights"
            
            db.commit()
            
            await update.callback_query.edit_message_text(
                f"✅ **{field_name.upper()} UPDATED**\n\n"
                f"User: @{target_user.username}\n"
                f"{field_name}: {'✅ Granted' if new_value else '❌ Revoked'}",
                parse_mode='Markdown'
            )
            
            # Log action
            admin_user = UserService.get_user_by_telegram_id(db, update.effective_user.id)
            if admin_user:
                ActivityLogService.log_action(
                    db, admin_user.id, "ADMIN_USER_EDIT",
                    f"{'Granted' if new_value else 'Revoked'} {privilege_type} for user {user_id}",
                    extra_data=json.dumps({
                        "target_user_id": user_id,
                        "field": privilege_type,
                        "new_value": new_value
                    })
                )
        
        context.user_data.clear()
        return ConversationHandler.END
    finally:
        close_db_session(db)

async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel any active conversation and clear context."""
    context.user_data.clear()
    logger.info(f"🔥 Conversation cancelled for user {update.effective_user.id}, context cleared")
    return ConversationHandler.END

def is_admin(user_id: int) -> bool:
    """Check if user is an admin based on environment variables."""
    from utils.helpers import is_admin as check_admin
    return check_admin(user_id)

def setup_admin_handlers(application) -> None:
    """Set up admin handlers."""
    # Main admin panel handler
    application.add_handler(CallbackQueryHandler(handle_admin_panel, pattern='^admin_panel$'))
    
    # Admin sub-handlers
    application.add_handler(CallbackQueryHandler(handle_admin_mailing, pattern='^admin_mailing$'))
    
    # Broadcast conversation handler
    broadcast_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_broadcast, pattern='^broadcast_(all|active|frozen|leaders)$')
        ],
        states={
            BROADCAST_TEXT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_broadcast)
            ]
        },
        fallbacks=[
            CallbackQueryHandler(handle_admin_mailing, pattern='^admin_mailing$'),
            CallbackQueryHandler(handle_admin_panel, pattern='^admin_panel$'),
            CommandHandler('start', cancel_conversation),
            CommandHandler('cancel', cancel_conversation)
        ],
        name="admin_broadcast_conversation",
        per_user=True,
        per_chat=True,
        allow_reentry=True,
        conversation_timeout=300  # 5 minutes timeout
    )
    application.add_handler(broadcast_conv)
    
    # User edit conversation handler
    user_edit_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(handle_admin_user_edit, pattern='^admin_user_edit$')
        ],
        states={
            USER_ID_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_user_id)
            ],
            USER_FIELD_SELECT: [
                CallbackQueryHandler(handle_field_selection, pattern='^edit_(balance|status|name|admin|leader|reset)$')
            ],
            USER_FIELD_VALUE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_field_value),
                CallbackQueryHandler(handle_status_selection, pattern='^status_(ACTIVE|FROZEN|BANNED|SUSPENDED)$'),
                CallbackQueryHandler(handle_toggle_admin, pattern='^toggle_(admin|leader)$')
            ]
        },
        fallbacks=[
            CallbackQueryHandler(handle_admin_panel, pattern='^admin_panel$'),
            CommandHandler('start', cancel_conversation),
            CommandHandler('cancel', cancel_conversation)
        ],
        per_user=True,
        per_chat=True,
        allow_reentry=True,
        conversation_timeout=300  # 5 minutes timeout
    )
    application.add_handler(user_edit_conv)
    
    # Balance adjustment conversation handler
    balance_adjust_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_balance_adjustment, pattern='^adjust_balance_start$')
        ],
        states={
            BALANCE_USERNAME_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_balance_username)
            ],
            BALANCE_AMOUNT_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_balance_amount)
            ]
        },
        fallbacks=[
            CallbackQueryHandler(handle_admin_user_edit, pattern='^admin_user_edit$'),
            CallbackQueryHandler(handle_admin_panel, pattern='^admin_panel$'),
            CommandHandler('start', cancel_balance_adjustment),
            CommandHandler('cancel', cancel_balance_adjustment)
        ],
        name="balance_adjustment_conversation",
        per_user=True,
        per_chat=True,
        allow_reentry=True,
        conversation_timeout=300  # 5 minutes timeout
    )
    application.add_handler(balance_adjust_conv)
    
    # Account Freeze Management handlers
    application.add_handler(CallbackQueryHandler(handle_account_freeze_panel, pattern='^admin_freeze_panel$'))
    application.add_handler(CallbackQueryHandler(handle_view_frozen_accounts, pattern='^view_frozen_accounts$'))
    
    # Sale Logs & Approval handlers
    application.add_handler(CallbackQueryHandler(handle_sale_logs_panel, pattern='^sale_logs_panel$'))
    application.add_handler(CallbackQueryHandler(handle_approve_sale_list, pattern='^approve_sale_list$'))
    application.add_handler(CallbackQueryHandler(handle_approve_sale_action, pattern='^approve_sale_\\d+$'))
    application.add_handler(CallbackQueryHandler(handle_reject_sale_action, pattern='^reject_sale_\\d+$'))
    
    # Session Management handlers
    application.add_handler(CallbackQueryHandler(handle_session_management, pattern='^admin_sessions$'))
    application.add_handler(CallbackQueryHandler(handle_terminate_user_sessions, pattern='^terminate_user_sessions$'))
    application.add_handler(CallbackQueryHandler(handle_view_user_sessions, pattern='^view_user_sessions_\\d+$'))
    application.add_handler(CallbackQueryHandler(handle_terminate_specific_session, pattern='^terminate_session_\\d+$'))
    application.add_handler(CallbackQueryHandler(handle_terminate_all_user_sessions, pattern='^terminate_all_user_sessions_\\d+$'))
    application.add_handler(CallbackQueryHandler(handle_terminate_sessions_confirm, pattern='^terminate_sessions_\\d+$'))
    application.add_handler(CallbackQueryHandler(handle_view_session_holds, pattern='^view_session_holds$'))
    application.add_handler(CallbackQueryHandler(handle_release_all_holds, pattern='^release_all_holds$'))
    application.add_handler(CallbackQueryHandler(handle_session_activity_logs, pattern='^session_activity_logs$'))
    
    # Account Manipulation conversation handler
    account_manip_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(handle_account_manipulation_panel, pattern='^account_manipulation$')
        ],
        states={
            ACCOUNT_SELECT: [
                CallbackQueryHandler(handle_manipulation_account_select, pattern='^manipulate_account_\\d+$')
            ],
            MANIPULATION_ACTION: [
                CallbackQueryHandler(handle_delete_history_action, pattern='^manip_delete_history$'),
                CallbackQueryHandler(handle_change_name_start, pattern='^manip_change_name$'),
                CallbackQueryHandler(handle_change_username_start, pattern='^manip_change_username$'),
                CallbackQueryHandler(handle_profile_photo_menu, pattern='^manip_profile_photo$'),
                CallbackQueryHandler(handle_2fa_menu, pattern='^manip_2fa$'),
                CallbackQueryHandler(handle_view_account_info, pattern='^manip_view_info$'),
                CallbackQueryHandler(handle_manipulation_account_select, pattern='^manipulate_account_\\d+$'),
                CallbackQueryHandler(handle_account_manipulation_panel, pattern='^account_manipulation$')
            ],
            NAME_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_name_input)
            ],
            USERNAME_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_username_input)
            ],
            PHOTO_SELECT: [
                CallbackQueryHandler(handle_upload_photo, pattern='^upload_photo_'),
                CallbackQueryHandler(handle_delete_all_photos, pattern='^delete_all_photos$'),
                CallbackQueryHandler(handle_profile_photo_menu, pattern='^manip_profile_photo$'),
                CallbackQueryHandler(handle_manipulation_account_select, pattern='^manipulate_account_\\d+$')
            ]
        },
        fallbacks=[
            CallbackQueryHandler(handle_admin_panel, pattern='^admin_panel$'),
            CommandHandler('start', cancel_conversation),
            CommandHandler('cancel', cancel_conversation)
        ],
        per_user=True,
        per_chat=True,
        allow_reentry=True,
        conversation_timeout=600  # 10 minutes timeout for account operations
    )
    application.add_handler(account_manip_conv)
    
    # Proxy/IP Configuration handlers
    application.add_handler(CallbackQueryHandler(handle_admin_proxy_panel, pattern='^admin_proxy$'))
    application.add_handler(CallbackQueryHandler(handle_force_proxy_rotation, pattern='^force_proxy_rotation$'))
    application.add_handler(CallbackQueryHandler(handle_proxy_health_check, pattern='^proxy_health_check$'))
    application.add_handler(CallbackQueryHandler(handle_view_proxy_pool, pattern='^view_proxy_pool$'))
    application.add_handler(CallbackQueryHandler(handle_refresh_proxy_sources, pattern='^refresh_proxy_sources$'))
    application.add_handler(CallbackQueryHandler(handle_clean_free_proxies, pattern='^clean_free_proxies$'))
    
    # Reports & Logs handlers
    from handlers.reports_logs_handlers import (
        handle_admin_reports,
        handle_view_activity_logs,
        handle_view_sales_report,
        handle_view_user_report,
        handle_view_revenue_report
    )
    application.add_handler(CallbackQueryHandler(handle_admin_reports, pattern='^admin_reports$'))
    application.add_handler(CallbackQueryHandler(handle_view_activity_logs, pattern='^view_activity_logs$'))
    application.add_handler(CallbackQueryHandler(handle_view_sales_report, pattern='^view_sales_report$'))
    application.add_handler(CallbackQueryHandler(handle_view_user_report, pattern='^view_user_report$'))
    application.add_handler(CallbackQueryHandler(handle_view_revenue_report, pattern='^view_revenue_report$'))
    
    # System Settings handlers
    from handlers.system_settings_handlers import (
        handle_admin_settings,
        handle_settings_bot_config,
        handle_settings_financial,
        handle_settings_security,
        handle_settings_maintenance,
        handle_toggle_verification,
        handle_toggle_captcha,
        handle_toggle_channel_verification,
        handle_clear_old_logs,
        handle_view_db_stats
    )
    from handlers.system_settings_handlers_additional import (
        handle_view_all_admins,
        handle_view_all_leaders,
        get_add_admin_conversation,
        get_remove_admin_conversation
    )
    application.add_handler(CallbackQueryHandler(handle_admin_settings, pattern='^admin_settings$'))
    application.add_handler(CallbackQueryHandler(handle_settings_bot_config, pattern='^settings_bot_config$'))
    application.add_handler(CallbackQueryHandler(handle_settings_financial, pattern='^settings_financial$'))
    application.add_handler(CallbackQueryHandler(handle_settings_security, pattern='^settings_security$'))
    application.add_handler(CallbackQueryHandler(handle_settings_maintenance, pattern='^settings_maintenance$'))
    application.add_handler(CallbackQueryHandler(handle_toggle_verification, pattern='^toggle_verification$'))
    application.add_handler(CallbackQueryHandler(handle_toggle_captcha, pattern='^toggle_captcha$'))
    application.add_handler(CallbackQueryHandler(handle_toggle_channel_verification, pattern='^toggle_channel_verification$'))
    application.add_handler(CallbackQueryHandler(handle_clear_old_logs, pattern='^clear_old_logs$'))
    application.add_handler(CallbackQueryHandler(handle_view_db_stats, pattern='^view_db_stats$'))
    application.add_handler(CallbackQueryHandler(handle_view_all_admins, pattern='^view_all_admins$'))
    application.add_handler(CallbackQueryHandler(handle_view_all_leaders, pattern='^view_all_leaders$'))
    
    # Admin management conversations
    application.add_handler(get_add_admin_conversation())
    application.add_handler(get_remove_admin_conversation())

    logger.info("Admin handlers set up successfully")# Additional handler functions will be implemented...
async def handle_field_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle field selection for user editing."""
    # Implementation will continue...
    pass

async def process_field_value(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process new field value."""
    # Implementation will continue...
    pass

async def handle_status_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle status selection."""
    # Implementation will continue...
    pass

async def handle_toggle_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle admin/leader toggle."""
    # Implementation will continue...
    pass

# ==================== ACCOUNT FREEZE MANAGEMENT PANEL ====================

async def handle_account_freeze_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    '''Show account freeze management panel.'''
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    if not is_admin(user.id):
        await query.edit_message_text('❌ Access denied. Admin privileges required.')
        return
    
    from database import get_db_session, close_db_session
    from services.account_management import account_manager
    
    db = get_db_session()
    try:
        # Get frozen accounts statistics
        frozen_accounts = account_manager.get_frozen_accounts(db, limit=100)
        
        freeze_text = f'''
❄️ **ACCOUNT FREEZE MANAGEMENT**

**Current Status:**
• 🧊 **Frozen Accounts:** {len(frozen_accounts)}
• 🔄 **Auto-Freeze Enabled:** ✅ Multi-device detection
• ⏱️ **Default Duration:** 24 hours

**Available Actions:**
• View all frozen accounts
• Manually freeze an account
• Unfreeze an account
• View freeze history

**System Features:**
• Automatic freeze on multi-device detection
• Admin-initiated manual freezes
• Timed auto-release for expired freezes
• Complete audit logging

Choose an action below:
        '''
        
        keyboard = [
            [InlineKeyboardButton('🧊 View Frozen Accounts', callback_data='view_frozen_accounts')],
            [InlineKeyboardButton('❄️ Freeze Account', callback_data='manual_freeze_account')],
            [InlineKeyboardButton('🔥 Unfreeze Account', callback_data='manual_unfreeze_account')],
            [InlineKeyboardButton('📊 Freeze Statistics', callback_data='freeze_statistics')],
            [InlineKeyboardButton('🔙 Back to Admin', callback_data='admin_panel')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(freeze_text, parse_mode='Markdown', reply_markup=reply_markup)
    finally:
        close_db_session(db)


# ------------------ Proxy admin handlers (top-level) ------------------
async def handle_admin_proxy_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin panel for proxy/IP configuration and rotation controls."""
    query = update.callback_query
    await query.answer()

    user = update.effective_user
    if not is_admin(user.id):
        await query.edit_message_text('❌ Access denied.')
        return

    from services.proxy_manager import proxy_manager
    from services.daily_proxy_rotator import daily_proxy_rotator

    # Get proxy stats and rotation status
    proxy_stats = proxy_manager.get_proxy_stats() or {}
    rotation_status = daily_proxy_rotator.get_rotation_status() or {}

    stats_text = (
        "🌐 **IP/Proxy Configuration & Rotation**\n\n"
        f"**Proxy Pool Stats:**\n• Total Proxies: {proxy_stats.get('total_proxies', 0)}\n"
        f"• Active: {proxy_stats.get('active_proxies', 0)}\n"
        f"• Inactive: {proxy_stats.get('inactive_proxies', 0)}\n"
        f"• Last Health Check: {proxy_stats.get('last_health_check', 'N/A')}\n\n"
        "**Rotation Status:**\n"
        f"• Running: {'✅' if rotation_status.get('is_running') else '❌'}\n"
        f"• Last Rotation: {rotation_status.get('last_rotation', 'N/A')}\n"
        f"• Next Rotation: {rotation_status.get('next_rotation', 'N/A')}\n"
        f"• Interval: {rotation_status.get('rotation_interval_hours', 24)}h\n"
    )

    keyboard = [
        [InlineKeyboardButton('🔄 Force Proxy Rotation', callback_data='force_proxy_rotation')],
        [InlineKeyboardButton('🔬 Health Check', callback_data='proxy_health_check')],
        [InlineKeyboardButton('📊 View Proxy Pool', callback_data='view_proxy_pool')],
        [InlineKeyboardButton('➕ Refresh from Sources', callback_data='refresh_proxy_sources')],
        [InlineKeyboardButton('🧹 Clean Free Proxies', callback_data='clean_free_proxies')],
        [InlineKeyboardButton('🔙 Back to Admin', callback_data='admin_panel')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(stats_text, parse_mode='Markdown', reply_markup=reply_markup)


async def handle_force_proxy_rotation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    from services.daily_proxy_rotator import force_proxy_rotation
    result = await force_proxy_rotation()

    msg = (
        "🔄 **Proxy Rotation Triggered**\n\n"
        f"Status: {result.get('status')}\n"
        f"Cleaned Proxies: {result.get('rotation', {}).get('cleaned_proxies', 'N/A')}\n"
        f"Refresh Success: {'✅' if result.get('rotation', {}).get('refresh_success') else '❌'}\n"
    )

    await query.edit_message_text(msg, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 Back', callback_data='admin_proxy')]]))


async def handle_proxy_health_check(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    from services.proxy_manager import proxy_manager
    result = proxy_manager.perform_health_check()

    msg = (
        "🔬 **Proxy Health Check**\n\n"
        f"Status: {result.get('status')}\n"
        f"Active Proxies: {result.get('active_proxies', 'N/A')}\n"
        f"Tested: {result.get('tested_count', 'N/A')}\n"
        f"Working: {result.get('working_count', 'N/A')}\n"
        f"Success Rate: {result.get('success_rate', 0):.2%}\n"
    )

    await query.edit_message_text(msg, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 Back', callback_data='admin_proxy')]]))


async def handle_view_proxy_pool(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """View all proxies in the pool with details."""
    query = update.callback_query
    await query.answer()
    
    from database import get_db_session, close_db_session
    from database.operations import ProxyService
    
    db = get_db_session()
    try:
        proxies = ProxyService.get_all_proxies(db, include_inactive=True)
        
        if not proxies:
            msg = "⚠️ **No Proxies in Pool**\n\nThe proxy pool is currently empty.\n\nUse 'Refresh from Sources' to fetch new proxies."
        else:
            active_count = sum(1 for p in proxies if p.is_active)
            msg = f"📊 **Proxy Pool Details**\n\nTotal: {len(proxies)} | Active: {active_count} | Inactive: {len(proxies) - active_count}\n\n"
            
            # Show first 10 proxies
            for proxy in proxies[:10]:
                status = "✅" if proxy.is_active else "❌"
                msg += f"{status} **{proxy.ip_address}:{proxy.port}**\n"
                msg += f"   └ {proxy.country_code or 'Unknown'} | {proxy.provider or 'free'} | Score: {proxy.reputation_score}\n"
            
            if len(proxies) > 10:
                msg += f"\n_...and {len(proxies) - 10} more proxies_"
        
        await query.edit_message_text(msg, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 Back', callback_data='admin_proxy')]]))
    finally:
        close_db_session(db)


async def handle_refresh_proxy_sources(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Refresh proxy pool from all sources."""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text("🔄 **Refreshing Proxy Pool...**\n\nFetching from all enabled sources...", parse_mode='Markdown')
    
    try:
        from services.proxy_scheduler import refresh_proxies_now
        results = await refresh_proxies_now()
        
        webshare = results.get('webshare', {})
        free_sources = results.get('free_sources', {})
        cleanup = results.get('cleanup', {})
        
        msg = "✅ **Proxy Refresh Complete**\n\n"
        
        if webshare.get('enabled'):
            status = "✅" if webshare.get('success') else "❌"
            msg += f"{status} **WebShare.io**: {webshare.get('count', 0)} proxies\n"
        
        if free_sources.get('enabled'):
            status = "✅" if free_sources.get('success') else "❌"
            msg += f"{status} **Free Sources**: {free_sources.get('count', 0)} proxies\n"
        
        msg += f"\n🧹 Cleanup: {cleanup.get('removed', 0)} old proxies removed\n"
        
        from database import get_db_session, close_db_session
        from database.operations import ProxyService
        db = get_db_session()
        stats = ProxyService.get_proxy_stats(db)
        close_db_session(db)
        
        msg += f"\n📊 **Current Pool**: {stats.get('total_proxies', 0)} total | {stats.get('active_proxies', 0)} active"
        
        await query.edit_message_text(msg, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 Back', callback_data='admin_proxy')]]))
    except Exception as e:
        logger.error(f"Refresh proxy sources failed: {e}")
        await query.edit_message_text(f"❌ **Refresh Failed**\n\nError: {str(e)}", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 Back', callback_data='admin_proxy')]]))


async def handle_clean_free_proxies(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Remove all free proxies (non-WebShare) from the database."""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text("🧹 **Cleaning Free Proxies...**\n\nRemoving all non-WebShare proxies...", parse_mode='Markdown')
    
    try:
        from database import get_db_session, close_db_session
        from database.operations import ProxyService
        
        db = get_db_session()
        try:
            # Get stats before cleanup
            before_stats = ProxyService.get_proxy_stats(db)
            before_total = before_stats.get('total_proxies', 0)
            
            # Remove free proxies
            removed_count = ProxyService.remove_free_proxies(db)
            
            # Get stats after cleanup
            after_stats = ProxyService.get_proxy_stats(db)
            after_total = after_stats.get('total_proxies', 0)
            
            msg = (
                "✅ **Free Proxies Cleaned**\n\n"
                f"**Removed:** {removed_count} free proxies\n"
                f"**Before:** {before_total} total proxies\n"
                f"**After:** {after_total} total proxies\n\n"
                f"**Remaining:** Only premium WebShare.io proxies\n\n"
                "ℹ️ Free proxy sources are now disabled by default.\n"
                "Only WebShare.io proxies will be fetched during auto-refresh."
            )
            
            await query.edit_message_text(msg, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 Back', callback_data='admin_proxy')]]))
            
        finally:
            close_db_session(db)
            
    except Exception as e:
        logger.error(f"Clean free proxies failed: {e}")
        await query.edit_message_text(
            f"❌ **Cleanup Failed**\n\nError: {str(e)}", 
            parse_mode='Markdown', 
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 Back', callback_data='admin_proxy')]])
        )

# ----------------------------------------------------------------------

async def handle_view_frozen_accounts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    '''Show list of all frozen accounts.'''
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    if not is_admin(user.id):
        await query.edit_message_text('❌ Access denied.')
        return
    
    from database import get_db_session, close_db_session
    from services.account_management import account_manager
    
    db = get_db_session()
    try:
        frozen_accounts = account_manager.get_frozen_accounts(db, limit=20)
        
        if not frozen_accounts:
            text = '''
✅ **NO FROZEN ACCOUNTS**

There are currently no frozen accounts in the system.

All accounts are in normal operational status.
            '''
            keyboard = [[InlineKeyboardButton('🔙 Back', callback_data='admin_freeze_panel')]]
        else:
            text = f'''
🧊 **FROZEN ACCOUNTS LIST** ({len(frozen_accounts)})

'''
            for acc in frozen_accounts[:15]:  # Show first 15
                freeze_emoji = '⏱️' if acc.freeze_duration_hours else '🔒'
                duration_text = f'{acc.freeze_duration_hours}h' if acc.freeze_duration_hours else 'Indefinite'
                
                text += f'''
{freeze_emoji} **{acc.phone_number}**
├ Reason: {acc.freeze_reason or 'No reason specified'}
├ Duration: {duration_text}
├ Frozen: {acc.freeze_timestamp.strftime('%Y-%m-%d %H:%M') if acc.freeze_timestamp else 'Unknown'}
└ [Unfreeze](callback_data=unfreeze_{acc.id})

'''
            
            keyboard = [
                [InlineKeyboardButton('🔥 Unfreeze Selected', callback_data='select_unfreeze')],
                [InlineKeyboardButton('🔄 Refresh List', callback_data='view_frozen_accounts')],
                [InlineKeyboardButton('🔙 Back', callback_data='admin_freeze_panel')]
            ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)
        
    finally:
        close_db_session(db)

# ==================== SALE LOGS & APPROVAL PANEL ====================

async def handle_sale_logs_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    '''Show sale logs management panel with pending approvals.'''
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    if not is_admin(user.id):
        await query.edit_message_text('❌ Access denied. Admin privileges required.')
        return
    
    from database import get_db_session, close_db_session
    from database.sale_log_operations import sale_log_service
    
    db = get_db_session()
    try:
        # Get pending sale logs
        pending_logs = sale_log_service.get_pending_sale_logs(db, include_frozen=True, limit=50)
        
        # Separate frozen and non-frozen
        frozen_pending = [log for log in pending_logs if log.account_is_frozen]
        active_pending = [log for log in pending_logs if not log.account_is_frozen]
        
        # Get statistics
        stats = sale_log_service.get_sale_log_statistics(db)
        
        logs_text = f'''
📋 **SALE LOGS & APPROVAL SYSTEM**

**📊 Statistics:**
• ⏳ **Pending Approval:** {stats.get('pending', 0)}
• ✅ **Approved:** {stats.get('approved', 0)}
• ❌ **Rejected:** {stats.get('rejected', 0)}
• ❄️ **Frozen (Pending):** {len(frozen_pending)}
• 🟢 **Active (Pending):** {len(active_pending)}

**⚠️ FROZEN ACCOUNTS:**
Frozen accounts **CANNOT** be approved until unfrozen.

**Recent Pending Sales:**
'''
        
        if not pending_logs:
            logs_text += '\\n✅ No pending sales requiring approval.\\n'
        else:
            for i, log in enumerate(pending_logs[:10], 1):  # Show first 10
                freeze_indicator = '❄️' if log.account_is_frozen else '🟢'
                
                logs_text += f'''
{i}. {freeze_indicator} **{log.account_phone}**
   Seller: @{log.seller_username or 'Unknown'} ({log.seller_name})
   Price: \
   Status: {log.status.value}
   {'⚠️ FROZEN: ' + (log.account_freeze_reason or 'No reason') if log.account_is_frozen else ''}

'''
        
        keyboard = [
            [InlineKeyboardButton(f'✅ Approve Sales ({len(active_pending)})', callback_data='approve_sale_list')],
            [InlineKeyboardButton(f'❌ Reject Sales', callback_data='reject_sale_list')],
            [InlineKeyboardButton('🔍 Search Logs', callback_data='search_sale_logs')],
            [InlineKeyboardButton('📊 Detailed Stats', callback_data='sale_logs_stats')],
            [InlineKeyboardButton('🔙 Back to Admin', callback_data='admin_panel')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(logs_text, parse_mode='Markdown', reply_markup=reply_markup)
        
    finally:
        close_db_session(db)

async def handle_approve_sale_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    '''Show list of sales that can be approved (not frozen).'''
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    if not is_admin(user.id):
        await query.edit_message_text('❌ Access denied.')
        return
    
    from database import get_db_session, close_db_session
    from database.sale_log_operations import sale_log_service
    
    db = get_db_session()
    try:
        pending_logs = sale_log_service.get_pending_sale_logs(db, include_frozen=False, limit=20)
        
        if not pending_logs:
            text = '''
✅ **NO SALES TO APPROVE**

All pending sales either require unfreezing or have been processed.
            '''
            keyboard = [[InlineKeyboardButton('🔙 Back', callback_data='sale_logs_panel')]]
        else:
            text = f'''
✅ **APPROVABLE SALES** ({len(pending_logs)})

These sales can be approved (accounts are NOT frozen):

'''
            keyboard = []
            for i, log in enumerate(pending_logs[:15], 1):
                text += f'''
{i}. 🟢 **{log.account_phone}**
   Seller: @{log.seller_username} - \
   ID: {log.id}

'''
                keyboard.append([
                    InlineKeyboardButton(f'✅ Approve #{log.id}', callback_data=f'approve_sale_{log.id}'),
                    InlineKeyboardButton(f'❌ Reject #{log.id}', callback_data=f'reject_sale_{log.id}')
                ])
            
            keyboard.append([InlineKeyboardButton('🔙 Back', callback_data='sale_logs_panel')])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)
        
    finally:
        close_db_session(db)

async def handle_approve_sale_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    '''Approve a specific sale after freeze check.'''
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    if not is_admin(user.id):
        await query.answer('❌ Access denied.', show_alert=True)
        return
    
    # Extract sale_log_id from callback data
    sale_log_id = int(query.data.split('_')[-1])
    
    from database import get_db_session, close_db_session
    from database.sale_log_operations import sale_log_service
    from database.operations import UserService
    
    db = get_db_session()
    try:
        # Get admin user
        admin_user = UserService.get_user_by_telegram_id(db, user.id)
        if not admin_user:
            await query.answer('❌ Admin user not found.', show_alert=True)
            return
        
        # Attempt approval with freeze check
        result = sale_log_service.approve_sale_log(
            db=db,
            sale_log_id=sale_log_id,
            admin_id=admin_user.id,
            notes=f'Approved by {admin_user.first_name or admin_user.username}'
        )
        
        if result['success']:
            # Send notification to seller
            try:
                from utils.notification_service import get_notification_service
                notification_service = get_notification_service()
                if notification_service:
                    sale_log = db.query(AccountSale).filter(AccountSale.id == sale_log_id).first()
                    if sale_log:
                        # Get seller info
                        seller = db.query(User).filter(User.id == sale_log.seller_id).first()
                        seller_telegram_id = seller.telegram_user_id if seller else None
                        if seller_telegram_id:
                            await notification_service.notify_sale_approved(
                                user_telegram_id=seller_telegram_id,
                                phone_number="account",
                                sale_price=sale_log.sale_price,
                                admin_notes=result.get('notes')
                            )
            except Exception as e:
                logger.error(f"Error sending approval notification: {e}")
            
            await query.answer(f'✅ Sale approved!', show_alert=True)
            
            # Show success message
            success_text = f'''
✅ **SALE APPROVED**

**Account:** {result['account_phone']}
**Approved by:** {result['approved_by']}
**Status:** ADMIN_APPROVED

The seller will be notified of the approval.
            '''
            
            keyboard = [
                [InlineKeyboardButton('📋 Back to Sales', callback_data='sale_logs_panel')],
                [InlineKeyboardButton('✅ Approve Another', callback_data='approve_sale_list')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(success_text, parse_mode='Markdown', reply_markup=reply_markup)
        else:
            # Handle errors - especially frozen account
            if result.get('blocked'):
                error_text = f'''
❄️ **APPROVAL BLOCKED - ACCOUNT FROZEN**

**Account:** {result.get('account_phone', 'Unknown')}
**Reason:** {result.get('freeze_reason', 'No reason specified')}

⚠️ **This account is FROZEN and cannot be approved for sale.**

**Actions Required:**
1. Review freeze reason
2. Unfreeze account if appropriate
3. Then approve the sale

The sale will remain pending.
                '''
                await query.answer('❄️ Account frozen - cannot approve', show_alert=True)
            else:
                error_text = f'''
❌ **APPROVAL FAILED**

**Error:** {result.get('message', 'Unknown error')}

Please try again or contact system administrator.
                '''
                await query.answer('❌ Approval failed', show_alert=True)
            
            keyboard = [[InlineKeyboardButton('🔙 Back', callback_data='sale_logs_panel')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(error_text, parse_mode='Markdown', reply_markup=reply_markup)
    
    finally:
        close_db_session(db)

async def handle_reject_sale_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    '''Reject a specific sale.'''
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    if not is_admin(user.id):
        await query.answer('❌ Access denied.', show_alert=True)
        return
    
    # Extract sale_log_id
    sale_log_id = int(query.data.split('_')[-1])
    
    from database import get_db_session, close_db_session
    from database.sale_log_operations import sale_log_service
    from database.operations import UserService
    
    db = get_db_session()
    try:
        # Get sale log details before rejection
        sale_log = db.query(AccountSale).filter(AccountSale.id == sale_log_id).first()
        if not sale_log:
            await query.answer('❌ Sale not found.', show_alert=True)
            return
        
        # Get admin user
        admin_user = UserService.get_user_by_telegram_id(db, user.id)
        if not admin_user:
            await query.answer('❌ Admin user not found.', show_alert=True)
            return
        
        rejection_reason = f'Rejected by {admin_user.first_name or admin_user.username}'
        
        # Reject the sale
        success = sale_log_service.reject_sale_log(
            db=db,
            sale_log_id=sale_log_id,
            admin_id=admin_user.id,
            rejection_reason=rejection_reason
        )
        
        if success:
            # Send notification to seller
            try:
                from utils.notification_service import get_notification_service
                notification_service = get_notification_service()
                if notification_service:
                    # Get seller info
                    seller = db.query(User).filter(User.id == sale_log.seller_id).first()
                    seller_telegram_id = seller.telegram_user_id if seller else None
                    if seller_telegram_id:
                        await notification_service.notify_sale_rejected(
                            user_telegram_id=seller_telegram_id,
                            phone_number="account",
                            rejection_reason='Admin review - does not meet requirements',
                            admin_notes=rejection_reason
                        )
            except Exception as e:
                logger.error(f"Error sending rejection notification: {e}")
            
            await query.answer('✅ Sale rejected!', show_alert=True)
            
            text = f'''
❌ **SALE REJECTED**

**Account:** {sale_log.account_phone}
**Rejected by:** {admin_user.first_name or admin_user.username}

The seller has been notified of the rejection.
            '''
        else:
            await query.answer('❌ Rejection failed', show_alert=True)
            text = '''
❌ **REJECTION FAILED**

An error occurred while rejecting the sale.
Please try again.
            '''
        
        keyboard = [
            [InlineKeyboardButton('📋 Back to Sales', callback_data='sale_logs_panel')],
            [InlineKeyboardButton('❌ Reject Another', callback_data='approve_sale_list')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)
        
    finally:
        close_db_session(db)



async def handle_session_management(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Main session management panel - terminate sessions, view holds, etc."""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    if not is_admin(user.id):
        await query.answer("❌ Access denied.", show_alert=True)
        return
    
    # Import session manager
    from services.session_management import session_manager
    
    # Get session statistics
    stats = session_manager.get_session_monitoring_stats()
    
    session_text = f"""
🔐 **SESSION MANAGEMENT PANEL**

**📊 Current Statistics:**
• 📱 Accounts on Hold: {stats.get('held_accounts', 0)}
• ⚠️ Multi-Device Detected: {stats.get('multi_device_accounts', 0)}
• 📝 Recent Activities (7d): {stats.get('recent_activities', 0)}
• 🟢 Monitoring Status: {"Active" if stats.get('monitoring_active') else "Inactive"}

**🔧 Available Actions:**
• Terminate all sessions for a specific user
• View and release accounts on hold
• View session activity logs
• Configure session settings

**💡 About Session Management:**
This system automatically detects multi-device usage and places accounts on temporary hold. You can manually terminate sessions or release holds as needed.
    """
    
    keyboard = [
        [InlineKeyboardButton("🚫 Terminate User Sessions", callback_data="terminate_user_sessions")],
        [InlineKeyboardButton("❄️ View Accounts on Freeze", callback_data="view_session_holds")],
        [InlineKeyboardButton("🔓 Release All Holds", callback_data="release_all_holds")],
        [InlineKeyboardButton("📊 Session Activity Logs", callback_data="session_activity_logs")],
        [InlineKeyboardButton("🔙 Back to Admin Panel", callback_data="admin_panel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        session_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )


async def handle_terminate_user_sessions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show list of users with active sessions to manage."""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    if not is_admin(user.id):
        await query.answer("❌ Access denied.", show_alert=True)
        return
    
    db = get_db_session()
    try:
        from database.operations import SessionLogService
        
        # Get all users with active sessions
        multi_session_users = SessionLogService.get_multi_session_users(db)
        
        # Get all users with at least one active session
        all_session_users = db.query(User).join(
            SessionLog,
            SessionLog.user_id == User.id
        ).filter(SessionLog.status == 'ACTIVE').distinct().all()
        
        if not all_session_users:
            await query.edit_message_text(
                "⚠️ **No active sessions found.**\n\nThere are currently no users with active Telegram sessions.",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Back", callback_data="admin_sessions")
                ]])
            )
            return
        
        # Build multi-session lookup
        multi_session_map = {u['user_id']: u['session_count'] for u in multi_session_users}
        
        text = f"""
🚫 **TERMINATE USER SESSIONS**

**Total Users with Sessions:** {len(all_session_users)}
**Users with Multiple Sessions:** {len(multi_session_users)} ⚠️

Select a user to view and manage their sessions:
        """
        
        keyboard = []
        for u in all_session_users[:20]:  # Limit to 20 users for UI
            display_name = u.username or u.first_name or f"User {u.telegram_user_id}"
            session_count = db.query(SessionLog).filter(
                SessionLog.user_id == u.id,
                SessionLog.status == 'ACTIVE'
            ).count()
            
            # Highlight users with multiple sessions
            if u.id in multi_session_map:
                display = f"⚠️ {display_name} ({session_count} sessions)"
            else:
                display = f"👤 {display_name} ({session_count} session)"
            
            keyboard.append([
                InlineKeyboardButton(
                    display,
                    callback_data=f"view_user_sessions_{u.id}"
                )
            ])
        
        if len(all_session_users) > 20:
            keyboard.append([InlineKeyboardButton(
                f"... and {len(all_session_users) - 20} more users",
                callback_data="noop"
            )])
        
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="admin_sessions")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)
        
    finally:
        close_db_session(db)


async def handle_view_user_sessions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """View individual sessions for a specific user with termination options."""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    if not is_admin(user.id):
        await query.answer("❌ Access denied.", show_alert=True)
        return
    
    # Extract user_id from callback data
    user_id = int(query.data.split('_')[-1])
    
    db = get_db_session()
    try:
        from database.operations import SessionLogService
        
        # Get user details
        target_user = db.query(User).filter(User.id == user_id).first()
        if not target_user:
            await query.answer("❌ User not found.", show_alert=True)
            return
        
        # Get active sessions for this user
        sessions = SessionLogService.get_user_sessions(db, user_id, active_only=True, limit=10)
        
        if not sessions:
            await query.edit_message_text(
                f"⚠️ **No active sessions found for {target_user.username or target_user.first_name}**",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Back", callback_data="terminate_user_sessions")
                ]])
            )
            return
        
        # Check if user has multiple sessions
        has_multiple = len(sessions) > 1
        
        text = f"""
📱 **USER SESSIONS: {target_user.username or target_user.first_name}**

**Total Active Sessions:** {len(sessions)}
{"**⚠️ MULTIPLE SESSIONS DETECTED**" if has_multiple else ""}

**Sessions:**

"""
        
        for i, session in enumerate(sessions, 1):
            device_info = session.device_model or 'Unknown Device'
            platform = session.system_version or 'Unknown'
            ip = session.ip_address or 'Unknown IP'
            country = session.country or 'Unknown'
            is_current = " 🟢 CURRENT" if session.is_current else ""
            
            text += f"{i}. **{device_info}**{is_current}\n"
            text += f"   └ Platform: {platform}\n"
            text += f"   └ Location: {country} ({ip})\n"
            text += f"   └ Active: {session.last_active.strftime('%m/%d %H:%M')}\n\n"
        
        if has_multiple:
            text += "\n⚠️ **Action Required:** Multiple sessions detected. Terminate unauthorized sessions below."
        
        # Build termination buttons
        keyboard = []
        for session in sessions:
            device_name = (session.device_model or 'Unknown')[:25]
            current_marker = " 🟢" if session.is_current else ""
            keyboard.append([
                InlineKeyboardButton(
                    f"🚫 Terminate: {device_name}{current_marker}",
                    callback_data=f"terminate_session_{session.id}"
                )
            ])
        
        if has_multiple:
            keyboard.append([InlineKeyboardButton(
                "🚫 Terminate ALL Sessions",
                callback_data=f"terminate_all_user_sessions_{user_id}"
            )])
        
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="terminate_user_sessions")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)
        
    finally:
        close_db_session(db)


async def handle_terminate_specific_session(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Terminate a specific session by ID."""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    if not is_admin(user.id):
        await query.answer("❌ Access denied.", show_alert=True)
        return
    
    # Extract session_id from callback data
    session_id = int(query.data.split('_')[-1])
    
    db = get_db_session()
    try:
        from database.operations import SessionLogService
        
        # Get session details
        session = db.query(SessionLog).filter(SessionLog.id == session_id).first()
        if not session:
            await query.answer("❌ Session not found.", show_alert=True)
            return
        
        # Terminate the session in database
        success = SessionLogService.terminate_session(db, session_id)
        
        if success:
            # Log the action
            ActivityLogService.log_action(
                db, user.id, "SESSION_TERMINATED",
                f"Admin terminated session {session_id} (Device: {session.device_model})"
            )
            
            await query.answer("✅ Session terminated successfully!", show_alert=True)
            
            # Refresh the view
            await handle_view_user_sessions(update, context)
        else:
            await query.answer("❌ Failed to terminate session.", show_alert=True)
        
    finally:
        close_db_session(db)


async def handle_terminate_all_user_sessions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Terminate all sessions for a specific user."""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    if not is_admin(user.id):
        await query.answer("❌ Access denied.", show_alert=True)
        return
    
    # Extract user_id from callback data
    user_id = int(query.data.split('_')[-1])
    
    db = get_db_session()
    try:
        from database.operations import SessionLogService
        
        # Get user details
        target_user = db.query(User).filter(User.id == user_id).first()
        if not target_user:
            await query.answer("❌ User not found.", show_alert=True)
            return
        
        # Terminate all sessions for this user
        terminated_count = SessionLogService.terminate_user_sessions(db, user_id)
        
        if terminated_count > 0:
            # Log the action
            ActivityLogService.log_action(
                db, user.id, "ALL_SESSIONS_TERMINATED",
                f"Admin terminated all {terminated_count} sessions for user {target_user.username or target_user.first_name}"
            )
            
            await query.answer(f"✅ Terminated {terminated_count} sessions!", show_alert=True)
            
            # Go back to user list
            await handle_terminate_user_sessions(update, context)
        else:
            await query.answer("⚠️ No active sessions to terminate.", show_alert=True)
        
    finally:
        close_db_session(db)


async def handle_terminate_sessions_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """DEPRECATED - Redirects to new view_user_sessions handler."""
    query = update.callback_query
    await query.answer()
    
    # Extract user_id and redirect to new handler
    user_id = int(query.data.split('_')[-1])
    context.user_data['redirect_user_id'] = user_id
    
    # Modify callback data and call new handler
    query.data = f"view_user_sessions_{user_id}"
    await handle_view_user_sessions(update, context)


async def handle_view_session_holds(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """View accounts currently on hold due to multi-device detection."""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    if not is_admin(user.id):
        await query.answer("❌ Access denied.", show_alert=True)
        return
    
    db = get_db_session()
    try:
        from database.models import TelegramAccount, AccountStatus
        
        # Get accounts on hold
        held_accounts = db.query(TelegramAccount).filter(
            TelegramAccount.status == AccountStatus.TWENTY_FOUR_HOUR_HOLD
        ).all()
        
        if not held_accounts:
            text = """
✅ **NO ACCOUNTS ON HOLD**

There are currently no accounts on temporary hold.
All accounts are operating normally.
            """
            keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="admin_sessions")]]
        else:
            text = f"""
📋 **ACCOUNTS ON HOLD**

**Total Accounts:** {len(held_accounts)}

**Accounts List:**
"""
            for i, account in enumerate(held_accounts[:10], 1):  # Show first 10
                hold_time_left = "N/A"
                if account.hold_until:
                    time_left = account.hold_until - datetime.utcnow()
                    hours_left = int(time_left.total_seconds() / 3600)
                    hold_time_left = f"{hours_left}h" if hours_left > 0 else "Expired"
                
                text += f"\n{i}. **{account.phone_number}**"
                text += f"\n   └ Hold expires: {hold_time_left}"
                text += f"\n   └ Reason: {account.freeze_reason or 'Multi-device detected'}\n"
            
            if len(held_accounts) > 10:
                text += f"\n_...and {len(held_accounts) - 10} more accounts_"
            
            keyboard = [
                [InlineKeyboardButton("🔓 Release All Holds", callback_data="release_all_holds")],
                [InlineKeyboardButton("🔙 Back", callback_data="admin_sessions")]
            ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)
        
    finally:
        close_db_session(db)


async def handle_release_all_holds(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Release all accounts from hold."""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    if not is_admin(user.id):
        await query.answer("❌ Access denied.", show_alert=True)
        return
    
    # Show processing message
    await query.edit_message_text(
        "⏳ **Releasing all holds...**\n\nPlease wait...",
        parse_mode='Markdown'
    )
    
    from services.session_management import session_manager
    
    # Release holds
    result = await session_manager.check_and_release_holds()
    
    if result.get('success'):
        released = result.get('released_count', 0)
        errors = result.get('errors', [])
        
        text = f"""
✅ **HOLDS RELEASED**

**Released Accounts:** {released}
**Errors:** {len(errors)}

All eligible accounts have been released from hold.
        """
        
        if errors:
            text += f"\n\n**Errors:**\n"
            for error in errors[:5]:  # Show first 5 errors
                text += f"• {error}\n"
    else:
        text = f"""
❌ **RELEASE FAILED**

**Error:** {result.get('error', 'Unknown error')}

Please try again or check logs for details.
        """
    
    keyboard = [
        [InlineKeyboardButton("📋 View Holds", callback_data="view_session_holds")],
        [InlineKeyboardButton("🔙 Back", callback_data="admin_sessions")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)


async def handle_session_activity_logs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """View real-time session logs with device details and activity."""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    if not is_admin(user.id):
        await query.answer("❌ Access denied.", show_alert=True)
        return
    
    db = get_db_session()
    try:
        from database.operations import SessionLogService
        from database.models import ActivityLog
        
        # Get recent session logs (last 24 hours)
        recent_sessions = SessionLogService.get_recent_sessions(db, limit=20, hours=24)
        
        # Get session-related activity logs
        activities = db.query(ActivityLog).filter(
            ActivityLog.action_type.in_([
                'SESSION_MONITORED', 'ACCOUNT_HOLD', 'ACCOUNT_RELEASED', 
                'ALL_SESSIONS_TERMINATED', 'SESSION_TERMINATED'
            ])
        ).order_by(ActivityLog.created_at.desc()).limit(10).all()
        
        # Get statistics
        total_active = db.query(SessionLog).filter(SessionLog.status == 'ACTIVE').count()
        total_terminated = db.query(SessionLog).filter(SessionLog.status == 'TERMINATED').count()
        multi_session = len(SessionLogService.get_multi_session_users(db))
        
        text = f"""
📊 **SESSION ACTIVITY LOGS**

**Real-Time Statistics:**
• 🟢 Active Sessions: {total_active}
• 🔴 Terminated Sessions: {total_terminated}
• ⚠️ Multi-Session Users: {multi_session}

**Recent Session Events (Last 24h):**

"""
        
        if recent_sessions:
            for session in recent_sessions[:10]:
                device = session.device_model or 'Unknown Device'
                status_icon = "🟢" if session.status == 'ACTIVE' else "🔴"
                timestamp = session.session_start.strftime('%m/%d %H:%M')
                location = f"{session.country or 'Unknown'} ({session.ip_address or 'N/A'})"
                
                text += f"{status_icon} **{device}**\n"
                text += f"   └ Location: {location}\n"
                text += f"   └ Started: {timestamp}\n"
                text += f"   └ Status: {session.status}\n\n"
        else:
            text += "_No session events in the last 24 hours._\n\n"
        
        if activities:
            text += "\n**Admin Actions:**\n\n"
            for activity in activities[:5]:
                timestamp = activity.created_at.strftime('%m/%d %H:%M')
                action_emoji = {
                    'SESSION_MONITORED': '👀',
                    'ACCOUNT_HOLD': '⏸️',
                    'ACCOUNT_RELEASED': '▶️',
                    'ALL_SESSIONS_TERMINATED': '🚫',
                    'SESSION_TERMINATED': '❌'
                }.get(activity.action_type, '•')
                
                desc = activity.description[:60] if activity.description else 'No details'
                text += f"{action_emoji} {timestamp} - {desc}\n"
        
        keyboard = [
            [InlineKeyboardButton("🔄 Refresh", callback_data="session_activity_logs")],
            [InlineKeyboardButton("🔙 Back", callback_data="admin_sessions")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)
        
    finally:
        close_db_session(db)



# ==================== ACCOUNT MANIPULATION PANEL ====================

# Conversation states for account manipulation
ACCOUNT_SELECT, MANIPULATION_ACTION, NAME_INPUT, USERNAME_INPUT, PHOTO_SELECT, PASSWORD_INPUT = range(1000, 1006)


async def handle_account_manipulation_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show account manipulation main panel - select account to manipulate."""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    if not is_admin(user.id):
        await query.answer("❌ Access denied.", show_alert=True)
        return ConversationHandler.END
    
    db = get_db_session()
    try:
        from database.models import TelegramAccount, AccountStatus
        
        # Get all sold accounts (available accounts we can manipulate)
        accounts = db.query(TelegramAccount).filter(
            TelegramAccount.status.in_([AccountStatus.AVAILABLE, AccountStatus.SOLD])
        ).limit(50).all()
        
        if not accounts:
            await query.edit_message_text(
                "⚠️ **No accounts available for manipulation.**\n\nThere are no sold or available accounts to manage.",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Back to Admin Panel", callback_data="admin_panel")
                ]])
            )
            return ConversationHandler.END
        
        text = f"""
🛠️ **ACCOUNT MANIPULATION PANEL**

**Available Operations:**
• 🗑️ Delete all chat history
• 👤 Change account name
• 📝 Change username (@handle)
• 🖼️ Upload profile photo
• 🔒 Setup/modify 2FA

**Accounts Available:** {len(accounts)}

Select an account to manipulate:
        """
        
        keyboard = []
        for account in accounts[:20]:  # Show first 20
            display = f"{account.phone_number}"
            if account.status == AccountStatus.SOLD:
                display += " [SOLD]"
            
            keyboard.append([
                InlineKeyboardButton(
                    f"📱 {display}",
                    callback_data=f"manipulate_account_{account.id}"
                )
            ])
        
        if len(accounts) > 20:
            keyboard.append([InlineKeyboardButton(
                f"... and {len(accounts) - 20} more (scroll down)",
                callback_data="noop"
            )])
        
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="admin_panel")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)
        
        # Store in context for conversation flow
        context.user_data['manipulation_mode'] = True
        
        return ACCOUNT_SELECT
        
    finally:
        close_db_session(db)


async def handle_manipulation_account_select(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle account selection for manipulation."""
    query = update.callback_query
    await query.answer()
    
    # Extract account_id
    account_id = int(query.data.split('_')[-1])
    
    db = get_db_session()
    try:
        from database.models import TelegramAccount
        
        account = db.query(TelegramAccount).filter(TelegramAccount.id == account_id).first()
        
        if not account:
            await query.answer("❌ Account not found.", show_alert=True)
            return ConversationHandler.END
        
        # Store account info in context
        context.user_data['manipulation_account_id'] = account_id
        context.user_data['manipulation_phone'] = account.phone_number
        
        # Get account info using service
        from services.real_telegram import real_telegram_service
        
        text = f"""
🛠️ **ACCOUNT MANIPULATION**

**Selected Account:** {account.phone_number}
**Status:** {account.status.value}

**Available Operations:**

🗑️ **Delete Chat History** - Remove all conversations
👤 **Change Name** - Update display name (First & Last)
📝 **Change Username** - Update @handle
🖼️ **Profile Photo** - Upload or remove photo
🔒 **2FA Management** - Setup or modify two-factor authentication

Select an operation:
        """
        
        keyboard = [
            [InlineKeyboardButton("🗑️ Delete All Chat History", callback_data="manip_delete_history")],
            [InlineKeyboardButton("👤 Change Account Name", callback_data="manip_change_name")],
            [InlineKeyboardButton("📝 Change Username", callback_data="manip_change_username")],
            [InlineKeyboardButton("🖼️ Manage Profile Photo", callback_data="manip_profile_photo")],
            [InlineKeyboardButton("🔒 2FA Management", callback_data="manip_2fa")],
            [InlineKeyboardButton("ℹ️ View Account Info", callback_data="manip_view_info")],
            [InlineKeyboardButton("🔙 Back to Account List", callback_data="account_manipulation")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)
        
        return MANIPULATION_ACTION
        
    finally:
        close_db_session(db)


async def handle_delete_history_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Execute chat history deletion."""
    query = update.callback_query
    await query.answer()
    
    account_id = context.user_data.get('manipulation_account_id')
    phone = context.user_data.get('manipulation_phone')
    
    if not account_id:
        await query.answer("❌ Session expired.", show_alert=True)
        return ConversationHandler.END
    
    # Show processing message
    await query.edit_message_text(
        f"⏳ **Deleting chat history for {phone}...**\n\nThis may take a few minutes.\nPlease wait...",
        parse_mode='Markdown'
    )
    
    db = get_db_session()
    try:
        from services.real_telegram import real_telegram_service
        from services.account_manipulation import account_manipulation_service
        
        # Create Telethon client for the account
        client = await real_telegram_service.create_client(phone, use_proxy=False)
        
        if not client:
            await query.edit_message_text(
                f"❌ **Failed to connect**\n\nCould not create session for {phone}.",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Back", callback_data=f"manipulate_account_{account_id}")
                ]])
            )
            return MANIPULATION_ACTION
        
        # Delete chat history
        result = await account_manipulation_service.delete_all_chat_history(client)
        
        # Disconnect client
        await client.disconnect()
        
        # Show results
        if result.get('success'):
            deleted = result.get('deleted_count', 0)
            failed = result.get('failed_count', 0)
            total = result.get('total_dialogs', 0)
            
            text = f"""
✅ **CHAT HISTORY DELETED**

**Account:** {phone}
**Total Chats:** {total}
**Deleted:** {deleted}
**Failed:** {failed}

All accessible chat history has been removed from the account.
            """
        else:
            text = f"""
❌ **DELETION FAILED**

**Account:** {phone}
**Error:** {result.get('error', 'Unknown error')}

Please check logs for details.
            """
        
        keyboard = [
            [InlineKeyboardButton("🛠️ More Operations", callback_data=f"manipulate_account_{account_id}")],
            [InlineKeyboardButton("🔙 Back to Account List", callback_data="account_manipulation")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)
        
        return MANIPULATION_ACTION
        
    finally:
        close_db_session(db)


async def handle_change_name_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start name change conversation."""
    query = update.callback_query
    await query.answer()
    
    phone = context.user_data.get('manipulation_phone')
    
    text = f"""
👤 **CHANGE ACCOUNT NAME**

**Account:** {phone}

Please send the new name in this format:
`FirstName LastName`

Or just send first name:
`FirstName`

Examples:
• John Smith
• Sarah
• Michael Johnson

Send /cancel to abort.
    """
    
    await query.edit_message_text(text, parse_mode='Markdown')
    
    return NAME_INPUT


async def handle_name_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process name input and change account name."""
    message = update.message
    name_parts = message.text.strip().split(maxsplit=1)
    
    first_name = name_parts[0] if name_parts else ""
    last_name = name_parts[1] if len(name_parts) > 1 else None
    
    if not first_name:
        await message.reply_text(
            "❌ Invalid name format. Please send a valid name.\n\nSend /cancel to abort."
        )
        return NAME_INPUT
    
    account_id = context.user_data.get('manipulation_account_id')
    phone = context.user_data.get('manipulation_phone')
    
    # Show processing
    processing_msg = await message.reply_text(
        f"⏳ **Changing name for {phone}...**",
        parse_mode='Markdown'
    )
    
    db = get_db_session()
    try:
        from services.real_telegram import real_telegram_service
        from services.account_manipulation import account_manipulation_service
        
        # Create client
        client = await real_telegram_service.create_client(phone, use_proxy=False)
        
        if not client:
            await processing_msg.edit_text(
                f"❌ **Failed to connect to {phone}**",
                parse_mode='Markdown'
            )
            return ConversationHandler.END
        
        # Change name
        result = await account_manipulation_service.change_account_name(
            client, first_name, last_name
        )
        
        await client.disconnect()
        
        # Show result
        if result.get('success'):
            text = f"""
✅ **NAME CHANGED**

**Account:** {phone}
**New Name:** {first_name} {last_name or ''}

Account name has been updated successfully!
            """
        else:
            text = f"""
❌ **NAME CHANGE FAILED**

**Account:** {phone}
**Error:** {result.get('error', 'Unknown error')}
            """
        
        keyboard = [
            [InlineKeyboardButton("🛠️ More Operations", callback_data=f"manipulate_account_{account_id}")],
            [InlineKeyboardButton("🔙 Back to Account List", callback_data="account_manipulation")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await processing_msg.edit_text(text, parse_mode='Markdown', reply_markup=reply_markup)
        
        context.user_data.clear()
        return ConversationHandler.END
        
    finally:
        close_db_session(db)


async def handle_change_username_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start username change conversation."""
    query = update.callback_query
    await query.answer()
    
    phone = context.user_data.get('manipulation_phone')
    
    text = f"""
📝 **CHANGE USERNAME**

**Account:** {phone}

Please send the new username (without @):
Examples:
• `john_smith`
• `sarah2024`
• `cooluser`

**Requirements:**
• At least 5 characters
• Only letters, numbers, and underscores
• Cannot remove username (send "remove" to delete)

Send /cancel to abort.
    """
    
    await query.edit_message_text(text, parse_mode='Markdown')
    
    return USERNAME_INPUT


async def handle_username_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process username input and change account username."""
    message = update.message
    new_username = message.text.strip().lstrip('@')
    
    account_id = context.user_data.get('manipulation_account_id')
    phone = context.user_data.get('manipulation_phone')
    
    # Show processing
    processing_msg = await message.reply_text(
        f"⏳ **Changing username for {phone}...**",
        parse_mode='Markdown'
    )
    
    db = get_db_session()
    try:
        from services.real_telegram import real_telegram_service
        from services.account_manipulation import account_manipulation_service
        
        # Create client
        client = await real_telegram_service.create_client(phone, use_proxy=False)
        
        if not client:
            await processing_msg.edit_text(
                f"❌ **Failed to connect to {phone}**",
                parse_mode='Markdown'
            )
            return ConversationHandler.END
        
        # Change or remove username
        if new_username.lower() == 'remove':
            result = await account_manipulation_service.remove_username(client)
            action = "removed"
        else:
            result = await account_manipulation_service.change_username(client, new_username)
            action = f"changed to @{new_username}"
        
        await client.disconnect()
        
        # Show result
        if result.get('success'):
            text = f"""
✅ **USERNAME {action.upper()}**

**Account:** {phone}

Username has been updated successfully!
            """
        else:
            text = f"""
❌ **USERNAME CHANGE FAILED**

**Account:** {phone}
**Error:** {result.get('error', 'Unknown error')}
            """
        
        keyboard = [
            [InlineKeyboardButton("🛠️ More Operations", callback_data=f"manipulate_account_{account_id}")],
            [InlineKeyboardButton("🔙 Back to Account List", callback_data="account_manipulation")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await processing_msg.edit_text(text, parse_mode='Markdown', reply_markup=reply_markup)
        
        context.user_data.clear()
        return ConversationHandler.END
        
    finally:
        close_db_session(db)


async def handle_profile_photo_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show profile photo management menu."""
    query = update.callback_query
    await query.answer()
    
    account_id = context.user_data.get('manipulation_account_id')
    phone = context.user_data.get('manipulation_phone')
    
    from services.account_manipulation import account_manipulation_service
    
    # Get available photos
    available_photos = account_manipulation_service.get_available_profile_photos()
    
    # Build photo list
    photo_list = ""
    if available_photos:
        photo_list = "**📁 Available Photos:**\n" + "\n".join([f"• {p}" for p in available_photos[:10]])
        if len(available_photos) > 10:
            photo_list += f"\n_...and {len(available_photos) - 10} more_"
    else:
        photo_list = "⚠️ No photos found in profile_photos/ directory"
    
    text = f"""
🖼️ **PROFILE PHOTO MANAGEMENT**

**Account:** {phone}
**Available Photos:** {len(available_photos)}

**Actions:**
• Upload a new profile photo
• Delete all current profile photos

{photo_list}

Select an action:
    """
    
    keyboard = []
    
    # Add photo selection buttons
    if available_photos:
        for photo in available_photos[:15]:  # Show first 15
            keyboard.append([
                InlineKeyboardButton(
                    f"📷 {photo}",
                    callback_data=f"upload_photo_{photo}"
                )
            ])
    
    keyboard.extend([
        [InlineKeyboardButton("🗑️ Delete All Profile Photos", callback_data="delete_all_photos")],
        [InlineKeyboardButton("🔙 Back", callback_data=f"manipulate_account_{account_id}")]
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)
    
    return PHOTO_SELECT


async def handle_upload_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Upload selected photo to account."""
    query = update.callback_query
    await query.answer()
    
    # Extract photo filename
    photo_filename = query.data.replace('upload_photo_', '')
    
    account_id = context.user_data.get('manipulation_account_id')
    phone = context.user_data.get('manipulation_phone')
    
    # Show processing
    await query.edit_message_text(
        f"⏳ **Uploading photo {photo_filename} to {phone}...**",
        parse_mode='Markdown'
    )
    
    db = get_db_session()
    try:
        from services.real_telegram import real_telegram_service
        from services.account_manipulation import account_manipulation_service
        
        # Create client
        client = await real_telegram_service.create_client(phone, use_proxy=False)
        
        if not client:
            await query.edit_message_text(
                f"❌ **Failed to connect to {phone}**",
                parse_mode='Markdown'
            )
            return ConversationHandler.END
        
        # Upload photo
        result = await account_manipulation_service.upload_profile_photo(client, photo_filename)
        
        await client.disconnect()
        
        # Show result
        if result.get('success'):
            text = f"""
✅ **PROFILE PHOTO UPLOADED**

**Account:** {phone}
**Photo:** {photo_filename}

Profile photo has been updated successfully!
            """
        else:
            text = f"""
❌ **PHOTO UPLOAD FAILED**

**Account:** {phone}
**Error:** {result.get('error', 'Unknown error')}
            """
        
        keyboard = [
            [InlineKeyboardButton("🖼️ Upload Another", callback_data="manip_profile_photo")],
            [InlineKeyboardButton("🛠️ More Operations", callback_data=f"manipulate_account_{account_id}")],
            [InlineKeyboardButton("🔙 Back to Account List", callback_data="account_manipulation")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)
        
        return MANIPULATION_ACTION
        
    finally:
        close_db_session(db)


async def handle_delete_all_photos(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Delete all profile photos from account."""
    query = update.callback_query
    await query.answer()
    
    account_id = context.user_data.get('manipulation_account_id')
    phone = context.user_data.get('manipulation_phone')
    
    # Show processing
    await query.edit_message_text(
        f"⏳ **Deleting all profile photos from {phone}...**",
        parse_mode='Markdown'
    )
    
    db = get_db_session()
    try:
        from services.real_telegram import real_telegram_service
        from services.account_manipulation import account_manipulation_service
        
        # Create client
        client = await real_telegram_service.create_client(phone, use_proxy=False)
        
        if not client:
            await query.edit_message_text(
                f"❌ **Failed to connect to {phone}**",
                parse_mode='Markdown'
            )
            return ConversationHandler.END
        
        # Delete photos
        result = await account_manipulation_service.delete_profile_photos(client)
        
        await client.disconnect()
        
        # Show result
        if result.get('success'):
            deleted_count = result.get('deleted_count', 0)
            text = f"""
✅ **PROFILE PHOTOS DELETED**

**Account:** {phone}
**Deleted:** {deleted_count} photos

All profile photos have been removed.
            """
        else:
            text = f"""
❌ **DELETION FAILED**

**Account:** {phone}
**Error:** {result.get('error', 'Unknown error')}
            """
        
        keyboard = [
            [InlineKeyboardButton("🖼️ Manage Photos", callback_data="manip_profile_photo")],
            [InlineKeyboardButton("🛠️ More Operations", callback_data=f"manipulate_account_{account_id}")],
            [InlineKeyboardButton("🔙 Back to Account List", callback_data="account_manipulation")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)
        
        return MANIPULATION_ACTION
        
    finally:
        close_db_session(db)


async def handle_2fa_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show 2FA management menu."""
    query = update.callback_query
    await query.answer()
    
    account_id = context.user_data.get('manipulation_account_id')
    phone = context.user_data.get('manipulation_phone')
    
    text = f"""
🔒 **2FA MANAGEMENT**

**Account:** {phone}

**Two-Factor Authentication** adds an extra layer of security to the account.

**Available Actions:**
• Setup new 2FA password
• Disable current 2FA
• Check 2FA status

⚠️ **Warning:** Changing 2FA settings will affect account security.

Select an action:
    """
    
    keyboard = [
        [InlineKeyboardButton("🔐 Setup/Change 2FA", callback_data="2fa_setup")],
        [InlineKeyboardButton("🔓 Disable 2FA", callback_data="2fa_disable")],
        [InlineKeyboardButton("ℹ️ Check Status", callback_data="2fa_status")],
        [InlineKeyboardButton("🔙 Back", callback_data=f"manipulate_account_{account_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)
    
    return MANIPULATION_ACTION


async def handle_view_account_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """View detailed account information."""
    query = update.callback_query
    await query.answer()
    
    account_id = context.user_data.get('manipulation_account_id')
    phone = context.user_data.get('manipulation_phone')
    
    # Show loading
    await query.edit_message_text(
        f"⏳ **Fetching account info for {phone}...**",
        parse_mode='Markdown'
    )
    
    db = get_db_session()
    try:
        from services.real_telegram import real_telegram_service
        from services.account_manipulation import account_manipulation_service
        
        # Create client
        client = await real_telegram_service.create_client(phone, use_proxy=False)
        
        if not client:
            await query.edit_message_text(
                f"❌ **Failed to connect to {phone}**",
                parse_mode='Markdown'
            )
            return MANIPULATION_ACTION
        
        # Get account info
        result = await account_manipulation_service.get_account_info(client)
        
        await client.disconnect()
        
        if result.get('success'):
            info = result
            text = f"""
ℹ️ **ACCOUNT INFORMATION**

**📱 Phone:** {info.get('phone', 'N/A')}
**🆔 ID:** {info.get('id', 'N/A')}
**👤 Name:** {info.get('first_name', '')} {info.get('last_name', '')}
**📝 Username:** @{info.get('username', 'none')}
**✅ Verified:** {"Yes" if info.get('is_verified') else "No"}
**🤖 Bot:** {"Yes" if info.get('is_bot') else "No"}
**⚠️ Restricted:** {"Yes" if info.get('is_restricted') else "No"}

This is the current state of the account on Telegram.
            """
        else:
            text = f"""
❌ **FAILED TO GET INFO**

**Account:** {phone}
**Error:** {result.get('error', 'Unknown error')}
            """
        
        keyboard = [
            [InlineKeyboardButton("🔙 Back to Operations", callback_data=f"manipulate_account_{account_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)
        
        return MANIPULATION_ACTION
        
    finally:
        close_db_session(db)


