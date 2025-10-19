"""Admin command handlers for the Telegram Account Bot."""
import logging
import json
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ConversationHandler

from database import get_db_session, close_db_session
from database.operations import UserService, SystemSettingsService, ActivityLogService
from database.models import User, UserStatus, AccountSaleLog
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
    
    broadcast_message = update.message.text
    broadcast_type = context.user_data.get('broadcast_type', 'all')
    
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
            users = db.query(User).filter(User.status == UserStatus.ACTIVE).all()
            target_desc = "active users"
        elif broadcast_type == 'frozen':
            users = db.query(User).filter(User.status == UserStatus.FROZEN).all()
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

def is_admin(user_id: int) -> bool:
    """Check if user is an admin."""
    ADMIN_IDS = [6733908384]  # Your admin ID
    return user_id in ADMIN_IDS

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
            CallbackQueryHandler(handle_admin_mailing, pattern='^admin_mailing$')
        ],
        name="admin_broadcast_conversation"
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
            CallbackQueryHandler(handle_admin_panel, pattern='^admin_panel$')
        ]
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

