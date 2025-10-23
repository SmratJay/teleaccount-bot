# 🔒 SECURITY LOCKDOWN CHECKLIST

**CRITICAL: Complete this checklist BEFORE deploying code fixes**

**Estimated Time:** 30 minutes  
**Priority:** CRITICAL - Do this immediately

---

## ☑️ STEP 1: Revoke Telegram Bot Token (5 min)

**Current Token:** `8483671369:AAEOTZCDpCPiarfZHdb1Z5CFAZoMvdtmeKs` ⚠️ EXPOSED

### Actions:
1. Open Telegram and find `@BotFather`
2. Send command: `/mybots`
3. Select your bot
4. Click "API Token" → "Revoke current token"
5. Confirm revocation
6. Copy the NEW token (you'll need it for Step 5)

**New Token:** `________________________________` (save this securely)

✅ **DONE** ☐

---

## ☑️ STEP 2: Rotate Database Credentials (10 min)

**Current URL:** `postgresql://neondb_owner:npg_oiTEI2qfeW8j@ep-silent-glade-ae6wc05t...` ⚠️ EXPOSED

### Actions:
1. Go to https://console.neon.tech
2. Log into your account
3. Select your project/database
4. Go to Settings → Reset Password
5. Generate new password
6. Copy the NEW connection string (you'll need it for Step 5)

**New Connection String:** `________________________________` (save this securely)

✅ **DONE** ☐

---

## ☑️ STEP 3: Revoke Telegram API Credentials (5 min)

**Current API_ID:** `21734417` ⚠️ EXPOSED  
**Current API_HASH:** `d64eb98d90eb41b8ba3644e3722a3714` ⚠️ EXPOSED

### Actions:
1. Go to https://my.telegram.org/apps
2. Log into your Telegram account
3. Delete the current app entry
4. Click "Create new application"
5. Fill in app details:
   - App title: `TeleAccount Bot`
   - Short name: `teleaccount`
   - Platform: Server
6. Copy the NEW api_id and api_hash

**New API_ID:** `________________________________`  
**New API_HASH:** `________________________________`

✅ **DONE** ☐

---

## ☑️ STEP 4: Secure EC2 SSH Access (5 min)

**Current Config:** SSH open to `0.0.0.0/0` (ENTIRE INTERNET) ⚠️ DANGEROUS

### Actions:
1. Go to AWS Console → EC2 → Instances
2. Find your bot instance: `13.53.80.228`
3. Click Security tab → Security Groups
4. Click the security group link
5. Click "Edit inbound rules"
6. Find the SSH rule (port 22, source 0.0.0.0/0)
7. Click "Edit"
8. Change Source to one of:
   - **Option A (Best):** `<Your IP>/32` (e.g., `203.0.113.45/32`)
   - **Option B (Good):** Your IP range (e.g., `203.0.113.0/24`)
   - **Option C (OK):** Use AWS Session Manager instead (no SSH needed)
9. Save rules

**Your IP Address:** `________________________________`

✅ **DONE** ☐

---

## ☑️ STEP 5: Create Secure .env File on EC2 (5 min)

### Actions:
1. SSH into your EC2 instance:
   ```bash
   ssh -i your-key.pem ubuntu@13.53.80.228
   ```

2. Create the environment directory and file:
   ```bash
   sudo mkdir -p /etc/telegram-bot
   sudo nano /etc/telegram-bot/.env
   ```

3. Paste the following (using NEW credentials from Steps 1-3):
   ```bash
   # Telegram Bot Configuration
   TELEGRAM_BOT_TOKEN=<NEW_TOKEN_FROM_STEP_1>
   API_ID=<NEW_API_ID_FROM_STEP_3>
   API_HASH=<NEW_API_HASH_FROM_STEP_3>
   
   # Admin Configuration
   ADMIN_TELEGRAM_ID=6733908384
   
   # Security
   SECRET_KEY=<GENERATE_NEW_RANDOM_STRING>
   
   # Database
   DATABASE_URL=<NEW_CONNECTION_STRING_FROM_STEP_2>
   
   # Optional: Debug mode (set to false in production)
   DEBUG=false
   ```

4. **Generate a new SECRET_KEY:**
   ```bash
   python3 -c "import secrets; print(secrets.token_urlsafe(32))"
   ```
   Copy the output and paste it as SECRET_KEY above

5. Save the file (Ctrl+O, Enter, Ctrl+X)

6. Secure the file permissions:
   ```bash
   sudo chmod 600 /etc/telegram-bot/.env
   sudo chown ubuntu:ubuntu /etc/telegram-bot/.env
   ```

7. Verify the file:
   ```bash
   sudo cat /etc/telegram-bot/.env
   ```

✅ **DONE** ☐

---

## ☑️ STEP 6: Remove Sensitive Files from Git (10 min - Optional but Recommended)

**WARNING:** This rewrites Git history. Only do this if you understand the implications.

### Actions:
1. Install git-filter-repo:
   ```bash
   pip install git-filter-repo
   ```

2. Clone a fresh copy (don't do this on EC2, do it locally):
   ```bash
   git clone <your-repo-url> teleaccount-cleanup
   cd teleaccount-cleanup
   ```

3. Remove sensitive files from ALL commits:
   ```bash
   git filter-repo --path create_env.py --invert-paths --force
   git filter-repo --path ENV_VARIABLES.md --invert-paths --force
   git filter-repo --path .encryption_key --invert-paths --force
   ```

4. Force push (this is destructive!):
   ```bash
   git push origin --force --all
   git push origin --force --tags
   ```

5. All team members must re-clone:
   ```bash
   cd ..
   rm -rf old-repo
   git clone <your-repo-url>
   ```

✅ **DONE** ☐ (or **SKIP** ☐ if you'll do this later)

---

## ✅ FINAL VERIFICATION

Before deploying code fixes, verify:

- [ ] New bot token is working (send a test message to bot)
- [ ] Database connection string is correct (test connection)
- [ ] `/etc/telegram-bot/.env` exists and has correct permissions (600)
- [ ] SSH access is restricted (try connecting from a different IP - should fail)
- [ ] Old credentials are truly revoked (try using old token - should fail)

---

## 🚀 NEXT STEP: DEPLOY CODE FIXES

Once all checkboxes are ✅, proceed to deploy the code fixes:

```bash
# On your EC2 instance
cd /path/to/teleaccount-bot
bash deploy_critical_fixes.sh
```

Or manually:
```bash
git pull origin main
pip3 install -r requirements.txt --upgrade
sudo systemctl restart telebot
sudo journalctl -u telebot -f
```

---

## 📞 EMERGENCY ROLLBACK

If something goes wrong after deployment:

```bash
# Restore from backup
sudo systemctl stop telebot
cd /home/ubuntu/telebot-backup-<timestamp>
pip3 install -r requirements.txt
sudo systemctl start telebot

# Check logs
sudo journalctl -u telebot -f
```

---

## 📝 NOTES

**What was exposed:**
- ✅ Telegram Bot Token → Revoked
- ✅ Database URL + Password → Rotated
- ✅ API ID + API Hash → Regenerated
- ✅ Encryption Key → Will regenerate
- ⚠️ SSH Access → Restricted

**Why this matters:**
With the old credentials, an attacker could:
- Take over your bot
- Access your database
- Read encrypted data
- SSH into your server (if they had the .pem file)

**After this checklist:**
- All attack vectors closed
- Fresh credentials secured
- Bot can be safely deployed

---

**Checklist completed on:** _________________ (date/time)  
**Completed by:** _________________ (your name)  
**All items verified:** ✅ YES ☐  /  ☐ NO

---

*Keep this checklist for your records. Store new credentials in a password manager.*
