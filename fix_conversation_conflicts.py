"""
Professional Fix for Conversation Handler Conflicts
Removes duplicate handlers and creates proper isolation between:
1. Withdrawal conversation (wallet addresses)
2. Selling conversation (phone numbers)
"""

import re

def fix_handler_file():
    """Remove duplicate conversation handlers and fix the mess."""
    
    with open('handlers/real_handlers.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find the first occurrence of debug_withdrawal_text_handler
    first_handler_match = re.search(r'async def debug_withdrawal_text_handler.*?return ConversationHandler\.END', content, re.DOTALL)
    
    if not first_handler_match:
        print("❌ No debug_withdrawal_text_handler found")
        return False
    
    first_handler_end = first_handler_match.end()
    
    # Find the second occurrence (duplicate)
    remaining_content = content[first_handler_end:]
    second_handler_match = re.search(r'async def debug_withdrawal_text_handler.*?return ConversationHandler\.END', remaining_content, re.DOTALL)
    
    if second_handler_match:
        # Remove the second occurrence entirely
        second_start_in_full = first_handler_end + second_handler_match.start()
        second_end_in_full = first_handler_end + second_handler_match.end()
        
        print(f"🔧 Removing duplicate handler from position {second_start_in_full} to {second_end_in_full}")
        
        # Also remove the duplicate withdrawal_conversation definition after it
        remaining_after_second = content[second_end_in_full:]
        duplicate_conv_match = re.search(r'\s*withdrawal_conversation = ConversationHandler\(.*?\)\s*application\.add_handler\(withdrawal_conversation\)', remaining_after_second, re.DOTALL)
        
        if duplicate_conv_match:
            duplicate_conv_end = second_end_in_full + duplicate_conv_match.end()
            print(f"🔧 Also removing duplicate conversation handler registration")
            content = content[:second_start_in_full] + content[duplicate_conv_end:]
        else:
            content = content[:second_start_in_full] + content[second_end_in_full:]
    
    # Now replace the remaining debug_withdrawal_text_handler with a proper isolated one
    isolated_handler = '''    # ISOLATED Withdrawal Text Handler - Only processes withdrawal conversations
    async def isolated_withdrawal_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Isolated handler for withdrawal text input - only processes withdrawal conversations."""
        user = update.effective_user
        message_text = update.message.text if update.message else "No text"
        
        # STRICT ISOLATION: Only handle if we're explicitly in a withdrawal conversation
        if context.user_data.get('conversation_type') != 'withdrawal':
            # Not our conversation - completely ignore, don't return anything
            logger.info(f"🔒 ISOLATION - User {user.id} sent text '{message_text}' but not in withdrawal conversation. Ignoring.")
            return  # Let other handlers process this
        
        logger.info(f"💸 WITHDRAWAL - User {user.id} sent text: '{message_text}'")
        
        try:
            # Call the original withdrawal details handler
            result = await handle_withdrawal_details(update, context)
            logger.info(f"💸 WITHDRAWAL - Handler returned: {result}")
            return result
        except Exception as e:
            logger.error(f"💸 WITHDRAWAL - ERROR in handle_withdrawal_details: {e}")
            import traceback
            logger.error(f"💸 WITHDRAWAL - Full traceback: {traceback.format_exc()}")
            await update.message.reply_text(f"❌ Withdrawal Error: {str(e)}\\n\\nPlease try again or contact support.")
            return ConversationHandler.END'''
    
    # Replace the debug handler with isolated handler
    content = re.sub(
        r'async def debug_withdrawal_text_handler.*?return ConversationHandler\.END',
        isolated_handler,
        content,
        flags=re.DOTALL
    )
    
    # Update the handler reference in the conversation
    content = content.replace('debug_withdrawal_text_handler', 'isolated_withdrawal_text_handler')
    
    # Also ensure phone handler is properly isolated
    phone_handler_fix = '''async def handle_real_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle phone number input via text message - ISOLATED to selling conversations only."""
    user = update.effective_user
    message_text = update.message.text if update.message else "No text"
    
    # STRICT ISOLATION: Only handle if we're explicitly in a selling conversation
    if context.user_data.get('conversation_type') != 'selling':
        logger.info(f"🔒 PHONE ISOLATION - User {user.id} sent text '{message_text}' but not in selling conversation. Ignoring.")
        return ConversationHandler.END  # End this conversation, let other handlers process
    
    logger.info(f"📱 SELLING - User {user.id} sent phone: '{message_text}'")
    
    phone = message_text.strip()
    
    # Validate phone format
    if not phone.startswith('+') or len(phone) < 8:
        await update.message.reply_text(
            "❌ **Invalid Format!**\\n\\nPlease include country code: `+1234567890`",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu")]
            ])
        )
        return PHONE
    
    # Store phone and send OTP
    context.user_data['phone'] = phone'''
    
    # Replace the phone handler with isolated version
    content = re.sub(
        r'async def handle_real_phone\(update: Update, context: ContextTypes\.DEFAULT_TYPE\) -> int:\s*""".*?""".*?phone = update\.message\.text\.strip\(\)',
        phone_handler_fix,
        content,
        flags=re.DOTALL
    )
    
    # Write the fixed content
    with open('handlers/real_handlers.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Fixed conversation handler conflicts!")
    print("🔧 Removed duplicate handlers")
    print("🔒 Added strict conversation isolation")
    print("📱 Phone handler only processes 'selling' conversations")
    print("💸 Withdrawal handler only processes 'withdrawal' conversations")
    
    return True

if __name__ == "__main__":
    print("🚀 Fixing conversation handler conflicts...")
    if fix_handler_file():
        print("✅ Fix completed successfully!")
    else:
        print("❌ Fix failed!")