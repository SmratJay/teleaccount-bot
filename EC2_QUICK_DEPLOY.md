# Quick EC2 Deployment Guide

## What's New in This Update

✅ **7-Day CAPTCHA Cache** - Returning users skip verification for 7 days  
✅ **Faster CAPTCHA** - Smaller images (200x70), fewer characters (4 instead of 5)  
✅ **Fixed Main Menu Bug** - "Continue to Main Menu" button now works  
✅ **Database Migrations** - Alembic setup for future schema changes  

---

## Deploy to EC2 (3 Simple Steps)

### Option A: Automated Script (Recommended)

```bash
# 1. SSH to EC2
ssh -i your-key.pem ubuntu@13.53.80.228

# 2. Navigate to project
cd ~/teleaccount-bot

# 3. Pull latest code
git pull origin main

# 4. Run deployment script
chmod +x DEPLOY_TO_EC2.sh
./DEPLOY_TO_EC2.sh
```

Done! The script handles everything automatically.

---

### Option B: Manual Commands

If you prefer to run commands one by one:

```bash
# SSH to EC2
ssh -i your-key.pem ubuntu@13.53.80.228

# Navigate to project
cd ~/teleaccount-bot

# Pull latest code
git pull origin main

# Set DATABASE_URL
export DATABASE_URL="postgresql://neondb_owner:npg_oiTEI2qfeW8j@ep-silent-glade-ae6wc05t.c-2.us-east-2.aws.neon.tech/neondb?sslmode=require"

# Add database column
psql $DATABASE_URL -c "ALTER TABLE users ADD COLUMN IF NOT EXISTS captcha_verified_at TIMESTAMP;"

# Restart bot
sudo systemctl restart telebot

# Check status
sudo systemctl status telebot
```

---

## Verify Deployment

### 1. Check Logs
```bash
sudo journalctl -u telebot -f
```

Look for:
- ✅ No Markdown parsing errors
- ✅ Logs showing "CAPTCHA cache hit" or "CAPTCHA verified, cached for 7 days"

### 2. Test the Bot

**First-time user experience:**
1. Send `/start`
2. See CAPTCHA image
3. Enter the 4 characters
4. Click "Continue to Channels"
5. Click "Continue to Main Menu" ← **Should work now!**
6. See main menu with balance

**Returning user experience:**
1. Send `/start` again
2. **Skip CAPTCHA entirely** ← Main menu appears instantly!
3. This works for 7 days after verification

**After 7 days:**
1. Send `/start`
2. CAPTCHA appears again (expired)
3. Verify and get another 7-day pass

---

## Troubleshooting

### Main Menu Still Broken?
```bash
# Check for Markdown errors in logs
sudo journalctl -u telebot | grep "parse entities"

# If you see errors, check the code was pulled
cd ~/teleaccount-bot
git log -1
```

### CAPTCHA Cache Not Working?
```bash
# Verify column exists
psql $DATABASE_URL -c "\d users" | grep captcha_verified_at

# Should show:
# captcha_verified_at | timestamp without time zone |
```

### Bot Won't Start?
```bash
# Check service status
sudo systemctl status telebot

# View detailed logs
sudo journalctl -u telebot -n 50

# Restart manually
sudo systemctl restart telebot
```

---

## What Changed in the Code

**Database:**
- Added `captcha_verified_at` column (TIMESTAMP) to `users` table

**Files Modified:**
- `handlers/real_handlers.py` - Fixed Markdown, added 7-day cache check
- `handlers/verification_flow.py` - Stores timestamp on CAPTCHA success
- `services/captcha.py` - Optimized image generation
- `database/models.py` - Added new field

**New Files:**
- `alembic/` - Database migration system
- `DEPLOYMENT_MIGRATION_GUIDE.md` - Detailed migration docs
- `DEPLOY_TO_EC2.sh` - Automated deployment script
- `EC2_QUICK_DEPLOY.md` - This file

---

## Future Deployments

For future updates, just:

```bash
cd ~/teleaccount-bot
git pull
./DEPLOY_TO_EC2.sh
```

The script handles everything automatically!

---

## Need Help?

**Check logs in real-time:**
```bash
sudo journalctl -u telebot -f
```

**Stop following logs:** Press `Ctrl+C`

**Restart bot:**
```bash
sudo systemctl restart telebot
```

That's it! Your bot is now live with all the new features. 🎉
