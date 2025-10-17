"""
Simple Telegram Account Selling Bot - No KYC, Core Functionality Only
Focus: Phone → OTP → 2FA Detection → Account Setup → Sale
"""
import logging
import random
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CallbackQueryHandler, MessageHandler, filters

logger = logging.getLogger(__name__)

# Simple conversation states
PHONE, OTP, DISABLE_2FA, NAME, PHOTO, NEW_2FA, CONFIRM = range(7)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Simple start command - no verification needed."""
    welcome_text = """
🤖 **Telegram Account Marketplace**

**💰 Sell Your Telegram Account Instantly!**

**How it works:**
1. 📱 Provide phone number
2. 🔐 Enter OTP code  
3. ⚙️ Account setup
4. 💵 Get paid instantly!

**Ready to sell?**
    """
    
    keyboard = [
        [InlineKeyboardButton("💰 Sell My Account", callback_data="start_selling")],
        [InlineKeyboardButton("📊 My Sales History", callback_data="sales_history")],
        [InlineKeyboardButton("💳 Check Balance", callback_data="balance")],
        [InlineKeyboardButton("🆘 Support", url="https://t.me/BujhlamNaKiHolo")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(welcome_text, parse_mode='Markdown', reply_markup=reply_markup)
    else:
        await update.message.reply_text(welcome_text, parse_mode='Markdown', reply_markup=reply_markup)

async def start_selling(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the selling process."""
    sell_text = """
📱 **Step 1: Phone Number**

Please enter your **Telegram phone number** with country code:

**Format:** +1234567890

**Example:** +1234567890

**What we'll do:**
• Login securely to verify ownership
• Configure account settings  
• Transfer ownership safely
• Pay you instantly! 💰
    """
    
    keyboard = [[InlineKeyboardButton("❌ Cancel", callback_data="main_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(sell_text, parse_mode='Markdown', reply_markup=reply_markup)
    return PHONE

async def handle_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle phone number input."""
    phone = update.message.text.strip()
    
    if not phone.startswith('+') or len(phone) < 8:
        await update.message.reply_text(
            "❌ Invalid format. Please use: +1234567890",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="main_menu")]])
        )
        return PHONE
    
    context.user_data['phone'] = phone
    
    otp_text = f"""
📨 **Step 2: Verification Code**

We're sending a login code to: `{phone}`

Please enter the **5-digit code** you receive:

**Waiting for your code...**
    """
    
    await update.message.reply_text(otp_text, parse_mode='Markdown')
    return OTP

async def handle_otp(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle OTP and detect 2FA."""
    code = update.message.text.strip()
    
    if not code.isdigit() or len(code) != 5:
        await update.message.reply_text("❌ Invalid code. Please enter 5 digits:")
        return OTP
    
    context.user_data['otp'] = code
    
    # Simulate 2FA detection
    has_2fa = random.choice([True, False])
    
    if has_2fa:
        disable_text = """
🔐 **2FA Detected!**

**Step 3: Disable 2FA**

Your account has **Two-Factor Authentication** enabled.

**⚠️ You must DISABLE 2FA first:**

1. Go to **Settings** → **Privacy & Security**
2. Select **Two-Step Verification**
3. **Turn OFF** Two-Step Verification
4. Enter your password to confirm

**Once disabled, click button below:**
        """
        
        keyboard = [
            [InlineKeyboardButton("✅ 2FA Disabled", callback_data="2fa_disabled")],
            [InlineKeyboardButton("❌ Cancel", callback_data="main_menu")]
        ]
        
        await update.message.reply_text(disable_text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
        return DISABLE_2FA
    else:
        # No 2FA, proceed to name setup
        return await ask_name(update, context)

async def handle_2fa_disabled(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle 2FA disabled confirmation."""
    await update.callback_query.answer("✅ 2FA Disabled!")
    return await ask_name(update, context)

async def ask_name(update, context) -> int:
    """Ask for account name."""
    name_text = """
👤 **Step 4: Account Name**

Enter the **new name** for this account:

**Examples:**
• John Smith
• Sarah Wilson
• Mike Johnson

**Enter name:**
    """
    
    keyboard = [
        [InlineKeyboardButton("🎲 Random Name", callback_data="random_name")],
        [InlineKeyboardButton("❌ Cancel", callback_data="main_menu")]
    ]
    
    if hasattr(update, 'callback_query') and update.callback_query:
        await update.callback_query.edit_message_text(name_text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(name_text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    
    return NAME

async def handle_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle name input."""
    if update.callback_query and update.callback_query.data == "random_name":
        names = ["John Smith", "Sarah Wilson", "Mike Johnson", "Emma Davis", "Alex Brown"]
        name = random.choice(names)
        await update.callback_query.answer(f"Selected: {name}")
        context.user_data['name'] = name
    else:
        name = update.message.text.strip()
        if len(name) < 2:
            await update.message.reply_text("❌ Name too short. Try again:")
            return NAME
        context.user_data['name'] = name
    
    # Ask for photo
    photo_text = """
📸 **Step 5: Profile Photo**

Send a **photo** for the profile picture:

**Options:**
• Send any image
• Use random avatar
• Skip photo setup
    """
    
    keyboard = [
        [InlineKeyboardButton("🎲 Random Photo", callback_data="random_photo")],
        [InlineKeyboardButton("⏭️ Skip Photo", callback_data="skip_photo")],
        [InlineKeyboardButton("❌ Cancel", callback_data="main_menu")]
    ]
    
    if hasattr(update, 'callback_query') and update.callback_query:
        await update.callback_query.edit_message_text(photo_text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(photo_text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    
    return PHOTO

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle photo input."""
    if update.callback_query:
        if update.callback_query.data == "random_photo":
            await update.callback_query.answer("✅ Random photo selected")
            context.user_data['photo'] = "random"
        elif update.callback_query.data == "skip_photo":
            await update.callback_query.answer("⏭️ Photo skipped")
            context.user_data['photo'] = None
    elif update.message and update.message.photo:
        context.user_data['photo'] = "uploaded"
        await update.message.reply_text("✅ Photo received!")
    else:
        await update.message.reply_text("❌ Please send photo or use buttons.")
        return PHOTO
    
    # Ask for new 2FA password
    twofa_text = """
🔐 **Step 6: New 2FA Password**

Create a **strong password** for the new 2FA:

**Requirements:**
• 8+ characters
• Mix letters & numbers

**Enter password:**
    """
    
    keyboard = [
        [InlineKeyboardButton("🎲 Generate Password", callback_data="generate_pass")],
        [InlineKeyboardButton("❌ Cancel", callback_data="main_menu")]
    ]
    
    if hasattr(update, 'callback_query') and update.callback_query:
        await update.callback_query.edit_message_text(twofa_text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(twofa_text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    
    return NEW_2FA

async def handle_new_2fa(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle new 2FA password."""
    if update.callback_query and update.callback_query.data == "generate_pass":
        password = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789', k=10))
        await update.callback_query.answer(f"Generated: {password}")
        context.user_data['new_2fa'] = password
    else:
        password = update.message.text.strip()
        if len(password) < 8:
            await update.message.reply_text("❌ Password too short (min 8 chars):")
            return NEW_2FA
        context.user_data['new_2fa'] = password
    
    # Show confirmation
    return await show_confirmation(update, context)

async def show_confirmation(update, context) -> int:
    """Show final confirmation."""
    phone = context.user_data.get('phone')
    name = context.user_data.get('name')
    photo = context.user_data.get('photo')
    new_2fa = context.user_data.get('new_2fa')
    
    price = round(random.uniform(15, 35), 2)
    
    confirm_text = f"""
✅ **Final Confirmation**

**📋 Sale Summary:**
• 📱 **Phone:** `{phone}`
• 👤 **New Name:** `{name}`
• 📸 **Photo:** {'✅ Set' if photo else '❌ None'}
• 🔐 **New 2FA:** `{new_2fa[:3]}***`
• 💰 **Earning:** `${price}`

**⚡ What happens next:**
1. Login to your account
2. Change name to `{name}`
3. Set new profile photo
4. Setup new 2FA password
5. Terminate all sessions
6. Transfer ownership
7. **Pay you ${price} instantly!**

**⚠️ WARNING: After sale, you LOSE ACCESS permanently!**

**Proceed?**
    """
    
    keyboard = [
        [InlineKeyboardButton("✅ YES - SELL NOW", callback_data="confirm_sale")],
        [InlineKeyboardButton("❌ Cancel", callback_data="main_menu")]
    ]
    
    context.user_data['price'] = price
    
    if hasattr(update, 'callback_query') and update.callback_query:
        await update.callback_query.edit_message_text(confirm_text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(confirm_text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    
    return CONFIRM

async def process_sale(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process the sale."""
    await update.callback_query.answer()
    
    phone = context.user_data.get('phone')
    name = context.user_data.get('name')
    price = context.user_data.get('price')
    
    # Show processing
    processing_text = f"""
⚡ **Processing Sale...**

**Current Status:**
✅ Phone verified: `{phone}`
⏳ Logging into account...
⏳ Changing name to `{name}`...
⏳ Setting new profile photo...
⏳ Configuring 2FA...
⏳ Terminating sessions...
⏳ Processing payment...

**Please wait 2-3 minutes...**
    """
    
    await update.callback_query.edit_message_text(processing_text, parse_mode='Markdown')
    
    # Simulate processing
    await asyncio.sleep(3)
    
    # Success message
    success_text = f"""
🎉 **SALE COMPLETED!**

**✅ Account Successfully Sold:**
• 📱 Phone: `{phone}`
• 👤 Name changed to: `{name}`
• 📸 Profile photo updated
• 🔐 New 2FA configured
• 🔄 All sessions terminated
• 📱 Ownership transferred

**💰 Payment: `${price}` added to balance!**

**🎊 Thank you for using our service!**
    """
    
    keyboard = [
        [InlineKeyboardButton("💰 Sell Another", callback_data="start_selling")],
        [InlineKeyboardButton("💳 Check Balance", callback_data="balance")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
    ]
    
    await update.callback_query.edit_message_text(success_text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    
    # Clear user data
    context.user_data.clear()
    return ConversationHandler.END

async def handle_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show balance."""
    balance = round(random.uniform(0, 500), 2)
    balance_text = f"""
💳 **Your Balance**

**Current Balance:** `${balance}`

**Recent Activity:**
• Account sale: +$25.50
• Account sale: +$18.75  
• Withdrawal: -$100.00

**Available Actions:**
    """
    
    keyboard = [
        [InlineKeyboardButton("💸 Withdraw", callback_data="withdraw")],
        [InlineKeyboardButton("📊 History", callback_data="history")],
        [InlineKeyboardButton("← Back", callback_data="main_menu")]
    ]
    
    await update.callback_query.edit_message_text(balance_text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_sales_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show sales history."""
    history_text = """
📊 **Sales History**

**Total Sales:** 12 accounts
**Total Earned:** $387.50

**Recent Sales:**
• +1234567890 - $25.50 - Oct 16
• +9876543210 - $18.75 - Oct 15  
• +5555551234 - $32.00 - Oct 14

**Performance:**
• Success Rate: 100%
• Avg Price: $32.29
    """
    
    keyboard = [
        [InlineKeyboardButton("💰 Sell Another", callback_data="start_selling")],
        [InlineKeyboardButton("← Back", callback_data="main_menu")]
    ]
    
    await update.callback_query.edit_message_text(history_text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

# Button callback handler
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle button callbacks."""
    query = update.callback_query
    await query.answer()
    
    if query.data == "main_menu":
        await start_command(update, context)
    elif query.data == "balance":
        await handle_balance(update, context)
    elif query.data == "sales_history":
        await handle_sales_history(update, context)
    elif query.data in ["withdraw", "history"]:
        await query.edit_message_text("🚧 Feature coming soon!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← Back", callback_data="main_menu")]]))

# Setup conversation handler
def get_selling_handler():
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_selling, pattern='^start_selling$')
        ],
        states={
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_phone)],
            OTP: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_otp)],
            DISABLE_2FA: [CallbackQueryHandler(handle_2fa_disabled, pattern='^2fa_disabled$')],
            NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_name),
                CallbackQueryHandler(handle_name, pattern='^random_name$')
            ],
            PHOTO: [
                MessageHandler(filters.PHOTO, handle_photo),
                CallbackQueryHandler(handle_photo, pattern='^(random_photo|skip_photo)$')
            ],
            NEW_2FA: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_new_2fa),
                CallbackQueryHandler(handle_new_2fa, pattern='^generate_pass$')
            ],
            CONFIRM: [CallbackQueryHandler(process_sale, pattern='^confirm_sale$')]
        },
        fallbacks=[
            CallbackQueryHandler(start_command, pattern='^main_menu$')
        ]
    )