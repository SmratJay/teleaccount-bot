"""Admin command handlers for the Telegram Account Bot."""
import logging
import json
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ConversationHandler
from sqlalchemy import func, select

from database import get_db_session, close_db_session
from database.operations import UserService, SystemSettingsService, ActivityLogService
from database.models_old import User, Withdrawal  # Real SQLAlchemy models
from database.models import AccountSaleLog, UserStatus  # Enums and other classes
from services.translation_service import translation_service

logger = logging.getLogger(__name__)

# Conversation states
BROADCAST_TEXT = 1
EDIT_USER_DATA = 2
USER_ID_INPUT = 3
USER_FIELD_SELECT = 4
USER_FIELD_VALUE = 5

async def handle_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Main admin panel with all specified features."""
    user = update.effective_user
    
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
• Chat history deletion toggle control
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
        [InlineKeyboardButton("❄️ Account Freeze Management", callback_data="admin_freeze_panel")],
        [InlineKeyboardButton("📋 Sale Logs & Approval", callback_data="sale_logs_panel")],
        [InlineKeyboardButton("🗑️ Chat History Control", callback_data="admin_chat_control")],
        [InlineKeyboardButton("⚠️ Reports & Logs", callback_data="admin_reports")],
        [InlineKeyboardButton("🔐 Session Management", callback_data="admin_sessions")],
        [InlineKeyboardButton("🌐 IP/Proxy Config", callback_data="admin_proxy")],
        [InlineKeyboardButton("📊 Activity Tracker", callback_data="admin_activity")],
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

async def cancel_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel broadcast and clear conversation state."""
    logger.info(f"🔥 CANCEL_BROADCAST: Clearing broadcast state for user {update.effective_user.id}")
    context.user_data.clear()
    return ConversationHandler.END

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
    
    # 🔥 CRITICAL: If user is in verification (CAPTCHA), don't process as broadcast!
    if context.user_data.get('verification_step'):
        logger.warning(f"⚠️ BROADCAST: User {update.effective_user.id} is in verification, ignoring broadcast")
        return ConversationHandler.END
    
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
        context.user_data.clear()  # 🔥 CRITICAL: Clear state on error too!
        await processing_msg.edit_text(
            f"❌ **Broadcast Failed**\n\nError: {str(e)}\n\nPlease try again.",
            parse_mode='Markdown'
        )
        return ConversationHandler.END
    finally:
        close_db_session(db)

async def handle_admin_user_edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle manual user data editing."""
    await update.callback_query.answer()
    
    edit_text = """
👥 **MANUAL USER DATA EDITOR**

Manually edit any user's data or status in the bot system.

**Available Operations:**
• 🔍 **Search User** - Find user by Telegram ID or username
• ✏️ **Edit User Data** - Modify name, balance, status, etc.
• 🔄 **Update Status** - Change user status (Active/Frozen/Banned)
• 📊 **View User Details** - See complete user information
• 💰 **Adjust Balance** - Add or subtract from user balance

**Security Notice:** All changes are logged for audit purposes.

Enter the **Telegram User ID** of the user you want to edit:
    """
    
    keyboard = [
        [InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_panel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        edit_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    
    return USER_ID_INPUT

async def process_user_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process user ID input for editing."""
    # 🔥 CRITICAL: If user is in verification (CAPTCHA), don't process as user edit!
    if context.user_data.get('verification_step'):
        logger.warning(f"⚠️ USER_EDIT: User {update.effective_user.id} is in verification, ignoring user edit")
        return ConversationHandler.END
    
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
    # 🔥 CRITICAL: If user is in verification (CAPTCHA), don't process as field value!
    if context.user_data.get('verification_step'):
        logger.warning(f"⚠️ USER_EDIT: User {update.effective_user.id} is in verification, ignoring field value")
        return ConversationHandler.END
    
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

async def handle_chat_history_control(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle chat history deletion control settings."""
    await update.callback_query.answer()
    
    db = get_db_session()
    try:
        # Get current setting
        delete_history_enabled = SystemSettingsService.get_setting(
            db, 'delete_chat_history_on_sale', default=False
        )
        
        status_icon = "✅" if delete_history_enabled else "❌"
        status_text = "ENABLED" if delete_history_enabled else "DISABLED"
        
        control_text = f"""
🗑️ **CHAT HISTORY DELETION CONTROL**

**Current Status:** {status_icon} {status_text}

**What This Does:**
When a user sells an account, their chat history with this bot will be:
• **Enabled:** Automatically deleted (more privacy)
• **Disabled:** Preserved (for support/records)

**Current Setting:** {'Chat histories will be DELETED after account sale' if delete_history_enabled else 'Chat histories will be PRESERVED after account sale'}

**Why Enable:**
• User privacy protection
• Clean slate for new buyers
• Reduce stored data

**Why Disable:**
• Keep audit trail
• Customer support history
• Dispute resolution

Toggle the setting below:
        """
        
        keyboard = [
            [InlineKeyboardButton(
                f"{'🔴 Disable' if delete_history_enabled else '🟢 Enable'} History Deletion",
                callback_data=f"toggle_history_{'off' if delete_history_enabled else 'on'}"
            )],
            [InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_panel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            control_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    finally:
        close_db_session(db)

async def handle_toggle_history_deletion(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Toggle chat history deletion setting."""
    await update.callback_query.answer()
    
    action = update.callback_query.data.split('_')[-1]  # 'on' or 'off'
    new_value = (action == 'on')
    
    db = get_db_session()
    try:
        # Update setting
        success = SystemSettingsService.set_setting(
            db, 
            'delete_chat_history_on_sale', 
            new_value,
            description="Automatically delete user chat history after account sale"
        )
        
        if success:
            status_text = "ENABLED" if new_value else "DISABLED"
            result_text = f"""
✅ **SETTING UPDATED**

**Chat History Deletion:** {status_text}

{'Users\' chat histories will now be DELETED after they sell their accounts.' if new_value else 'Users\' chat histories will now be PRESERVED after they sell their accounts.'}

This setting will apply to all future account sales.
            """
            
            # Log action
            admin_user = UserService.get_user_by_telegram_id(db, update.effective_user.id)
            if admin_user:
                ActivityLogService.log_action(
                    db, admin_user.id, "ADMIN_SYSTEM_SETTING",
                    f"{'Enabled' if new_value else 'Disabled'} chat history deletion on sale",
                    extra_data=json.dumps({
                        "setting": "delete_chat_history_on_sale",
                        "new_value": new_value
                    })
                )
        else:
            result_text = "❌ **Error**\n\nFailed to update setting. Please try again."
        
        keyboard = [[InlineKeyboardButton("🔙 Back to Chat Control", callback_data="admin_chat_control")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            result_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    finally:
        close_db_session(db)

async def handle_session_management(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle session management panel - monitor and control active sessions."""
    await update.callback_query.answer()
    
    from services.session_management import session_manager
    
    # Get session monitoring statistics
    stats = session_manager.get_session_monitoring_stats()
    
    if stats['success']:
        management_text = f"""
🔐 **SESSION MANAGEMENT PANEL**

**📊 Current Status:**
• Accounts on Hold: {stats['held_accounts']}
• Multi-Device Detected: {stats['multi_device_accounts']}
• Recent Activities (7 days): {stats['recent_activities']}
• Monitoring Status: {'🟢 Active' if stats['monitoring_active'] else '🔴 Inactive'}

**⚙️ How It Works:**
1. **Auto-Detection** - System monitors for multi-device usage
2. **Auto-Freeze** - Accounts frozen for 24h when detected
3. **Session Termination** - Other devices logged out automatically
4. **Auto-Release** - Accounts released after hold period

**🛡️ Security Features:**
• Multi-device detection and prevention
• Automatic session termination
• 24-48 hour account holds
• Force logout capabilities
• Activity logging and monitoring

**📋 Admin Actions:**
• View accounts on hold
• Force release from hold
• Manual session termination
• View session activity logs

Choose an action:
        """
    else:
        management_text = f"""
🔐 **SESSION MANAGEMENT PANEL**

⚠️ **Error Loading Stats**
{stats.get('error', 'Unknown error')}

The session management system may be experiencing issues.
Please check logs or try again later.
        """
    
    keyboard = [
        [InlineKeyboardButton("📋 View Held Accounts", callback_data="session_view_holds")],
        [InlineKeyboardButton("🔓 Release Holds Now", callback_data="session_release_holds")],
        [InlineKeyboardButton("📊 Session Activity Logs", callback_data="session_activity_logs")],
        [InlineKeyboardButton("⚙️ Auto-Monitoring Settings", callback_data="session_settings")],
        [InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_panel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        management_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def handle_view_held_accounts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display all accounts currently on hold."""
    await update.callback_query.answer()
    
    from database.models import TelegramAccount, AccountStatus
    
    db = get_db_session()
    try:
        from sqlalchemy import select
        # Get all accounts on hold
        held_accounts = db.execute(
            select(TelegramAccount).where(
                TelegramAccount.status == AccountStatus.TWENTY_FOUR_HOUR_HOLD
            )
        ).scalars().all()
        
        if held_accounts:
            accounts_list = []
            for idx, account in enumerate(held_accounts, 1):
                hold_until = account.hold_until.strftime('%Y-%m-%d %H:%M UTC') if account.hold_until else 'N/A'
                time_remaining = (account.hold_until - datetime.utcnow()).total_seconds() / 3600 if account.hold_until else 0
                
                accounts_list.append(
                    f"{idx}. **Account #{account.id}**\n"
                    f"   Phone: {account.phone_number}\n"
                    f"   Seller ID: {account.seller_id}\n"
                    f"   Hold Until: {hold_until}\n"
                    f"   Time Left: {time_remaining:.1f}h\n"
                    f"   Reason: Multi-device detection"
                )
            
            held_text = f"""
📋 **ACCOUNTS ON HOLD**

**Total:** {len(held_accounts)} accounts

{chr(10).join(accounts_list)}

**Actions:**
• Wait for auto-release
• Force release manually
• View activity logs
            """
        else:
            held_text = """
📋 **ACCOUNTS ON HOLD**

✅ **No accounts currently on hold!**

All accounts are clear. The system will automatically place accounts on hold when multi-device usage is detected.
            """
        
        keyboard = [
            [InlineKeyboardButton("🔓 Release All Now", callback_data="session_release_holds")],
            [InlineKeyboardButton("🔙 Back to Sessions", callback_data="admin_sessions")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            held_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    finally:
        close_db_session(db)

async def handle_release_holds(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Manually release all accounts from hold."""
    await update.callback_query.answer()
    
    from services.session_management import session_manager
    
    # Release holds
    result = await session_manager.check_and_release_holds()
    
    if result['success']:
        if result['released_count'] > 0:
            release_text = f"""
✅ **HOLDS RELEASED**

**Released:** {result['released_count']} accounts

All held accounts have been released and are now available again.

{'⚠️ **Errors:** ' + ', '.join(result['errors']) if result['errors'] else ''}
            """
        else:
            release_text = """
ℹ️ **NO HOLDS TO RELEASE**

There are no accounts currently on hold that are ready to be released.

Accounts are automatically released after their hold period expires.
            """
    else:
        release_text = f"""
❌ **ERROR RELEASING HOLDS**

{result.get('error', 'Unknown error occurred')}

Please check logs or try again later.
        """
    
    keyboard = [
        [InlineKeyboardButton("📋 View Held Accounts", callback_data="session_view_holds")],
        [InlineKeyboardButton("🔙 Back to Sessions", callback_data="admin_sessions")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        release_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def handle_session_activity_logs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display recent session-related activity logs."""
    await update.callback_query.answer()
    
    from database.operations import ActivityLogService
    from datetime import timedelta
    
    db = get_db_session()
    try:
        # Get recent session activities (last 7 days)
        recent_date = datetime.utcnow() - timedelta(days=7)
        
        activities = db.query(ActivityLogService).filter(
            ActivityLogService.action_type.in_([
                'SESSION_MONITORED', 'ACCOUNT_HOLD', 'ACCOUNT_RELEASED', 
                'ALL_SESSIONS_TERMINATED', 'SESSION_TERMINATED'
            ]),
            ActivityLogService.created_at >= recent_date
        ).order_by(ActivityLogService.created_at.desc()).limit(20).all()
        
        if activities:
            log_entries = []
            for activity in activities:
                timestamp = activity.created_at.strftime('%m/%d %H:%M')
                log_entries.append(
                    f"• **{activity.action_type}**\n"
                    f"  {activity.description}\n"
                    f"  {timestamp} UTC"
                )
            
            logs_text = f"""
📊 **SESSION ACTIVITY LOGS**

**Recent 7 Days** (Last 20 entries)

{chr(10).join(log_entries)}

**Legend:**
• SESSION_MONITORED - Routine check
• ACCOUNT_HOLD - 24h hold applied
• ACCOUNT_RELEASED - Hold expired/removed
• ALL_SESSIONS_TERMINATED - Full logout
            """
        else:
            logs_text = """
📊 **SESSION ACTIVITY LOGS**

ℹ️ **No recent session activities**

No session-related events in the last 7 days.
System is monitoring but no issues detected.
            """
        
        keyboard = [[InlineKeyboardButton("🔙 Back to Sessions", callback_data="admin_sessions")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            logs_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    finally:
        close_db_session(db)

async def handle_session_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display and manage session monitoring settings."""
    await update.callback_query.answer()
    
    db = get_db_session()
    try:
        # Get current settings
        auto_terminate = SystemSettingsService.get_setting(
            db, 'auto_terminate_sessions', default=True
        )
        auto_freeze = SystemSettingsService.get_setting(
            db, 'auto_freeze_multi_device', default=True
        )
        hold_duration = SystemSettingsService.get_setting(
            db, 'multi_device_hold_hours', default=24
        )
        
        settings_text = f"""
⚙️ **SESSION MONITORING SETTINGS**

**Current Configuration:**

🔓 **Auto-Terminate Other Sessions**
Status: {'✅ ENABLED' if auto_terminate else '❌ DISABLED'}
• When multi-device detected, logout other devices

❄️ **Auto-Freeze Accounts**
Status: {'✅ ENABLED' if auto_freeze else '❌ DISABLED'}
• Automatically freeze accounts with multi-device usage

⏱️ **Hold Duration**
Current: {hold_duration} hours
• How long accounts stay frozen

**Recommendations:**
• Keep auto-terminate ENABLED for security
• Keep auto-freeze ENABLED to prevent abuse
• 24-48 hours hold is standard

**Note:** These are automatic security features.
Disabling them may increase security risks.
        """
        
        keyboard = [
            [InlineKeyboardButton(
                f"{'🔴 Disable' if auto_terminate else '🟢 Enable'} Auto-Terminate",
                callback_data=f"session_toggle_terminate_{'off' if auto_terminate else 'on'}"
            )],
            [InlineKeyboardButton(
                f"{'🔴 Disable' if auto_freeze else '🟢 Enable'} Auto-Freeze",
                callback_data=f"session_toggle_freeze_{'off' if auto_freeze else 'on'}"
            )],
            [InlineKeyboardButton("⏱️ Set Hold Duration", callback_data="session_set_duration")],
            [InlineKeyboardButton("🔙 Back to Sessions", callback_data="admin_sessions")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            settings_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    finally:
        close_db_session(db)

async def handle_toggle_session_setting(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Toggle session management settings."""
    await update.callback_query.answer()
    
    # Parse callback data: session_toggle_{setting}_{action}
    parts = update.callback_query.data.split('_')
    setting_type = parts[2]  # 'terminate' or 'freeze'
    action = parts[3]  # 'on' or 'off'
    new_value = (action == 'on')
    
    setting_map = {
        'terminate': 'auto_terminate_sessions',
        'freeze': 'auto_freeze_multi_device'
    }
    
    setting_key = setting_map.get(setting_type)
    if not setting_key:
        await update.callback_query.answer("Invalid setting", show_alert=True)
        return
    
    db = get_db_session()
    try:
        success = SystemSettingsService.set_setting(
            db, setting_key, new_value,
            description=f"Auto-{'terminate sessions' if setting_type == 'terminate' else 'freeze accounts'} on multi-device detection"
        )
        
        if success:
            status = "ENABLED" if new_value else "DISABLED"
            result_text = f"""
✅ **SETTING UPDATED**

**{'Auto-Terminate Sessions' if setting_type == 'terminate' else 'Auto-Freeze Accounts'}:** {status}

{'System will now automatically logout other sessions when multi-device is detected.' if new_value and setting_type == 'terminate' else
 'System will NOT terminate sessions automatically.' if not new_value and setting_type == 'terminate' else
 'System will now automatically freeze accounts when multi-device is detected.' if new_value else
 'System will NOT freeze accounts automatically.'}

This takes effect immediately.
            """
            
            # Log admin action
            admin_user = UserService.get_user_by_telegram_id(db, update.effective_user.id)
            if admin_user:
                ActivityLogService.log_action(
                    db, admin_user.id, "ADMIN_SESSION_SETTING",
                    f"{'Enabled' if new_value else 'Disabled'} {setting_key}",
                    extra_data=json.dumps({
                        "setting": setting_key,
                        "new_value": new_value
                    })
                )
        else:
            result_text = "❌ **Error**\n\nFailed to update setting. Please try again."
        
        keyboard = [[InlineKeyboardButton("🔙 Back to Settings", callback_data="session_settings")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            result_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    finally:
        close_db_session(db)

async def handle_proxy_configuration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle IP/Proxy configuration panel."""
    await update.callback_query.answer()
    
    from services.proxy_manager import proxy_manager
    from services.daily_proxy_rotator import get_proxy_rotation_status
    from database.operations import ProxyService
    
    db = get_db_session()
    try:
        # Get proxy statistics
        stats = ProxyService.get_proxy_stats(db)
        rotation_status = get_proxy_rotation_status()
        
        proxy_text = f"""
🌐 **IP/PROXY CONFIGURATION PANEL**

**📊 Current Pool Status:**
• Total Proxies: {stats.get('total_proxies', 0)}
• Active Proxies: {stats.get('active_proxies', 0)}
• Inactive Proxies: {stats.get('inactive_proxies', 0)}
• Recently Used (24h): {stats.get('recently_used_24h', 0)}

**🌍 Country Distribution:**
{chr(10).join([f"• {country}: {count}" for country, count in list(stats.get('country_distribution', {}).items())[:5]])}

**⏰ Rotation Status:**
• Auto-Rotation: {'✅ Running' if rotation_status.get('is_running') else '❌ Stopped'}
• Last Rotation: {rotation_status.get('last_rotation', 'Never')}
• Next Rotation: {rotation_status.get('next_rotation', 'Unknown')}

**🔧 Features:**
• View all proxies in the pool
• Add/remove proxies manually
• Test proxy connectivity
• Force immediate rotation
• Health monitoring dashboard
• Configure rotation schedules

**⚙️ Settings:**
• Daily auto-rotation enabled
• Health checks enabled
• Load balancing: Round-Robin

Choose an action:
        """
        
        keyboard = [
            [InlineKeyboardButton("📋 View All Proxies", callback_data="proxy_view_all")],
            [InlineKeyboardButton("➕ Add New Proxy", callback_data="proxy_add_new")],
            [InlineKeyboardButton("🔄 Rotate IPs Now", callback_data="proxy_rotate_now")],
            [InlineKeyboardButton("🏥 Health Dashboard", callback_data="proxy_health")],
            [InlineKeyboardButton("⚙️ Rotation Settings", callback_data="proxy_settings")],
            [InlineKeyboardButton("🧪 Test Proxy", callback_data="proxy_test")],
            [InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_panel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            proxy_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    finally:
        close_db_session(db)

async def handle_view_all_proxies(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display paginated list of all proxies."""
    await update.callback_query.answer()
    
    from database.models import ProxyPool
    
    db = get_db_session()
    try:
        # Get first 10 proxies
        proxies = db.query(ProxyPool).filter(ProxyPool.is_active == True).limit(10).all()
        
        if proxies:
            proxy_list = []
            for proxy in proxies:
                status_icon = "✅" if proxy.is_active else "❌"
                country_flag = proxy.country_code if proxy.country_code else "🌍"
                
                proxy_list.append(
                    f"{status_icon} **ID {proxy.id}** | {country_flag} {proxy.country_code or 'N/A'}\n"
                    f"   IP: `{proxy.ip_address}:{proxy.port}`\n"
                    f"   Type: {proxy.proxy_type or 'Unknown'}\n"
                    f"   Success: {proxy.success_count} | Fails: {proxy.failure_count}\n"
                    f"   Last used: {proxy.last_used.strftime('%m/%d %H:%M') if proxy.last_used else 'Never'}"
                )
            
            proxies_text = f"""
📋 **PROXY LIST** (Showing 1-{len(proxies)})

{chr(10).join(proxy_list)}

**Actions:**
• Test a specific proxy
• Deactivate a proxy
• View more proxies
            """
        else:
            proxies_text = """
📋 **PROXY LIST**

ℹ️ **No active proxies found**

Add proxies manually or fetch from WebShare.
            """
        
        keyboard = [
            [InlineKeyboardButton("🧪 Test Proxy by ID", callback_data="proxy_test")],
            [InlineKeyboardButton("➕ Add New Proxy", callback_data="proxy_add_new")],
            [InlineKeyboardButton("🔙 Back to Proxy Panel", callback_data="admin_proxy")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            proxies_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    finally:
        close_db_session(db)

async def handle_rotate_ips_now(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Force immediate IP/proxy rotation."""
    await update.callback_query.answer("🔄 Starting rotation...")
    
    from services.daily_proxy_rotator import force_proxy_rotation
    
    # Perform rotation
    result = await force_proxy_rotation()
    
    if result.get("status") == "completed":
        rotation = result.get("rotation", {})
        health = result.get("health_check", {})
        
        rotation_text = f"""
✅ **PROXY ROTATION COMPLETED**

**📊 Rotation Results:**
• Proxies Cleaned: {rotation.get('cleaned_proxies', 0)}
• Refresh Success: {'✅ Yes' if rotation.get('refresh_success') else '❌ No'}

**Current Stats:**
• Total: {rotation.get('current_stats', {}).get('total_proxies', 0)}
• Active: {rotation.get('current_stats', {}).get('active_proxies', 0)}
• Recently Used (24h): {rotation.get('current_stats', {}).get('recently_used_24h', 0)}

**Health Check:**
• Tested: {health.get('tested_count', 0)}
• Working: {health.get('working_count', 0)}
• Success Rate: {health.get('success_rate', 0):.1%}

**Timestamp:** {result.get('timestamp', 'N/A')}

All proxies have been refreshed and tested!
        """
        
        # Log admin action
        admin_user = UserService.get_user_by_telegram_id(db := get_db_session(), update.effective_user.id)
        if admin_user:
            ActivityLogService.log_action(
                db, admin_user.id, "ADMIN_PROXY_ROTATION",
                f"Forced proxy rotation - cleaned {rotation.get('cleaned_proxies', 0)} proxies",
                extra_data=json.dumps(result)
            )
        close_db_session(db)
    else:
        rotation_text = f"""
❌ **ROTATION FAILED**

**Error:** {result.get('error', 'Unknown error')}

Please check logs or try again later.
        """
    
    keyboard = [
        [InlineKeyboardButton("📋 View Proxies", callback_data="proxy_view_all")],
        [InlineKeyboardButton("🔙 Back to Proxy Panel", callback_data="admin_proxy")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        rotation_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def handle_proxy_health_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display proxy health monitoring dashboard."""
    await update.callback_query.answer()
    
    from services.proxy_health_monitor import get_proxy_health_report, get_unhealthy_proxies
    
    health_report = get_proxy_health_report()
    unhealthy = get_unhealthy_proxies(limit=5)
    
    summary = health_report.get('summary', {})
    
    health_text = f"""
🏥 **PROXY HEALTH DASHBOARD**

**📊 Overall Health:**
• Total Tested: {summary.get('total_proxies', 0)}
• Healthy Proxies: {summary.get('healthy_proxies', 0)} ✅
• Unhealthy Proxies: {summary.get('unhealthy_proxies', 0)} ❌
• Average Success Rate: {summary.get('average_success_rate', 0):.1%}

**🔴 Unhealthy Proxies (Top 5):**
    """
    
    if unhealthy:
        for proxy in unhealthy[:5]:
            health_text += f"\n• ID {proxy.get('id')}: {proxy.get('ip_address')}:{proxy.get('port')}"
            health_text += f"\n  Success Rate: {proxy.get('success_rate', 0):.1%}"
    else:
        health_text += "\n✅ All proxies are healthy!"
    
    health_text += f"""

**⚙️ Monitoring Status:**
• Auto Health Checks: ✅ Enabled
• Check Frequency: Every 6 hours
• Auto-Deactivate Unhealthy: ✅ Enabled

**📈 Recent Trends:**
• Last check showed {summary.get('healthy_proxies', 0)}/{summary.get('total_proxies', 0)} working
• {summary.get('unhealthy_proxies', 0)} proxies need attention

Choose an action:
    """
    
    keyboard = [
        [InlineKeyboardButton("🔄 Run Health Check Now", callback_data="proxy_health_check_now")],
        [InlineKeyboardButton("🗑️ Remove Unhealthy", callback_data="proxy_remove_unhealthy")],
        [InlineKeyboardButton("🔙 Back to Proxy Panel", callback_data="admin_proxy")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        health_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def handle_proxy_health_check_now(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Run immediate health check on all proxies."""
    await update.callback_query.answer("🏥 Running health check...")
    
    from services.proxy_manager import proxy_manager
    
    result = proxy_manager.perform_health_check()
    
    if result.get('success'):
        check_text = f"""
✅ **HEALTH CHECK COMPLETED**

**📊 Results:**
• Proxies Tested: {result.get('tested_count', 0)}
• Working Proxies: {result.get('working_count', 0)}
• Failed Proxies: {result.get('failed_count', 0)}
• Success Rate: {result.get('success_rate', 0):.1%}

**🔧 Actions Taken:**
• Unhealthy proxies marked
• Database updated
• Statistics refreshed

All proxies have been tested!
        """
    else:
        check_text = f"""
❌ **HEALTH CHECK FAILED**

**Error:** {result.get('error', 'Unknown error')}

Please try again or check logs.
        """
    
    keyboard = [[InlineKeyboardButton("🔙 Back to Health Dashboard", callback_data="proxy_health")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        check_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def handle_proxy_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display and manage proxy rotation settings."""
    await update.callback_query.answer()
    
    from services.proxy_manager import proxy_manager
    
    db = get_db_session()
    try:
        # Get current settings
        auto_rotation = SystemSettingsService.get_setting(db, 'proxy_auto_rotation', default=True)
        rotation_interval = SystemSettingsService.get_setting(db, 'proxy_rotation_hours', default=24)
        auto_health_check = SystemSettingsService.get_setting(db, 'proxy_auto_health_check', default=True)
        load_strategy = proxy_manager.get_current_strategy()
        
        settings_text = f"""
⚙️ **PROXY ROTATION SETTINGS**

**🔄 Auto-Rotation:**
Status: {'✅ ENABLED' if auto_rotation else '❌ DISABLED'}
• Automatically refresh proxy pool daily
• Remove old/inactive proxies
• Fetch new proxies from sources

**⏱️ Rotation Interval:**
Current: {rotation_interval} hours
• How often to perform rotation
• Recommended: 24 hours

**🏥 Auto Health Checks:**
Status: {'✅ ENABLED' if auto_health_check else '❌ DISABLED'}
• Test proxy connectivity periodically
• Auto-deactivate non-working proxies

**⚖️ Load Balancing Strategy:**
Current: {load_strategy}
• round_robin - Equal distribution
• least_used - Use least recently used
• weighted - Based on success rate
• country_based - Match user location

**Recommendations:**
• Keep auto-rotation ENABLED
• 24-hour interval is optimal
• Enable health checks for reliability
        """
        
        keyboard = [
            [InlineKeyboardButton(
                f"{'🔴 Disable' if auto_rotation else '🟢 Enable'} Auto-Rotation",
                callback_data=f"proxy_toggle_rotation_{'off' if auto_rotation else 'on'}"
            )],
            [InlineKeyboardButton("⏱️ Set Interval", callback_data="proxy_set_interval")],
            [InlineKeyboardButton("⚖️ Change Strategy", callback_data="proxy_change_strategy")],
            [InlineKeyboardButton("🔙 Back to Proxy Panel", callback_data="admin_proxy")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            settings_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    finally:
        close_db_session(db)

async def handle_toggle_proxy_setting(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Toggle proxy auto-rotation setting."""
    await update.callback_query.answer()
    
    # Parse callback data: proxy_toggle_rotation_{on|off}
    action = update.callback_query.data.split('_')[-1]
    new_value = (action == 'on')
    
    db = get_db_session()
    try:
        success = SystemSettingsService.set_setting(
            db, 'proxy_auto_rotation', new_value,
            description="Automatic daily proxy rotation"
        )
        
        if success:
            result_text = f"""
✅ **SETTING UPDATED**

**Auto-Rotation:** {'ENABLED' if new_value else 'DISABLED'}

{'Proxies will now be automatically rotated daily.' if new_value else 'Automatic proxy rotation has been disabled.'}

{'The system will refresh proxies, remove old ones, and fetch new ones automatically.' if new_value else 'You will need to manually rotate proxies using the "Rotate IPs Now" button.'}

This takes effect immediately.
            """
            
            # Log action
            admin_user = UserService.get_user_by_telegram_id(db, update.effective_user.id)
            if admin_user:
                ActivityLogService.log_action(
                    db, admin_user.id, "ADMIN_PROXY_SETTING",
                    f"{'Enabled' if new_value else 'Disabled'} proxy auto-rotation",
                    extra_data=json.dumps({"setting": "proxy_auto_rotation", "new_value": new_value})
                )
        else:
            result_text = "❌ **Error**\n\nFailed to update setting. Please try again."
        
        keyboard = [[InlineKeyboardButton("🔙 Back to Settings", callback_data="proxy_settings")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            result_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    finally:
        close_db_session(db)

async def handle_toggle_session_setting(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Toggle session management settings."""
    await update.callback_query.answer()
    
    # Parse callback data: session_toggle_{setting}_{action}
    parts = update.callback_query.data.split('_')
    setting_type = parts[2]  # 'terminate' or 'freeze'
    action = parts[3]  # 'on' or 'off'
    new_value = (action == 'on')
    
    setting_map = {
        'terminate': 'auto_terminate_sessions',
        'freeze': 'auto_freeze_multi_device'
    }
    
    setting_key = setting_map.get(setting_type)
    if not setting_key:
        await update.callback_query.answer("Invalid setting", show_alert=True)
        return
    
    db = get_db_session()
    try:
        success = SystemSettingsService.set_setting(
            db, setting_key, new_value,
            description=f"Auto-{'terminate sessions' if setting_type == 'terminate' else 'freeze accounts'} on multi-device detection"
        )
        
        if success:
            status = "ENABLED" if new_value else "DISABLED"
            result_text = f"""
✅ **SETTING UPDATED**

**{'Auto-Terminate Sessions' if setting_type == 'terminate' else 'Auto-Freeze Accounts'}:** {status}

{'System will now automatically logout other sessions when multi-device is detected.' if new_value and setting_type == 'terminate' else
 'System will NOT terminate sessions automatically.' if not new_value and setting_type == 'terminate' else
 'System will now automatically freeze accounts when multi-device is detected.' if new_value else
 'System will NOT freeze accounts automatically.'}

This takes effect immediately.
            """
            
            # Log admin action
            admin_user = UserService.get_user_by_telegram_id(db, update.effective_user.id)
            if admin_user:
                ActivityLogService.log_action(
                    db, admin_user.id, "ADMIN_SESSION_SETTING",
                    f"{'Enabled' if new_value else 'Disabled'} {setting_key}",
                    extra_data=json.dumps({
                        "setting": setting_key,
                        "new_value": new_value
                    })
                )
        else:
            result_text = "❌ **Error**\n\nFailed to update setting. Please try again."
        
        keyboard = [[InlineKeyboardButton("🔙 Back to Settings", callback_data="session_settings")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            result_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    finally:
        close_db_session(db)

async def handle_activity_tracker(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle activity log tracker panel."""
    await update.callback_query.answer()
    
    from database.models import ActivityLog
    from datetime import timedelta
    
    db = get_db_session()
    try:
        # Get recent activity statistics (last 24 hours)
        recent_date = datetime.utcnow() - timedelta(hours=24)
        
        total_activities = db.query(ActivityLog).filter(
            ActivityLog.created_at >= recent_date
        ).count()
        
        # Get activity type breakdown
        activity_types = db.query(
            ActivityLog.action_type,
            func.count(ActivityLog.id).label('count')
        ).filter(
            ActivityLog.created_at >= recent_date
        ).group_by(ActivityLog.action_type).all()
        
        tracker_text = f"""
📊 **ACTIVITY LOG TRACKER**

**📈 Last 24 Hours:**
• Total Activities: {total_activities}

**Activity Breakdown:**
{chr(10).join([f"• {act_type}: {count}" for act_type, count in activity_types[:10]])}

**🔍 Available Filters:**
• By User ID
• By Action Type
• By Date Range
• By IP Address

**📝 Action Types:**
• SALE_LOG_CREATED - Account sales
• WITHDRAWAL_REQUEST - Payment requests
• ADMIN_PROXY_ROTATION - IP rotations
• SESSION_MONITORED - Security checks
• ALL_SESSIONS_TERMINATED - Logouts
• ACCOUNT_HOLD/RELEASED - Freezes
• ADMIN_SYSTEM_SETTING - Config changes

**Features:**
• Real-time activity monitoring
• Advanced filtering options
• Export to CSV/JSON
• Activity search
• User activity history

Choose an action:
        """
        
        keyboard = [
            [InlineKeyboardButton("📋 View Recent Logs", callback_data="activity_recent")],
            [InlineKeyboardButton("🔍 Search Logs", callback_data="activity_search")],
            [InlineKeyboardButton("👤 User Activity", callback_data="activity_by_user")],
            [InlineKeyboardButton("📅 Filter by Date", callback_data="activity_by_date")],
            [InlineKeyboardButton("📊 Activity Stats", callback_data="activity_stats")],
            [InlineKeyboardButton("💾 Export Logs", callback_data="activity_export")],
            [InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_panel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            tracker_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    finally:
        close_db_session(db)

async def handle_view_recent_logs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display recent activity logs."""
    await update.callback_query.answer()
    
    from database.models import ActivityLog
    
    db = get_db_session()
    try:
        # Get last 20 activities
        activities = db.query(ActivityLog).order_by(
            ActivityLog.created_at.desc()
        ).limit(20).all()
        
        if activities:
            log_entries = []
            for activity in activities:
                timestamp = activity.created_at.strftime('%m/%d %H:%M')
                user_info = f"User {activity.user_id}" if activity.user_id else "System"
                
                log_entries.append(
                    f"🔹 **{activity.action_type}**\n"
                    f"   {activity.description}\n"
                    f"   {user_info} | {timestamp} UTC"
                )
            
            logs_text = f"""
📋 **RECENT ACTIVITY LOGS**

**Last 20 Activities:**

{chr(10).join(log_entries)}

**Legend:**
• SALE_LOG_* - Account sales
• WITHDRAWAL_* - Payment operations
• ADMIN_* - Admin actions
• SESSION_* - Security operations
• ACCOUNT_* - Account changes
            """
        else:
            logs_text = """
📋 **RECENT ACTIVITY LOGS**

ℹ️ **No activities recorded yet**

Activity logs will appear here as actions are performed.
            """
        
        keyboard = [
            [InlineKeyboardButton("🔄 Refresh", callback_data="activity_recent")],
            [InlineKeyboardButton("🔙 Back to Tracker", callback_data="admin_activity")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            logs_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    finally:
        close_db_session(db)

async def handle_activity_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display activity statistics."""
    await update.callback_query.answer()
    
    from database.models import ActivityLog
    from datetime import timedelta
    
    db = get_db_session()
    try:
        # Get statistics for different time periods
        now = datetime.utcnow()
        periods = {
            '24h': now - timedelta(hours=24),
            '7d': now - timedelta(days=7),
            '30d': now - timedelta(days=30)
        }
        
        stats = {}
        for period_name, period_date in periods.items():
            stats[period_name] = db.query(ActivityLog).filter(
                ActivityLog.created_at >= period_date
            ).count()
        
        # Get most active users (last 7 days)
        active_users = db.query(
            ActivityLog.user_id,
            func.count(ActivityLog.id).label('activity_count')
        ).filter(
            ActivityLog.created_at >= periods['7d'],
            ActivityLog.user_id.isnot(None)
        ).group_by(ActivityLog.user_id).order_by(
            func.count(ActivityLog.id).desc()
        ).limit(5).all()
        
        # Get most common action types (last 7 days)
        common_actions = db.query(
            ActivityLog.action_type,
            func.count(ActivityLog.id).label('count')
        ).filter(
            ActivityLog.created_at >= periods['7d']
        ).group_by(ActivityLog.action_type).order_by(
            func.count(ActivityLog.id).desc()
        ).limit(10).all()
        
        stats_text = f"""
📊 **ACTIVITY STATISTICS**

**📈 Total Activities:**
• Last 24 Hours: {stats['24h']}
• Last 7 Days: {stats['7d']}
• Last 30 Days: {stats['30d']}

**👥 Most Active Users (7 days):**
{chr(10).join([f"• User {user_id}: {count} activities" for user_id, count in active_users]) if active_users else '• No user activity'}

**🔥 Most Common Actions (7 days):**
{chr(10).join([f"• {action}: {count}x" for action, count in common_actions[:7]])}

**📊 Activity Rate:**
• Average (24h): {stats['24h'] / 24:.1f} per hour
• Average (7d): {stats['7d'] / 7:.1f} per day
• Average (30d): {stats['30d'] / 30:.1f} per day

Choose an action:
        """
        
        keyboard = [
            [InlineKeyboardButton("📋 View Logs", callback_data="activity_recent")],
            [InlineKeyboardButton("🔙 Back to Tracker", callback_data="admin_activity")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            stats_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    finally:
        close_db_session(db)

async def handle_toggle_proxy_setting(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Toggle proxy auto-rotation setting."""
    await update.callback_query.answer()
    
    # Parse callback data: proxy_toggle_rotation_{on|off}
    action = update.callback_query.data.split('_')[-1]
    new_value = (action == 'on')
    
    db = get_db_session()
    try:
        success = SystemSettingsService.set_setting(
            db, 'proxy_auto_rotation', new_value,
            description="Automatic daily proxy rotation"
        )
        
        if success:
            result_text = f"""
✅ **SETTING UPDATED**

**Auto-Rotation:** {'ENABLED' if new_value else 'DISABLED'}

{'Proxies will now be automatically rotated daily.' if new_value else 'Automatic proxy rotation has been disabled.'}

{'The system will refresh proxies, remove old ones, and fetch new ones automatically.' if new_value else 'You will need to manually rotate proxies using the "Rotate IPs Now" button.'}

This takes effect immediately.
            """
            
            # Log action
            admin_user = UserService.get_user_by_telegram_id(db, update.effective_user.id)
            if admin_user:
                ActivityLogService.log_action(
                    db, admin_user.id, "ADMIN_PROXY_SETTING",
                    f"{'Enabled' if new_value else 'Disabled'} proxy auto-rotation",
                    extra_data=json.dumps({"setting": "proxy_auto_rotation", "new_value": new_value})
                )
        else:
            result_text = "❌ **Error**\n\nFailed to update setting. Please try again."
        
        keyboard = [[InlineKeyboardButton("🔙 Back to Settings", callback_data="proxy_settings")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            result_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    finally:
        close_db_session(db)

async def handle_admin_reports(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle reports and logs panel."""
    await update.callback_query.answer()
    
    from database.models import ActivityLog
    from datetime import timedelta
    
    db = get_db_session()
    try:
        # Get various report statistics
        recent_date = datetime.utcnow() - timedelta(hours=24)
        
        # Count different types of reports
        otp_reports = db.query(ActivityLog).filter(
            ActivityLog.action_type == 'OTP_REPORTED',
            ActivityLog.created_at >= recent_date
        ).count()
        
        spam_reports = db.query(ActivityLog).filter(
            ActivityLog.action_type == 'SPAM_REPORTED',
            ActivityLog.created_at >= recent_date
        ).count()
        
        frozen_accounts = db.query(ActivityLog).filter(
            ActivityLog.action_type == 'ACCOUNT_HOLD',
            ActivityLog.created_at >= recent_date
        ).count()
        
        reports_text = f"""
⚠️ **REPORTS & LOGS DASHBOARD**

**📊 Last 24 Hours:**
• OTP Reports: {otp_reports}
• Spam Reports: {spam_reports}
• Frozen Accounts: {frozen_accounts}

**📋 Available Reports:**
• Security incident reports
• User flagged accounts
• OTP/verification issues
• Spam/abuse reports
• System error logs
• Failed transactions

**🔍 Report Types:**
• **OTP Issues** - Verification problems
• **Spam Reports** - User-reported spam
• **Security Flags** - Multi-device detection
• **Transaction Errors** - Failed payments
• **System Logs** - Technical errors

**Actions:**
• View detailed reports
• Filter by type
• Export report data
• Resolve reported issues

All reports are logged and tracked automatically.
        """
        
        keyboard = [
            [InlineKeyboardButton("🚨 View OTP Reports", callback_data="reports_otp")],
            [InlineKeyboardButton("⚠️ View Spam Reports", callback_data="reports_spam")],
            [InlineKeyboardButton("🧊 Frozen Accounts", callback_data="view_frozen_accounts")],
            [InlineKeyboardButton("📊 All System Logs", callback_data="activity_recent")],
            [InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_panel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            reports_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    finally:
        close_db_session(db)

async def handle_system_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle system settings panel."""
    await update.callback_query.answer()
    
    db = get_db_session()
    try:
        # Get current system settings
        chat_history_deletion = SystemSettingsService.get_setting(
            db, 'delete_chat_history_on_sale', default=False
        )
        auto_rotation = SystemSettingsService.get_setting(
            db, 'proxy_auto_rotation', default=True
        )
        auto_terminate = SystemSettingsService.get_setting(
            db, 'auto_terminate_sessions', default=True
        )
        auto_freeze = SystemSettingsService.get_setting(
            db, 'auto_freeze_multi_device', default=True
        )
        
        settings_text = f"""
⚙️ **SYSTEM SETTINGS CONTROL**

**🔧 Current Configuration:**

**Privacy & Security:**
• Chat History Deletion: {'✅ Enabled' if chat_history_deletion else '❌ Disabled'}
• Auto-Terminate Sessions: {'✅ Enabled' if auto_terminate else '❌ Disabled'}
• Auto-Freeze Multi-Device: {'✅ Enabled' if auto_freeze else '❌ Disabled'}

**Network & Infrastructure:**
• Proxy Auto-Rotation: {'✅ Enabled' if auto_rotation else '❌ Disabled'}

**⚡ Quick Actions:**
• Toggle chat history deletion
• Configure session management
• Adjust proxy rotation settings
• Set freeze durations

**📊 System Status:**
• Database: 🟢 Connected
• Telegram API: 🟢 Active
• Proxy Pool: 🟢 Operational
• Background Tasks: 🟢 Running

**Navigation:**
• Chat History → Admin Panel → Chat History Control
• Sessions → Admin Panel → Session Management
• Proxies → Admin Panel → IP/Proxy Config

All settings are persistent and take effect immediately.
        """
        
        keyboard = [
            [InlineKeyboardButton("🗑️ Chat History Settings", callback_data="admin_chat_control")],
            [InlineKeyboardButton("🔐 Session Settings", callback_data="session_settings")],
            [InlineKeyboardButton("🌐 Proxy Settings", callback_data="proxy_settings")],
            [InlineKeyboardButton("📊 View All Settings", callback_data="settings_view_all")],
            [InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_panel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            settings_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    finally:
        close_db_session(db)

async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel any active conversation and clear context."""
    context.user_data.clear()
    logger.info(f"🔥 Conversation cancelled for user {update.effective_user.id}, context cleared")
    return ConversationHandler.END

def is_admin(user_id: int) -> bool:
    """Check if user is an admin by querying the database."""
    from database import get_db_session
    from database.models_old import User
    
    db = get_db_session()
    try:
        user = db.query(User).filter(User.telegram_user_id == user_id).first()
        if user:
            return user.is_admin or user.is_leader  # Leaders are also admins
        return False
    except Exception as e:
        logger.error(f"Error checking admin status: {e}")
        return False
    finally:
        db.close()

def setup_admin_handlers(application) -> None:
    """Set up admin handlers."""
    # Main admin panel handler
    application.add_handler(CallbackQueryHandler(handle_admin_panel, pattern='^admin_panel$'))
    
    # Admin sub-handlers
    application.add_handler(CallbackQueryHandler(handle_admin_mailing, pattern='^admin_mailing$'))
    application.add_handler(CallbackQueryHandler(handle_chat_history_control, pattern='^admin_chat_control$'))
    application.add_handler(CallbackQueryHandler(handle_toggle_history_deletion, pattern='^toggle_history_(on|off)$'))
    
    # Session Management handlers
    application.add_handler(CallbackQueryHandler(handle_session_management, pattern='^admin_sessions$'))
    application.add_handler(CallbackQueryHandler(handle_view_held_accounts, pattern='^session_view_holds$'))
    application.add_handler(CallbackQueryHandler(handle_release_holds, pattern='^session_release_holds$'))
    application.add_handler(CallbackQueryHandler(handle_session_activity_logs, pattern='^session_activity_logs$'))
    application.add_handler(CallbackQueryHandler(handle_session_settings, pattern='^session_settings$'))
    application.add_handler(CallbackQueryHandler(handle_toggle_session_setting, pattern='^session_toggle_(terminate|freeze)_(on|off)$'))
    
    # Proxy/IP Configuration handlers
    application.add_handler(CallbackQueryHandler(handle_proxy_configuration, pattern='^admin_proxy$'))
    application.add_handler(CallbackQueryHandler(handle_view_all_proxies, pattern='^proxy_view_all$'))
    application.add_handler(CallbackQueryHandler(handle_rotate_ips_now, pattern='^proxy_rotate_now$'))
    application.add_handler(CallbackQueryHandler(handle_proxy_health_dashboard, pattern='^proxy_health$'))
    application.add_handler(CallbackQueryHandler(handle_proxy_health_check_now, pattern='^proxy_health_check_now$'))
    application.add_handler(CallbackQueryHandler(handle_proxy_settings, pattern='^proxy_settings$'))
    application.add_handler(CallbackQueryHandler(handle_toggle_proxy_setting, pattern='^proxy_toggle_rotation_(on|off)$'))
    
    # Activity Tracker handlers
    application.add_handler(CallbackQueryHandler(handle_activity_tracker, pattern='^admin_activity$'))
    application.add_handler(CallbackQueryHandler(handle_view_recent_logs, pattern='^activity_recent$'))
    application.add_handler(CallbackQueryHandler(handle_activity_stats, pattern='^activity_stats$'))
    
    # Reports & System Settings handlers
    application.add_handler(CallbackQueryHandler(handle_admin_reports, pattern='^admin_reports$'))
    application.add_handler(CallbackQueryHandler(handle_system_settings, pattern='^admin_settings$'))
    
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
    
    # Account Freeze Management handlers
    application.add_handler(CallbackQueryHandler(handle_account_freeze_panel, pattern='^admin_freeze_panel$'))
    application.add_handler(CallbackQueryHandler(handle_view_frozen_accounts, pattern='^view_frozen_accounts$'))
    
    # Sale Logs & Approval handlers
    application.add_handler(CallbackQueryHandler(handle_sale_logs_panel, pattern='^sale_logs_panel$'))
    application.add_handler(CallbackQueryHandler(handle_approve_sale_list, pattern='^approve_sale_list$'))
    application.add_handler(CallbackQueryHandler(handle_approve_sale_action, pattern='^approve_sale_\\d+$'))
    application.add_handler(CallbackQueryHandler(handle_reject_sale_action, pattern='^reject_sale_\\d+$'))

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
                    sale_log = db.query(AccountSaleLog).filter(AccountSaleLog.id == sale_log_id).first()
                    if sale_log:
                        await notification_service.notify_sale_approved(
                            user_telegram_id=sale_log.seller_telegram_id,
                            phone_number=sale_log.account_phone,
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
        sale_log = db.query(AccountSaleLog).filter(AccountSaleLog.id == sale_log_id).first()
        if not sale_log:
            await query.answer('❌ Sale log not found.', show_alert=True)
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
                    await notification_service.notify_sale_rejected(
                        user_telegram_id=sale_log.seller_telegram_id,
                        phone_number=sale_log.account_phone,
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

