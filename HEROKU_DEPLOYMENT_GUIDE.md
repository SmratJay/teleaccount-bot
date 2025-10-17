# 🚀 HEROKU DEPLOYMENT GUIDE - TELEACCOUNT BOT

## Quick Start (5 minutes to deploy!)

### Prerequisites
1. **Heroku Account**: Sign up at [heroku.com](https://heroku.com)
2. **Heroku CLI**: Download from [Heroku CLI](https://devcenter.heroku.com/articles/heroku-cli)
3. **Git**: Ensure git is installed
4. **Your Bot Tokens**: Get from @BotFather and my.telegram.org

### 🔥 SUPER QUICK DEPLOYMENT

**Option 1: Automatic Script (Recommended)**
```bash
# Windows PowerShell
.\deploy_heroku.ps1

# Linux/Mac
chmod +x deploy_heroku.sh
./deploy_heroku.sh
```

**Option 2: Manual Commands**
```bash
# 1. Login to Heroku
heroku login

# 2. Create app (replace 'your-app-name' with unique name)
heroku create your-app-name

# 3. Add PostgreSQL database
heroku addons:create heroku-postgresql:essential-0 --app your-app-name

# 4. Set environment variables (UPDATE THESE!)
heroku config:set BOT_TOKEN='your_bot_token_here' --app your-app-name
heroku config:set API_ID='your_api_id' --app your-app-name
heroku config:set API_HASH='your_api_hash' --app your-app-name
heroku config:set TELEGRAM_API_ID='your_api_id' --app your-app-name
heroku config:set TELEGRAM_API_HASH='your_api_hash' --app your-app-name
heroku config:set ADMIN_CHAT_ID='your_telegram_user_id' --app your-app-name
heroku config:set ADMIN_USER_ID='your_telegram_user_id' --app your-app-name
heroku config:set LEADER_CHANNEL_ID='your_channel_id' --app your-app-name

# 5. Set production config
heroku config:set DB_USER='postgres' --app your-app-name
heroku config:set DEBUG='False' --app your-app-name
heroku config:set ENVIRONMENT='production' --app your-app-name

# 6. Deploy
git init
git add .
git commit -m "Deploy to Heroku"
git push heroku main
```

### 🔧 REQUIRED ENVIRONMENT VARIABLES

**Critical Variables (Must Set):**
- `BOT_TOKEN`: Get from @BotFather
- `API_ID`: Get from my.telegram.org
- `API_HASH`: Get from my.telegram.org
- `TELEGRAM_API_ID`: Same as API_ID
- `TELEGRAM_API_HASH`: Same as API_HASH
- `ADMIN_CHAT_ID`: Your Telegram user ID
- `ADMIN_USER_ID`: Your Telegram user ID
- `LEADER_CHANNEL_ID`: Your channel ID for notifications

**Auto-Set Variables:**
- `DATABASE_URL`: Automatically set by PostgreSQL addon
- `SECRET_KEY`: Auto-generated
- `ENCRYPTION_KEY`: Auto-generated

### 🎯 Getting Your Tokens

**1. Bot Token (@BotFather)**
1. Message @BotFather on Telegram
2. Send `/newbot`
3. Follow instructions
4. Copy the token (format: `123456789:ABCdefGHI...`)

**2. API Credentials (my.telegram.org)**
1. Visit [my.telegram.org](https://my.telegram.org)
2. Login with your phone number
3. Go to "API development tools"
4. Create an app
5. Copy `API ID` and `API Hash`

**3. Your User ID**
1. Message @userinfobot on Telegram
2. It will show your user ID
3. Use this for `ADMIN_CHAT_ID` and `ADMIN_USER_ID`

**4. Channel ID (Optional)**
1. Add @RawDataBot to your channel
2. Send any message
3. Look for `"chat":{"id":-1001234567890}`
4. Use the ID for `LEADER_CHANNEL_ID`

### 🚀 One-Click Deploy Button

[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy?template=https://github.com/yourusername/teleaccount_bot)

*Note: Update the repository URL in app.json*

### 📋 Post-Deployment Checklist

✅ App created and deployed  
✅ PostgreSQL addon added  
✅ All environment variables set  
✅ Bot token configured  
✅ API credentials configured  
✅ Admin user ID set  
✅ Database tables created automatically  

### 🔍 Monitoring & Troubleshooting

**Check Status:**
```bash
heroku ps --app your-app-name
heroku logs --tail --app your-app-name
```

**Restart App:**
```bash
heroku restart --app your-app-name
```

**Database Console:**
```bash
heroku pg:psql --app your-app-name
```

**Config Variables:**
```bash
heroku config --app your-app-name
```

### 🛠️ Common Issues & Solutions

**Issue: "Application Error"**
- Check logs: `heroku logs --tail --app your-app-name`
- Ensure all required env vars are set
- Verify bot token is correct

**Issue: "Database connection failed"**
- PostgreSQL addon should auto-configure
- Check if `DATABASE_URL` is set in config vars

**Issue: "Bot not responding"**
- Verify bot token with @BotFather
- Check if webhook conflicts exist
- Restart the app

### 💰 Heroku Costs

**Free Tier (Eco Dynos):**
- Up to 1000 dyno hours/month
- Sleeps after 30 mins of inactivity
- Perfect for testing

**Paid Tier (Basic - $7/month):**
- Always-on (no sleeping)
- Recommended for production

**Database:**
- PostgreSQL Essential-0: $5/month
- 10,000 rows, 20 connections

### 🎉 Success!

Your bot is now live on Heroku! 

**URLs:**
- Bot: `https://your-app-name.herokuapp.com`
- Dashboard: `https://dashboard.heroku.com/apps/your-app-name`
- Logs: `https://dashboard.heroku.com/apps/your-app-name/logs`

The bot will automatically:
- Handle user verification with CAPTCHAs
- Process account selling requests
- Manage withdrawals and payments
- Store data in PostgreSQL database
- Send admin notifications

**Next Steps:**
1. Test the bot by messaging it on Telegram
2. Set up your admin panel
3. Configure withdrawal settings
4. Add your Telegram channels for verification

🎊 **Your professional Telegram bot is now live and ready for business!**