# 🚀 Quick Deployment Checklist

## Before You Start
- [ ] All code changes are saved in Replit
- [ ] You have access to your EC2 server
- [ ] You know your GitHub credentials

---

## Part 1: Sync to GitHub (Do this on Replit or your computer)

```bash
# Copy and paste these commands one by one:

git add .

git commit -m "UI text fixes: Update branding to teleflare_bot_io, fix balance display, clean admin messages"

git push origin main
```

**✅ Checkpoint:** Visit your GitHub repository - you should see the new commit

---

## Part 2: Deploy to EC2 (Do this on your EC2 server)

```bash
# 1. Connect to EC2
ssh -i your-key.pem ubuntu@13.53.80.228

# 2. Go to project folder
cd ~/teleaccount-bot

# 3. Pull changes from GitHub
git pull origin main

# 4. Restart bot
sudo systemctl restart telebot

# 5. Check it's running
sudo systemctl status telebot
```

**✅ Checkpoint:** You should see "active (running)" in green

---

## Part 3: Test in Telegram

- [ ] Send `/start` to your bot
- [ ] Main menu says "Welcome to teleflare_bot_io" ✓
- [ ] Balance shows `$0.00` (not `\$0.00`) ✓
- [ ] Bot responds normally ✓

---

## If Something Goes Wrong

### Bot shows old text?
```bash
# On EC2, check which version is running:
cd ~/teleaccount-bot
git log -1

# Should show your latest commit. If not:
git pull origin main
sudo systemctl restart telebot
```

### Bot won't start?
```bash
# View error logs:
sudo journalctl -u telebot -n 50

# Force restart:
sudo systemctl stop telebot
sleep 2
sudo systemctl start telebot
```

### Still stuck?
```bash
# View live logs to see what's happening:
sudo journalctl -u telebot -f
# (Press Ctrl+C to stop)
```

---

## Quick Reference Commands

```bash
# View status
sudo systemctl status telebot

# Restart bot
sudo systemctl restart telebot

# View logs (last 50 lines)
sudo journalctl -u telebot -n 50

# Follow live logs
sudo journalctl -u telebot -f

# Check code version
cd ~/teleaccount-bot && git log -1
```

---

## Success Indicators

✅ Git push succeeded (no errors)  
✅ Git pull on EC2 succeeded  
✅ Bot service shows "active (running)"  
✅ Telegram shows updated text  
✅ No errors in logs  

**Estimated time:** 2-3 minutes total
