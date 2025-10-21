"""
Verification Flow Handlers
Handles CAPTCHA verification and channel membership verification
"""
import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import get_db_session, close_db_session
from database.operations import UserService
from services.captcha import CaptchaService

logger = logging.getLogger(__name__)


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
        [
            InlineKeyboardButton("❓ Why Verification?", callback_data="why_verification"),
            InlineKeyboardButton("🆘 Contact Support", callback_data="contact_support")
        ]
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
    
    user = update.effective_user
    
    # Store CAPTCHA data in database instead of context
    db = get_db_session()
    try:
        db_user = UserService.get_user_by_telegram_id(db, user.id)
        if db_user:
            # Store CAPTCHA data in user record
            db_user.captcha_answer = captcha_data['answer']
            db_user.captcha_type = captcha_data['type']
            db_user.captcha_image_path = captcha_data.get('image_path')
            db_user.verification_step = 1
            db.commit()
    finally:
        close_db_session(db)
    
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
    
    # Store CAPTCHA answer in context as backup
    context.user_data['captcha_answer'] = captcha_data['answer']
    context.user_data['captcha_type'] = captcha_data['type']
    context.user_data['captcha_image_path'] = captcha_data.get('image_path')
    context.user_data['verification_step'] = 1
    
    # Try to edit message text, if it fails send new message
    try:
        if update.callback_query and update.callback_query.message:
            if update.callback_query.message.text:
                await update.callback_query.edit_message_text(
                    verification_text,
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
            else:
                await update.callback_query.message.reply_text(
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
    except Exception as e:
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
            # Delete old CAPTCHA image if it exists (prevents chat bloat)
            if 'captcha_photo_message_id' in context.user_data and 'captcha_chat_id' in context.user_data:
                try:
                    await context.bot.delete_message(
                        chat_id=context.user_data['captcha_chat_id'],
                        message_id=context.user_data['captcha_photo_message_id']
                    )
                    logger.info(f"Deleted old CAPTCHA image for user {user.id}")
                except Exception as delete_error:
                    logger.warning(f"Could not delete old CAPTCHA image: {delete_error}")
            
            # Send new CAPTCHA image
            with open(captcha_data['image_path'], 'rb') as photo:
                if update.callback_query and update.callback_query.message:
                    photo_message = await update.callback_query.message.reply_photo(
                        photo=photo,
                        caption="🔍 **Enter the text shown in this image**",
                        parse_mode='Markdown'
                    )
                    context.user_data['captcha_photo_message_id'] = photo_message.message_id
                    context.user_data['captcha_chat_id'] = photo_message.chat_id
                elif update.message:
                    photo_message = await update.message.reply_photo(
                        photo=photo,
                        caption="🔍 **Enter the text shown in this image**",
                        parse_mode='Markdown'
                    )
                    context.user_data['captcha_photo_message_id'] = photo_message.message_id
                    context.user_data['captcha_chat_id'] = photo_message.chat_id
        except Exception as e:
            logger.error(f"Error sending captcha image: {e}")
            # Fallback to text-based captcha
            try:
                fallback_text = "⚠️ **Image failed to load. Fallback question:**\n\nWhat is 25 + 17?"
                if update.callback_query and update.callback_query.message:
                    await update.callback_query.message.reply_text(fallback_text)
                elif update.message:
                    await update.message.reply_text(fallback_text)
                context.user_data['captcha_answer'] = "42"
                # Update database with fallback
                db = get_db_session()
                try:
                    db_user = UserService.get_user_by_telegram_id(db, user.id)
                    if db_user:
                        db_user.captcha_answer = "42"
                        db.commit()
                finally:
                    close_db_session(db)
            except Exception as fallback_error:
                logger.error(f"Failed to send fallback captcha: {fallback_error}")


async def handle_captcha_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle CAPTCHA text answers for both visual and text captchas."""
    user = update.effective_user
    user_answer = update.message.text.strip()
    
    db = get_db_session()
    try:
        # Get user and CAPTCHA data from database
        db_user = UserService.get_user_by_telegram_id(db, user.id)
        
        if not db_user:
            logger.error(f"User {user.id} not found in database")
            await update.message.reply_text("❌ Error: User not found. Please restart with /start")
            return
        
        # Get CAPTCHA data from database (with context as fallback)
        correct_answer = (db_user.captcha_answer or context.user_data.get('captcha_answer', '')).lower().strip()
        captcha_image_path = db_user.captcha_image_path or context.user_data.get('captcha_image_path')
        
        logger.info(f"CAPTCHA verification for user {user.id}: answer='{user_answer}', expected='{correct_answer}'")
        
        # Clean up visual captcha image if exists
        if captcha_image_path:
            captcha_service = CaptchaService()
            captcha_service.cleanup_captcha_image(captcha_image_path)
            # Clear from database and context
            if db_user:
                db_user.captcha_image_path = None
            context.user_data.pop('captcha_image_path', None)
        
        if user_answer.lower() == correct_answer:
            # CAPTCHA passed - update user status
            if db_user:
                UserService.update_user(db, db_user.id, captcha_verified=True)
            
            # Delete the captcha photo message if exists
            captcha_photo_message_id = context.user_data.get('captcha_photo_message_id')
            captcha_chat_id = context.user_data.get('captcha_chat_id')
            if captcha_photo_message_id and captcha_chat_id:
                try:
                    await context.bot.delete_message(chat_id=captcha_chat_id, message_id=captcha_photo_message_id)
                except Exception as e:
                    logger.warning(f"Could not delete captcha photo message: {e}")
                context.user_data.pop('captcha_photo_message_id', None)
                context.user_data.pop('captcha_chat_id', None)
            
            success_text = """
✅ **CAPTCHA Verified Successfully!**

Great job! You've proven you're human.

**Next Step:** Channel Verification
            """
            
            keyboard = [[InlineKeyboardButton("📢 Continue to Channels", callback_data="show_channels")]]
            await update.message.reply_text(
                success_text,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
            # Clear captcha data from database and context
            if db_user:
                db_user.captcha_answer = None
                db_user.captcha_type = None
                db_user.verification_step = 2
                db.commit()
            
            context.user_data.pop('captcha_answer', None)
            context.user_data.pop('captcha_type', None)
            context.user_data['verification_step'] = 2
            
        else:
            # Wrong answer - try again
            fail_text = f"""
❌ **Incorrect Answer**

**Your answer:** {user_answer}
**Expected:** (hidden for security)

Please try again or request a new CAPTCHA.
            """
            
            keyboard = [
                [InlineKeyboardButton("🔄 New CAPTCHA", callback_data="new_captcha")],
                [InlineKeyboardButton("🆘 Contact Support", callback_data="contact_support")]
            ]
            await update.message.reply_text(
                fail_text,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    
    finally:
        close_db_session(db)


async def show_channel_verification(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show channel joining verification step."""
    from services.captcha import VerificationTaskService
    
    context.user_data['verification_step'] = 2
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


async def handle_verify_channels(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Verify user has joined all required channels."""
    from services.captcha import VerificationTaskService
    
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    task_service = VerificationTaskService()
    channels = task_service.get_required_channels()
    enforce_membership = os.getenv('ENFORCE_CHANNEL_MEMBERSHIP', 'false').lower() == 'true'
    
    # Check membership in all channels
    not_joined = []
    for channel in channels:
        channel_name = channel.get('name', 'Unnamed Channel')

        # Determine the best identifier for the channel
        chat_identifier = channel.get('id')
        channel_username = channel.get('username')

        if not chat_identifier and channel_username:
            chat_identifier = f"@{channel_username.lstrip('@')}"

        if not chat_identifier and channel.get('link'):
            extracted_username = channel['link'].rstrip('/').split('/')[-1]
            if extracted_username:
                chat_identifier = f"@{extracted_username.lstrip('@')}"

        if not chat_identifier:
            logger.error(
                "Channel configuration missing identifier for membership check: %s",
                channel
            )
            not_joined.append(channel_name)
            continue

        try:
            member = await context.bot.get_chat_member(chat_identifier, user.id)
            if getattr(member, 'status', None) in ['left', 'kicked']:
                not_joined.append(channel_name)
        except Exception as e:
            logger.error(f"Error checking membership in {channel_name}: {e}")
            not_joined.append(channel_name)
    
    if not_joined and enforce_membership:
        # User hasn't joined all channels
        fail_text = f"""
❌ **Verification Failed**

You haven't joined these channels yet:
"""
        for channel_name in not_joined:
            fail_text += f"\\n• {channel_name}"
        
        fail_text += """

Please join ALL channels and try again.
        """

        await query.edit_message_text(fail_text, parse_mode='Markdown')
        
        # Show channels again after 3 seconds
        import asyncio
        await asyncio.sleep(3)
        await show_channel_verification(update, context)
    
    else:
        # All channels joined - update user status
        db = get_db_session()
        try:
            db_user = UserService.get_user_by_telegram_id(db, user.id)
            if db_user:
                UserService.update_user(
                    db,
                    db_user.id,
                    captcha_completed=True,
                    channels_joined=True,
                    channels_verified=True,
                    verification_completed=True,
                    is_verified=True
                )
            
            channel_status_line = "✅ All Channels Joined" if not not_joined else "⚠️ Channel Join Skipped"
            success_text = f"""
🎉 **Verification Complete!**

✅ CAPTCHA Verified
{channel_status_line}
✅ Account Activated

**You now have full access to the platform!**

Welcome to the Telegram Account Selling community! 🚀
            """

            if not_joined and not enforce_membership:
                skipped_channels = "\n".join(f"• {channel}" for channel in not_joined)
                success_text += f"""

⚠️ *Note: Channel membership not enforced.*
The following channels were skipped:
{skipped_channels}
Please make sure you join them later for important announcements.
                """
            
            keyboard = [[InlineKeyboardButton("🏠 Go to Main Menu", callback_data="real_main_menu")]]
            await query.edit_message_text(
                success_text,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
            context.user_data['verification_step'] = 3
            context.user_data['verified'] = True
        
        finally:
            close_db_session(db)
