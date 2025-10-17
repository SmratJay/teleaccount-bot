# 🔐 Environment Variables for Cloud Deployment

This file contains all the environment variables you need to set up on your hosting platform.

## 📋 Required Variables

### 🤖 Telegram Bot Configuration
```
BOT_TOKEN=8483671369:AAEOTZCDpCPiarfZHdb1Z5CFAZoMvdtmeKs
API_ID=21734417
API_HASH=d64eb98d90eb41b8ba3644e3722a3714
```

### 👑 Admin & Leader Configuration
```
ADMIN_CHAT_ID=6733908384
ADMIN_USER_ID=6733908384
LEADER_CHANNEL_ID=-4859227833
```

### 🔒 Security
```
SECRET_KEY=super_secret_key_for_your_bot_12345
```

### 🏭 Production Settings
```
DEBUG=False
ENVIRONMENT=production
```

## 🎯 How to Set These Up

### In Replit:
1. Click the 🔒 "Secrets" tab in your Repl
2. Add each variable as Key = Value
3. Example: Key: `BOT_TOKEN`, Value: `8483671369:AAE...`

### In Heroku:
1. Go to your app's "Settings" tab
2. Click "Reveal Config Vars"
3. Add each variable as Key = Value

### In Railway:
1. Go to your project settings
2. Click "Environment" tab
3. Add each variable

## ⚠️ Important Notes

- **Never commit .env files to GitHub!** (They're in .gitignore)
- **Keep your bot token secret** - never share it publicly
- **Use your actual values** - the ones shown here are examples
- **Test locally first** before deploying to production

## 🔄 Getting Your Values

| Variable | How to Get |
|----------|------------|
| `BOT_TOKEN` | Message @BotFather on Telegram |
| `API_ID` & `API_HASH` | Visit my.telegram.org |
| `ADMIN_CHAT_ID` | Your Telegram user ID |
| `LEADER_CHANNEL_ID` | Run get_channel_id.py script |
| `SECRET_KEY` | Generate random string (keep secret!) |