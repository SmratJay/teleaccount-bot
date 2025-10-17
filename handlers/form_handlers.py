"""
Professional Phone Input Form Handlers
Creates inline forms with country code selector and validates input
"""
import logging
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

# Common country codes for easy selection
POPULAR_COUNTRIES = [
    ("🇺🇸 United States", "+1"),
    ("🇮🇳 India", "+91"),
    ("🇬🇧 United Kingdom", "+44"),
    ("🇨🇦 Canada", "+1"),
    ("🇦🇺 Australia", "+61"),
    ("🇩🇪 Germany", "+49"),
    ("🇫🇷 France", "+33"),
    ("🇷🇺 Russia", "+7"),
    ("🇧🇷 Brazil", "+55"),
    ("🇯🇵 Japan", "+81")
]

async def show_phone_input_form(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display professional phone input form with country selector."""
    
    form_html = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Phone Number Input</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }
        
        body {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 400px;
            margin: 0 auto;
            background: white;
            border-radius: 16px;
            padding: 24px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
        }
        
        .header {
            text-align: center;
            margin-bottom: 24px;
        }
        
        .title {
            font-size: 24px;
            font-weight: bold;
            color: #2d3748;
            margin-bottom: 8px;
        }
        
        .subtitle {
            font-size: 14px;
            color: #718096;
        }
        
        .form-group {
            margin-bottom: 20px;
        }
        
        .label {
            display: block;
            font-weight: 600;
            color: #2d3748;
            margin-bottom: 8px;
        }
        
        .country-selector {
            width: 100%;
            padding: 12px 16px;
            border: 2px solid #e2e8f0;
            border-radius: 8px;
            font-size: 16px;
            background: white;
            cursor: pointer;
            margin-bottom: 12px;
        }
        
        .phone-input-container {
            display: flex;
            gap: 8px;
        }
        
        .country-code {
            padding: 12px 16px;
            border: 2px solid #e2e8f0;
            border-radius: 8px;
            background: #f7fafc;
            color: #2d3748;
            font-weight: 600;
            min-width: 80px;
            text-align: center;
        }
        
        .phone-number {
            flex: 1;
            padding: 12px 16px;
            border: 2px solid #e2e8f0;
            border-radius: 8px;
            font-size: 16px;
        }
        
        .phone-number:focus, .country-selector:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        
        .submit-btn {
            width: 100%;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 16px;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s;
        }
        
        .submit-btn:hover {
            transform: translateY(-2px);
        }
        
        .submit-btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }
        
        .warning {
            background: #fed7d7;
            border: 1px solid #feb2b2;
            color: #c53030;
            padding: 12px 16px;
            border-radius: 8px;
            margin-bottom: 20px;
            font-size: 14px;
        }
        
        .info {
            background: #bee3f8;
            border: 1px solid #90cdf4;
            color: #2b6cb0;
            padding: 12px 16px;
            border-radius: 8px;
            margin-bottom: 20px;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="title">📱 Phone Verification</div>
            <div class="subtitle">Enter your Telegram phone number</div>
        </div>
        
        <div class="warning">
            ⚠️ <strong>Real Process:</strong> We will send an actual OTP to your phone via Telegram API
        </div>
        
        <form id="phoneForm">
            <div class="form-group">
                <label class="label">Select Country</label>
                <select class="country-selector" id="countrySelect">
                    <option value="+1">🇺🇸 United States (+1)</option>
                    <option value="+91">🇮🇳 India (+91)</option>
                    <option value="+44">🇬🇧 United Kingdom (+44)</option>
                    <option value="+1">🇨🇦 Canada (+1)</option>
                    <option value="+61">🇦🇺 Australia (+61)</option>
                    <option value="+49">🇩🇪 Germany (+49)</option>
                    <option value="+33">🇫🇷 France (+33)</option>
                    <option value="+7">🇷🇺 Russia (+7)</option>
                    <option value="+55">🇧🇷 Brazil (+55)</option>
                    <option value="+81">🇯🇵 Japan (+81)</option>
                    <option value="">🌍 Other (type manually)</option>
                </select>
            </div>
            
            <div class="form-group">
                <label class="label">Phone Number</label>
                <div class="phone-input-container">
                    <div class="country-code" id="countryCode">+1</div>
                    <input 
                        type="tel" 
                        class="phone-number" 
                        id="phoneNumber" 
                        placeholder="1234567890"
                        maxlength="15"
                        required
                    >
                </div>
            </div>
            
            <div class="info">
                💡 <strong>Format:</strong> Enter only the phone number without country code
            </div>
            
            <button type="submit" class="submit-btn" id="submitBtn">
                📲 Send Verification Code
            </button>
        </form>
    </div>
    
    <script>
        const countrySelect = document.getElementById('countrySelect');
        const countryCode = document.getElementById('countryCode');
        const phoneNumber = document.getElementById('phoneNumber');
        const submitBtn = document.getElementById('submitBtn');
        const form = document.getElementById('phoneForm');
        
        // Update country code display
        countrySelect.addEventListener('change', function() {
            const selectedCode = this.value;
            if (selectedCode === '') {
                countryCode.style.display = 'none';
                phoneNumber.placeholder = '+1234567890 (with country code)';
            } else {
                countryCode.style.display = 'block';
                countryCode.textContent = selectedCode;
                phoneNumber.placeholder = '1234567890';
            }
        });
        
        // Validate phone number input
        phoneNumber.addEventListener('input', function() {
            this.value = this.value.replace(/[^0-9+]/g, '');
            validateForm();
        });
        
        function validateForm() {
            const phone = phoneNumber.value.trim();
            const country = countrySelect.value;
            
            let isValid = false;
            
            if (country === '') {
                // Manual entry - must start with +
                isValid = phone.startsWith('+') && phone.length >= 8;
            } else {
                // Selected country - just need digits
                isValid = phone.length >= 6 && /^[0-9]+$/.test(phone);
            }
            
            submitBtn.disabled = !isValid;
        }
        
        // Handle form submission
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const country = countrySelect.value;
            const phone = phoneNumber.value.trim();
            
            let fullPhone;
            if (country === '') {
                fullPhone = phone;
            } else {
                fullPhone = country + phone;
            }
            
            // Validate final phone number
            if (!fullPhone.startsWith('+') || fullPhone.length < 8) {
                alert('Please enter a valid phone number');
                return;
            }
            
            // Send data back to Telegram bot
            if (window.Telegram && window.Telegram.WebApp) {
                window.Telegram.WebApp.sendData(JSON.stringify({
                    action: 'phone_submitted',
                    phone: fullPhone,
                    country_code: country || 'manual'
                }));
                window.Telegram.WebApp.close();
            } else {
                alert('Phone: ' + fullPhone);
            }
        });
        
        // Initialize Telegram WebApp
        if (window.Telegram && window.Telegram.WebApp) {
            window.Telegram.WebApp.ready();
            window.Telegram.WebApp.expand();
        }
        
        // Initial validation
        validateForm();
    </script>
</body>
</html>
    """
    
    # For now, let's use inline keyboard since WebApp requires hosting
    # I'll create a professional inline keyboard form instead
    
    text = """
📱 **Professional Phone Input**

**Step 1:** Select your country code below
**Step 2:** Enter your phone number
**Step 3:** We'll send real OTP via Telegram API

**⚠️ This is REAL - not a simulation!**

Choose your country:
    """
    
    # Create country selection buttons (2 per row)
    keyboard = []
    for i in range(0, len(POPULAR_COUNTRIES), 2):
        row = []
        for j in range(2):
            if i + j < len(POPULAR_COUNTRIES):
                country, code = POPULAR_COUNTRIES[i + j]
                row.append(InlineKeyboardButton(
                    f"{country} {code}", 
                    callback_data=f"country_{code}"
                ))
        keyboard.append(row)
    
    # Add manual entry and back buttons
    keyboard.extend([
        [InlineKeyboardButton("🌍 Other Country (Manual)", callback_data="country_manual")],
        [InlineKeyboardButton("❌ Cancel", callback_data="main_menu")]
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)
    else:
        await update.message.reply_text(text, parse_mode='Markdown', reply_markup=reply_markup)

async def handle_country_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle country code selection."""
    query = update.callback_query
    await query.answer()
    
    country_code = query.data.replace("country_", "")
    
    if country_code == "manual":
        text = """
📱 **Manual Phone Entry**

Please enter your **complete phone number** including country code:

**Format:** +1234567890
**Example:** +919876543210

**What happens next:**
1. Real OTP sent via Telegram API ✅
2. You receive actual code on your phone ✅
3. Account verification and login ✅

Enter your phone number:
        """
        context.user_data['country_code'] = 'manual'
    else:
        # Find country name for the code
        country_name = "Selected Country"
        for name, code in POPULAR_COUNTRIES:
            if code == country_code:
                country_name = name.split(' ', 1)[1] if ' ' in name else name
                break
        
        text = f"""
📱 **Phone Number Input**

**Country:** {country_name}
**Country Code:** `{country_code}`

Now enter **only your phone number** (without country code):

**Example:** 9876543210
**Full number will be:** `{country_code}9876543210`

**What happens next:**
1. Real OTP sent via Telegram API ✅
2. You receive actual code on your phone ✅
3. Account verification and login ✅

Enter your phone number:
        """
        context.user_data['country_code'] = country_code
    
    keyboard = [
        [InlineKeyboardButton("🔙 Change Country", callback_data="start_real_selling")],
        [InlineKeyboardButton("❌ Cancel", callback_data="main_menu")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)
    
    return 1  # PHONE state

async def handle_phone_number_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle phone number input after country selection."""
    phone_input = update.message.text.strip()
    country_code = context.user_data.get('country_code')
    
    # Validate and format phone number
    if country_code == 'manual':
        # Manual entry - should include country code
        if not phone_input.startswith('+'):
            await update.message.reply_text(
                "❌ **Invalid format!**\n\nPlease include country code: `+1234567890`",
                parse_mode='Markdown'
            )
            return 1  # Stay in same state
        full_phone = phone_input
    else:
        # Selected country - just add country code
        if not phone_input.isdigit():
            await update.message.reply_text(
                f"❌ **Invalid format!**\n\nPlease enter only digits: `1234567890`\n\nCountry code `{country_code}` will be added automatically.",
                parse_mode='Markdown'
            )
            return 1  # Stay in same state
        full_phone = country_code + phone_input
    
    # Final validation
    if len(full_phone) < 8 or len(full_phone) > 16:
        await update.message.reply_text(
            "❌ **Invalid phone length!**\n\nPhone number should be 8-15 digits.",
            parse_mode='Markdown'
        )
        return 1  # Stay in same state
    
    # Store phone and show confirmation
    context.user_data['phone'] = full_phone
    
    confirmation_text = f"""
✅ **Phone Number Confirmation**

**Complete Number:** `{full_phone}`
**Country Code:** `{country_code if country_code != 'manual' else 'Manual entry'}`

**⚠️ READY TO SEND REAL OTP!**

This will:
• Send **actual verification code** via Telegram API
• You'll receive **real SMS/code** on your phone
• Begin **actual account verification** process

Proceed with sending OTP?
    """
    
    keyboard = [
        [InlineKeyboardButton("📲 Send Real OTP", callback_data="confirm_send_otp")],
        [InlineKeyboardButton("✏️ Edit Number", callback_data="start_real_selling")],
        [InlineKeyboardButton("❌ Cancel", callback_data="main_menu")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(confirmation_text, parse_mode='Markdown', reply_markup=reply_markup)
    
    return 2  # Move to confirmation state