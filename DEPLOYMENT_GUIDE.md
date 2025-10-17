# 🚀 Deploy Your Telegram Account Bot - 24/7 Live Hosting

This guide will help you deploy your Telegram Account Selling Bot to run 24/7 on free cloud platforms.

## 📋 Prerequisites

Before deploying, make sure you have:
- ✅ A GitHub account
- ✅ Your bot token from @BotFather
- ✅ Telegram API credentials (API_ID, API_HASH) from my.telegram.org
- ✅ Your Telegram user ID and leader channel ID

## 🎯 Recommended Free Hosting Options

### 1. 🔥 **Replit (Recommended - Easiest)**

**Pros:** ✅ Free forever, ✅ Easy setup, ✅ Built-in database
**Cons:** ⚠️ May sleep after inactivity (can be kept alive)

**Steps:**
1. **Create GitHub Repository:**
   - Go to GitHub.com and create a new repository
   - Upload all your bot files to the repository

2. **Import to Replit:**
   - Go to [replit.com](https://replit.com)
   - Click "Create Repl" → "Import from GitHub"
   - Enter your repository URL
   - Replit will automatically detect it's a Python project

3. **Set Environment Variables:**
   - In Replit, go to "Secrets" tab (🔒 icon)
   - Add these environment variables:
   ```
   BOT_TOKEN=8483671369:AAEOTZCDpCPiarfZHdb1Z5CFAZoMvdtmeKs
   API_ID=21734417
   API_HASH=d64eb98d90eb41b8ba3644e3722a3714
   ADMIN_CHAT_ID=6733908384
   ADMIN_USER_ID=6733908384
   LEADER_CHANNEL_ID=-4859227833
   SECRET_KEY=super_secret_key_for_your_bot_12345
   DEBUG=False
   ENVIRONMENT=production
   ```

4. **Run Your Bot:**
   - Click the "Run" button
   - Your bot will start automatically!

5. **Keep Alive (Optional):**
   - Use UptimeRobot.com to ping your Repl every 5 minutes
   - This prevents it from sleeping

### 2. 🟣 **Heroku (Free Tier)**

**Pros:** ✅ Professional hosting, ✅ Good uptime
**Cons:** ⚠️ Limited free hours per month

**Steps:**
1. **Create Heroku Account:**
   - Go to [heroku.com](https://heroku.com) and sign up

2. **Deploy via GitHub:**
   - Push your code to a GitHub repository
   - In Heroku dashboard, create new app
   - Connect your GitHub repository
   - Enable automatic deploys

3. **Set Config Variables:**
   - In Heroku app settings → "Config Vars"
   - Add all the environment variables listed above

4. **Deploy:**
   - Heroku will automatically build and deploy your bot

## 📁 Repository Structure

Your GitHub repository should look like this:
```
teleaccount_bot/
├── .replit                 # Replit configuration
├── replit.nix             # Replit dependencies
├── Procfile               # Heroku process file
├── runtime.txt            # Python version
├── requirements.txt       # Python dependencies
├── app.json              # Heroku app configuration
├── real_main.py          # Main bot file
├── database/             # Database models and operations
├── handlers/             # Bot handlers
├── services/             # Bot services
├── utils/                # Utility functions
├── webapp/               # Web interface
└── README.md             # Documentation
```

## 🔧 Environment Variables Required

| Variable | Description | Example |
|----------|-------------|---------|
| `BOT_TOKEN` | Bot token from @BotFather | `123456:ABC-DEF1234...` |
| `API_ID` | Telegram API ID | `21734417` |
| `API_HASH` | Telegram API Hash | `d64eb98d90eb41b8ba...` |
| `ADMIN_CHAT_ID` | Your Telegram user ID | `6733908384` |
| `ADMIN_USER_ID` | Your Telegram user ID | `6733908384` |
| `LEADER_CHANNEL_ID` | Leader notification channel | `-4859227833` |
| `SECRET_KEY` | Random secret key | `your_secret_key_123` |
| `DEBUG` | Debug mode | `False` |
| `ENVIRONMENT` | Environment type | `production` |

## 🚀 Quick Deploy Buttons

### Deploy to Replit:
1. Fork this repository to your GitHub
2. Go to replit.com → Import from GitHub
3. Add environment variables in Secrets tab
4. Click Run!

### Deploy to Heroku:
[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy)

## 🎯 Post-Deployment Checklist

After deployment, verify:
- ✅ Bot responds to /start command
- ✅ Withdrawal notifications work in your channel
- ✅ Database operations work correctly
- ✅ WebApp interface loads (if using)
- ✅ Leader panel is accessible

## 🔄 Keeping Your Bot Alive

### For Replit:
1. **UptimeRobot Method:**
   - Sign up at uptimerobot.com
   - Add your Repl URL as HTTP monitor
   - Set check interval to 5 minutes

2. **Always-On (Paid):**
   - Upgrade to Replit Core ($7/month)
   - Enable "Always On" feature

### For Heroku:
- Free tier gives 550-1000 hours/month
- Add credit card for additional hours
- Use Heroku Scheduler for periodic tasks

## 🆘 Troubleshooting

**Bot not responding:**
- Check logs in platform dashboard
- Verify all environment variables are set
- Ensure bot token is correct

**Database errors:**
- Check if SQLite file is being created
- Verify database permissions
- Check database initialization

**Withdrawal notifications not working:**
- Verify LEADER_CHANNEL_ID is correct
- Ensure bot is admin in the channel
- Check bot permissions in the group

## 📞 Support

If you need help:
1. Check the logs in your hosting platform
2. Verify all environment variables
3. Test bot locally first
4. Contact support through the bot's contact feature

---

**🎉 Your bot will now run 24/7 and handle real Telegram account sales with professional withdrawal system!**