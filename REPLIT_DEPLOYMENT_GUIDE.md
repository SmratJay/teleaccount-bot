# 🚀 Complete Replit Deployment Guide for Telegram Account Bot

## 📋 **Prerequisites**
- Replit account (free tier works)
- Telegram Bot Token from @BotFather
- Telegram API credentials (API_ID, API_HASH) from my.telegram.org
- Database URL (we'll use Replit's built-in database)

## 🎯 **Step 1: Create New Replit Project**

1. Go to [replit.com](https://replit.com)
2. Click "Create Repl"
3. Choose "Python" template
4. Name your repl: `telegram-account-bot`
5. Click "Create Repl"

## 📁 **Step 2: Upload Project Files**

Upload ALL these files to your Replit project:

### Core Files (Required):
```
├── main.py                    # Entry point for Replit
├── real_main.py              # Main bot application
├── requirements.txt          # Python dependencies
├── replit.nix               # Replit configuration
├── pyproject.toml           # Python project config
├── .replit                  # Replit run configuration
├── database/
│   ├── __init__.py
│   ├── connection.py
│   ├── models.py
│   └── services.py
├── handlers/
│   ├── __init__.py
│   ├── real_handlers.py
│   ├── main_handlers.py
│   ├── admin_handlers.py
│   ├── leader_handlers.py
│   └── analytics_handlers.py
├── services/
│   ├── __init__.py
│   ├── real_telegram.py
│   ├── telethon_manager.py
│   └── security_bypass.py
├── webapp/
│   ├── __init__.py
│   └── server.py
└── utils/
    ├── __init__.py
    ├── logging_config.py
    └── helpers.py
```

## ⚙️ **Step 3: Configure Replit Environment**

### 3.1 Set Environment Variables (Secrets)
In your Replit project:
1. Click the "Secrets" tab (lock icon) in the left sidebar
2. Add these environment variables ONE BY ONE:

#### 🔑 **Essential Secrets (REQUIRED)**:
```bash
BOT_TOKEN=8483671369:AAEOTZCDpCPiarfZHdb1Z5CFAZoMvdtmeKs
API_ID=21734417
API_HASH=your_api_hash_from_my_telegram_org
TELEGRAM_API_ID=21734417
TELEGRAM_API_HASH=your_api_hash_from_my_telegram_org
ADMIN_TELEGRAM_ID=6733908384
LEADER_TELEGRAM_ID=6733908384
```

#### 🛡️ **Security Secrets (REQUIRED)**:
```bash
SECRET_KEY=generate_random_32_char_string_here
WEBHOOK_SECRET=generate_random_string_for_webhook
SESSION_SECRET=generate_random_string_for_sessions
```

#### 🗄️ **Database & App Secrets (REQUIRED)**:
```bash
DATABASE_URL=sqlite:///./teleaccount_bot.db
DB_TYPE=sqlite
ENVIRONMENT=production
DEBUG=False
HOST=0.0.0.0
PORT=8080
```

### 3.2 How to Get API Credentials

#### Get API_ID and API_HASH:
1. Go to [my.telegram.org](https://my.telegram.org)
2. Login with your phone number
3. Go to "API development tools"
4. Create a new application:
   - App title: "Telegram Account Bot"
   - Short name: "accountbot"
   - Platform: "Desktop"
5. Copy `API_ID` and `API_HASH`

## 📦 **Step 4: File Structure & Upload**

### 4.1 Upload These Key Files:

1. **main.py** (Replit entry point) - ✅ Already created
2. **requirements.txt** - ✅ Already created  
3. **pyproject.toml** - ✅ Already created
4. **.replit** - ✅ Already created
5. **replit.nix** - ✅ Already created

### 4.2 Upload Your Project Files:
Copy ALL files from your local `teleaccount_bot` folder to Replit:

1. In Replit, click "Upload file" or drag & drop
2. Upload ALL Python files from your project
3. Maintain the directory structure exactly

## 🚀 **Step 5: Run the Bot**

### 5.1 Install Dependencies:
In the Replit Shell tab, run:
```bash
pip install -r requirements.txt
```

### 5.2 Start the Bot:
Click the green "Run" button or use:
```bash
python main.py
```

## 📊 **Step 6: Keep Bot Running (Always On)**

### 6.1 Enable Always On (Paid Feature):
1. Go to your Repl settings
2. Enable "Always On" (requires Replit Core subscription)

### 6.2 Alternative - Free Uptime:
Create `keep_alive.py`:
```python
from flask import Flask
from threading import Thread
import time

app = Flask('')

@app.route('/')
def home():
    return "Telegram Bot is running!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()

# Use an external service like UptimeRobot to ping your repl URL every 5 minutes
```

Add to your `main.py`:
```python
from keep_alive import keep_alive
keep_alive()  # Add this before starting the bot
```

## 🔧 **Step 7: Database Setup**

### 7.1 Database Initialization:
The bot will automatically create SQLite database on first run.

### 7.2 Set Your Admin Privileges:
Create `setup_admin.py` in Replit:
```python
import os
import sys
sys.path.append('.')

from database import get_db_session, close_db_session
from database.models import User, UserStatus

def setup_admin():
    user_id = 6733908384  # Your Telegram user ID
    
    db = get_db_session()
    try:
        user = db.query(User).filter(User.telegram_user_id == user_id).first()
        
        if not user:
            user = User(
                telegram_user_id=user_id,
                username="popexenon",
                first_name="Admin",
                is_admin=True,
                is_leader=True,
                status=UserStatus.ACTIVE,
                verification_completed=True,
                captcha_completed=True,
                channels_joined=True
            )
            db.add(user)
        else:
            user.is_admin = True
            user.is_leader = True
            user.status = UserStatus.ACTIVE
            
        db.commit()
        print("✅ Admin privileges set!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        close_db_session(db)

if __name__ == "__main__":
    setup_admin()
```

Run it once:
```bash
python setup_admin.py
```

## 🛠️ **Step 8: Testing & Verification**

### 8.1 Check Bot Status:
1. Send `/start` to your bot
2. Verify admin panel appears
3. Test OTP mechanism with a phone number
4. Test withdrawal request

### 8.2 Monitor Logs:
Watch the Replit console for any errors or issues.

## 🔍 **Step 9: Troubleshooting**

### Common Issues & Solutions:

#### ❌ **"Module not found" errors:**
```bash
pip install --upgrade -r requirements.txt
```

#### ❌ **Database errors:**
```bash
rm teleaccount_bot.db
python setup_admin.py
```

#### ❌ **Bot not responding:**
- Check BOT_TOKEN is correct
- Verify all required secrets are set
- Check Replit console for errors

#### ❌ **OTP not working:**
- Verify API_ID and API_HASH are correct
- Check phone number format (+country_code_number)
- Ensure Telethon dependencies are installed

#### ❌ **Admin panel not showing:**
- Run setup_admin.py
- Check ADMIN_TELEGRAM_ID matches your user ID
- Restart the bot

## ✅ **Step 10: Final Verification Checklist**

- [ ] All environment variables set in Secrets
- [ ] Bot responds to /start command
- [ ] Admin panel buttons visible
- [ ] OTP mechanism accepts phone numbers
- [ ] Withdrawal system shows options
- [ ] Bot stays online (Always On or keep_alive)
- [ ] Database stores user data correctly
- [ ] No errors in console logs

## 🎉 **Deployment Complete!**

Your Telegram account bot is now fully deployed on Replit with:
- ✅ Real OTP integration via Telethon
- ✅ Complete withdrawal system
- ✅ Admin and leader panels
- ✅ SQLite database with full functionality
- ✅ Professional hosting on Replit

**Bot URL**: Your Replit will provide a URL like `https://telegram-account-bot.yourusername.repl.co`

**Support**: If you encounter issues, check the console logs and verify all environment variables are correctly set.

---

## 📚 **Additional Resources**

### Replit Documentation:
- [Replit Python Guide](https://docs.replit.com/programming-ide/using-replit/languages/python)
- [Environment Variables](https://docs.replit.com/programming-ide/workspace-features/secrets-and-environment-variables)

### Telegram Bot API:
- [Bot API Documentation](https://core.telegram.org/bots/api)
- [Telethon Documentation](https://docs.telethon.dev/)

**Congratulations! Your bot is now live and fully functional on Replit! 🚀**