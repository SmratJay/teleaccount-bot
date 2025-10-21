# 🚂 Railway Deployment Guide

Complete step-by-step guide to deploy your Telegram bot on Railway.app for **$5-10/month**.

## 📋 Prerequisites

- ✅ GitHub account
- ✅ Railway account ([sign up here](https://railway.app))
- ✅ Your bot's secrets (API keys, tokens)

## 🎯 Quick Start (10 minutes)

**Cost:** $5/month free credits, then ~$5-10/month

---

## Step 1: Push to GitHub

```bash
# In your Replit terminal:
git init
git add .
git commit -m "Ready for Railway"

# Replace with your GitHub username and repo name:
git remote add origin https://github.com/YOUR_USERNAME/telegram-bot.git
git push -u origin main
```

---

## Step 2: Deploy on Railway

1. Go to **railway.app** → Login with GitHub
2. Click **"New Project"** → **"Deploy from GitHub repo"**
3. Select your repository
4. Railway auto-detects Python!

---

## Step 3: Add PostgreSQL

1. In Railway dashboard: **"+ New"** → **"Database"** → **"PostgreSQL"**
2. Done! `DATABASE_URL` is set automatically

---

## Step 4: Add Environment Variables

In Railway → Your bot service → **"Variables"** tab:

| Variable | Get From |
|----------|----------|
| `TELEGRAM_BOT_TOKEN` | @BotFather |
| `API_ID` | my.telegram.org |
| `API_HASH` | my.telegram.org |
| `ADMIN_TELEGRAM_ID` | Your Telegram ID |
| `SECRET_KEY` | `python -c "import secrets; print(secrets.token_urlsafe(32))"` |

---

## Step 5: Deploy & Test

1. Railway → **"Deployments"** tab → Watch it deploy (2-3 min)
2. Check **"Logs"** tab for: `✅ Bot Started!`
3. Open Telegram → `/start` your bot 🎉

---

## 🔄 Making Updates

```bash
git add .
git commit -m "Your changes"
git push
```

Railway auto-deploys in 2-3 minutes!

---

## 💰 Pricing

- **Free:** $5/month credits
- **After:** ~$5-10/month for 24/7 operation
- Monitor usage in Railway **"Usage"** tab

---

## ⚠️ Troubleshooting

**Bot not starting?**
- Check Railway → "Logs" tab
- Verify all environment variables are set

**Database errors?**
- Make sure PostgreSQL database was added
- `DATABASE_URL` is automatic - don't add manually

**Need to restart?**
- Railway → "Deployments" → Three dots → "Redeploy"

---

## 🎉 Done!

Your bot is now:
- ✅ Running 24/7
- ✅ Auto-deploys from GitHub
- ✅ Connected to PostgreSQL
- ✅ Only $5-10/month

**Next steps:**
1. Test all features
2. Monitor Railway usage
3. Keep your repo private for security

---

**Questions?** Railway Discord: [discord.gg/railway](https://discord.gg/railway)
