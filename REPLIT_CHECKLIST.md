# 📋 Replit Deployment Checklist

## 🎯 **Before You Start**
- [ ] Replit account created
- [ ] Telegram bot token from @BotFather  
- [ ] API_ID and API_HASH from my.telegram.org
- [ ] Your Telegram user ID (6733908384)

## 📁 **Step 1: Project Setup**
- [ ] Create new Python Repl named "telegram-account-bot"
- [ ] Upload ALL project files maintaining directory structure
- [ ] Verify all core files are present:
  - [ ] main.py
  - [ ] real_main.py
  - [ ] requirements.txt
  - [ ] pyproject.toml
  - [ ] .replit
  - [ ] replit.nix
  - [ ] keep_alive.py
  - [ ] setup_admin.py
  - [ ] verify_deployment.py

## 🔐 **Step 2: Environment Variables (Secrets Tab)**

### Essential Secrets:
- [ ] `BOT_TOKEN` = `8483671369:AAEOTZCDpCPiarfZHdb1Z5CFAZoMvdtmeKs`
- [ ] `API_ID` = `21734417`
- [ ] `API_HASH` = `[your_hash_from_my.telegram.org]`
- [ ] `TELEGRAM_API_ID` = `21734417`
- [ ] `TELEGRAM_API_HASH` = `[same_as_API_HASH]`
- [ ] `ADMIN_TELEGRAM_ID` = `6733908384`
- [ ] `LEADER_TELEGRAM_ID` = `6733908384`

### Security Secrets:
- [ ] `SECRET_KEY` = `[32_char_random_string]`
- [ ] `WEBHOOK_SECRET` = `[random_string]`
- [ ] `SESSION_SECRET` = `[random_string]`

### App Secrets:
- [ ] `DATABASE_URL` = `sqlite:///./teleaccount_bot.db`
- [ ] `DB_TYPE` = `sqlite`
- [ ] `ENVIRONMENT` = `production`
- [ ] `DEBUG` = `False`
- [ ] `HOST` = `0.0.0.0`
- [ ] `PORT` = `8080`

## 🧪 **Step 3: Pre-Deployment Testing**
- [ ] Run verification: `python verify_deployment.py`
- [ ] Check all dependencies: `pip install -r requirements.txt`
- [ ] Setup admin privileges: `python setup_admin.py`

## 🚀 **Step 4: Deployment**
- [ ] Click "Run" button or run `python main.py`
- [ ] Check console for startup messages
- [ ] Verify "Application started" message appears
- [ ] No error messages in console

## ✅ **Step 5: Bot Testing**
- [ ] Send `/start` to your bot on Telegram
- [ ] Admin panel buttons are visible
- [ ] Test OTP mechanism with phone number
- [ ] Test withdrawal system options
- [ ] All features respond correctly

## 🔄 **Step 6: Keep-Alive Setup**

### Option A: Replit Core (Paid)
- [ ] Subscribe to Replit Core
- [ ] Enable "Always On" in settings

### Option B: Free Monitoring
- [ ] Get your Replit URL: `https://telegram-account-bot.yourusername.repl.co`
- [ ] Sign up for UptimeRobot (free)
- [ ] Create HTTP monitor with 5-minute intervals
- [ ] Monitor will ping your bot to keep it alive

## 🎉 **Step 7: Final Verification**
- [ ] Bot responds within 5 seconds
- [ ] All admin features accessible
- [ ] OTP system accepts phone numbers
- [ ] Withdrawal requests process correctly
- [ ] Database stores user data
- [ ] Keep-alive URL shows "Bot is Running"

## 🛠️ **Troubleshooting Checklist**

### Bot Not Starting:
- [ ] Check BOT_TOKEN is correct
- [ ] Verify all required secrets are set
- [ ] Check console for import errors
- [ ] Run `pip install -r requirements.txt`

### Admin Panel Missing:
- [ ] Verify ADMIN_TELEGRAM_ID = 6733908384
- [ ] Run `python setup_admin.py` again
- [ ] Restart bot with `python main.py`

### OTP Not Working:
- [ ] Check API_ID and API_HASH are from my.telegram.org
- [ ] Verify phone number format: +countrycode_number
- [ ] Check Telethon is installed: `pip install telethon`

### Database Errors:
- [ ] Delete old database: `rm teleaccount_bot.db`
- [ ] Run setup again: `python setup_admin.py`
- [ ] Restart bot

### Connection Issues:
- [ ] Check Replit console for errors
- [ ] Verify all environment variables set
- [ ] Try restarting the Repl

## 📞 **Support Commands**

```bash
# Check environment
python verify_deployment.py

# Setup admin
python setup_admin.py

# Install dependencies
pip install -r requirements.txt

# Start bot
python main.py

# Check status
curl https://your-repl-url.repl.co/status
```

## ✨ **Success Indicators**
- ✅ Console shows "Application started"
- ✅ Bot responds to /start immediately
- ✅ Admin buttons visible and working
- ✅ OTP accepts phone numbers
- ✅ Withdrawal system shows options
- ✅ Keep-alive URL accessible
- ✅ No errors in console

**Once all checkboxes are completed, your bot is fully deployed and operational on Replit! 🚀**