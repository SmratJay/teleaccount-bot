# 🎯 WEBSHARE SETUP - VISUAL WALKTHROUGH

## **COMPLETE STEP-BY-STEP WITH SCREENSHOTS**

---

## 📸 **STEP 1: CREATE WEBSHARE ACCOUNT**

### What you'll see:

**1.1 - Visit WebShare Homepage**
```
URL: https://proxy.webshare.io/

You'll see:
┌─────────────────────────────────────┐
│  WEBSHARE                           │
│  Premium Proxy Service              │
│                                     │
│  [Sign Up]  [Login]  [Pricing]     │
└─────────────────────────────────────┘
```

**1.2 - Click "Sign Up"**
```
Sign Up Form:
┌─────────────────────────────────────┐
│  Create Account                     │
│                                     │
│  Email: [________________]          │
│  Password: [________________]       │
│  Confirm: [________________]        │
│                                     │
│  [✓] I agree to Terms              │
│  [Create Account]                   │
└─────────────────────────────────────┘
```

**1.3 - Verify Email**
```
Check your inbox:
┌─────────────────────────────────────┐
│  From: WebShare <no-reply@...>      │
│  Subject: Verify Your Email         │
│                                     │
│  Click here to verify:              │
│  [Verify Email Address]             │
└─────────────────────────────────────┘
```

**1.4 - Email Verified!**
```
Success page:
┌─────────────────────────────────────┐
│  ✅ Email Verified!                 │
│                                     │
│  Your account is now active         │
│  [Continue to Dashboard]            │
└─────────────────────────────────────┘
```

---

## 🔑 **STEP 2: GET YOUR API TOKEN**

### What you'll see:

**2.1 - Go to Dashboard**
```
After login:
┌─────────────────────────────────────┐
│  WebShare Dashboard                 │
│  ├─ Dashboard                       │
│  ├─ Proxy List                      │
│  ├─ API                     ← CLICK │
│  ├─ Billing                         │
│  └─ Settings                        │
└─────────────────────────────────────┘
```

**2.2 - Click "API" Section**
```
Or directly visit:
https://proxy.webshare.io/userapi/
```

**2.3 - Find Your API Token**
```
API Page:
┌─────────────────────────────────────┐
│  API Access                         │
│                                     │
│  Your API Token:                    │
│  ┌───────────────────────────────┐ │
│  │ abc123def456ghi789jkl012mno345│ │
│  │ pqr678stu901vwx234yz567...    │ │
│  └───────────────────────────────┘ │
│  [📋 Copy Token]                    │
│                                     │
│  API Documentation: [View Docs]     │
└─────────────────────────────────────┘
```

**2.4 - Token Copied!**
```
Your token looks like:
abc123def456ghi789jkl012mno345pqr678stu901vwx234

⚠️ IMPORTANT: Keep this secret!
✅ Copy it to clipboard
📝 We'll use it in next step
```

---

## ⚙️ **STEP 3: ADD TOKEN TO YOUR BOT**

### What you'll do:

**3.1 - Open Project Folder**
```
Navigate to:
D:\teleaccount_bot

You'll see these files:
┌─────────────────────────────────────┐
│  📁 teleaccount_bot                 │
│  ├─ 📄 .env              ← EDIT THIS│
│  ├─ 📄 bot_proxy_test.py           │
│  ├─ 📄 main.py                      │
│  ├─ 📄 requirements.txt             │
│  ├─ 📁 services/                    │
│  └─ ...                             │
└─────────────────────────────────────┘
```

**3.2 - Open .env File**
```
Right-click .env → Open with Notepad

You'll see:
┌─────────────────────────────────────┐
│  # Bot Configuration                │
│  BOT_TOKEN=8483671369:AAE...        │
│  API_ID=21734417                    │
│  API_HASH=d64eb98d90eb...           │
│                                     │
│  # WebShare.io Integration          │
│  WEBSHARE_ENABLED=false      ← FIX! │
│  WEBSHARE_API_TOKEN=your_web... ← FIX│
│  WEBSHARE_PROXY_COUNT=100           │
└─────────────────────────────────────┘
```

**3.3 - Edit WebShare Settings**
```
BEFORE:
WEBSHARE_ENABLED=false
WEBSHARE_API_TOKEN=your_webshare_token_here

AFTER:
WEBSHARE_ENABLED=true
WEBSHARE_API_TOKEN=abc123def456ghi789jkl012mno345pqr678stu901vwx234
                   ↑ YOUR ACTUAL TOKEN HERE
```

**3.4 - Save File**
```
In Notepad:
File → Save
Or press: Ctrl+S

✅ File saved!
```

---

## 🤖 **STEP 4: RESTART YOUR BOT**

### What you'll do:

**4.1 - Open PowerShell**
```
Windows Search → "PowerShell"

PowerShell window:
┌─────────────────────────────────────┐
│  Windows PowerShell                 │
│  PS C:\Users\YourName>              │
│  ▊                                  │
└─────────────────────────────────────┘
```

**4.2 - Navigate to Project**
```powershell
cd D:\teleaccount_bot
```

**4.3 - Stop Bot (if running)**
```
If bot is already running:
Press: Ctrl+C

You'll see:
Bot stopped by user
PS D:\teleaccount_bot>
```

**4.4 - Start Bot**
```powershell
D:/teleaccount_bot/.venv/Scripts/python.exe bot_proxy_test.py
```

**4.5 - Wait for Success**
```
You'll see:
┌─────────────────────────────────────┐
│ 2025-10-19 16:25:23 - INFO -        │
│ Loaded custom rules for operation:  │
│ account_creation                    │
│ ... (more loading messages)         │
│                                     │
│ ✅ Bot started successfully!        │
│ Press Ctrl+C to stop                │
│                                     │
│ HTTP Request: POST .../getMe        │
│ "HTTP/1.1 200 OK"                   │
│                                     │
│ Application started                 │
│ ▊                                   │
└─────────────────────────────────────┘

✅ Bot is now ONLINE!
```

---

## 📱 **STEP 5: FETCH PROXIES IN TELEGRAM**

### What you'll do:

**5.1 - Open Telegram App**
```
Mobile or Desktop app:
┌─────────────────────────────────────┐
│  < Chats                   Search 🔍│
│                                     │
│  🤖 Your Bot Name           Now     │
│  Last seen recently                 │
│                                     │
│  📱 Contact 1               2:30 PM │
│  📱 Contact 2               1:15 PM │
└─────────────────────────────────────┘
```

**5.2 - Find Your Bot**
```
Tap on your bot:
┌─────────────────────────────────────┐
│  < Your Bot Name          ⋮         │
│  ─────────────────────────────────  │
│                                     │
│  Type a message...                  │
│  ▊                                  │
└─────────────────────────────────────┘
```

**5.3 - Test WebShare Info**
```
Type and send:
/webshare_info

Bot responds:
┌─────────────────────────────────────┐
│  💎 WebShare Account Info           │
│                                     │
│  Email: your@email.com              │
│  Available Proxies: 10              │
│  Bandwidth: 0.00 GB                 │
│  Account Type: Free                 │
│                                     │
│  Status: ✅ Active                  │
│  Proxies in Database: 0             │
└─────────────────────────────────────┘

✅ WebShare connected!
```

**5.4 - Fetch Proxies**
```
Type and send:
/fetch_webshare

Bot responds:
┌─────────────────────────────────────┐
│  🔄 Fetching proxies from           │
│  WebShare.io...                     │
│                                     │
│  ✅ Successfully fetched WebShare   │
│  proxies!                           │
│                                     │
│  WebShare proxies in database: 10   │
│  Provider: WebShare.io Premium      │
└─────────────────────────────────────┘

🎉 Proxies fetched!
```

**5.5 - Verify Proxy Count**
```
Type and send:
/proxy_stats

Bot responds:
┌─────────────────────────────────────┐
│  📊 Proxy Statistics                │
│                                     │
│  Total Proxies: 510                 │
│         ↑ Was 500, now +10!         │
│  Active Proxies: 510                │
│  Current Strategy: weighted         │
│  Last Refresh: 2025-10-19 16:30:15  │
│                                     │
│  Operation Counts:                  │
│    • account_creation: 3            │
│    • login: 3                       │
│    • otp_retrieval: 3               │
│    ...                              │
└─────────────────────────────────────┘

✅ Proxy count increased!
```

**5.6 - Check Providers**
```
Type and send:
/proxy_providers

Bot responds:
┌─────────────────────────────────────┐
│  🌐 Proxy Providers                 │
│                                     │
│  📍 free-proxy-list                 │
│     Total: 250 | Active: 235        │
│                                     │
│  📍 socks-proxy                     │
│     Total: 150 | Active: 142        │
│                                     │
│  📍 proxy-list                      │
│     Total: 100 | Active: 95         │
│                                     │
│  📍 webshare          ← NEW!        │
│     Total: 10 | Active: 10          │
└─────────────────────────────────────┘

🎉 WebShare provider added!
```

**5.7 - Test Proxy Selection**
```
Type and send:
/proxy_test

Bot responds:
┌─────────────────────────────────────┐
│  🧪 Proxy Selection Test            │
│                                     │
│  ✅ account_creation:               │
│     142.93.154.89:8080 (SOCKS5)     │
│     Success: 98.5% | Country: US    │
│     ↑ High quality WebShare proxy!  │
│                                     │
│  ✅ login:                          │
│     167.172.184.166:1080 (SOCKS5)   │
│     Success: 97.2% | Country: GB    │
│                                     │
│  ✅ otp_retrieval:                  │
│     138.68.161.123:4145 (SOCKS5)    │
│     Success: 96.8% | Country: FR    │
└─────────────────────────────────────┘

✅ WebShare proxies working!
```

---

## ✅ **SUCCESS! YOU'RE DONE!**

### What you achieved:

```
✅ WebShare account created
✅ API token obtained
✅ Token configured in .env
✅ Bot restarted with new config
✅ WebShare connection verified
✅ 10 premium proxies fetched
✅ Total proxy count: 510
✅ WebShare provider active
✅ Premium proxies ready to use!
```

---

## 🎯 **WHAT YOU HAVE NOW**

### Before WebShare:
```
┌────────────────────────┐
│  500 Free Proxies      │
│  Quality: Variable     │
│  Success: ~85-95%      │
│  Speed: Mixed          │
└────────────────────────┘
```

### After WebShare:
```
┌────────────────────────┐
│  500 Free Proxies      │
│  Quality: Variable     │
│  Success: ~85-95%      │
│  Speed: Mixed          │
└────────────────────────┘
        +
┌────────────────────────┐
│  10 Premium Proxies    │
│  Quality: HIGH         │
│  Success: ~98%         │
│  Speed: Fast           │
│  Provider: WebShare    │
└────────────────────────┘
        =
┌────────────────────────┐
│  510 TOTAL PROXIES     │
│  Mix of free + premium │
│  Best of both worlds!  │
└────────────────────────┘
```

---

## 🔄 **OPTIONAL: ENABLE AUTO-REFRESH**

**What it does:**
- Automatically refreshes WebShare proxies daily
- Keeps proxy pool fresh
- No manual `/fetch_webshare` needed

**How to enable:**

```
1. Open .env file
2. Find: PROXY_AUTO_REFRESH=false
3. Change to: PROXY_AUTO_REFRESH=true
4. Save file
5. Restart bot

✅ Done! Proxies refresh automatically every 24h
```

---

## 💡 **PRO TIPS**

### Upgrade Your Plan
```
Free (10 proxies)          $0/month
    ↓ Upgrade
Starter (25 proxies)       $2.99/month
    ↓ Upgrade
Professional (100 proxies) $9.99/month
    ↓ Upgrade
Business (500 proxies)     $49.99/month
```

### When to Use WebShare Proxies
```
✅ USE WebShare for:
   - Account creation (critical)
   - OTP retrieval (needs reliability)
   - Verification (needs clean IPs)
   - Payment operations
   - Sensitive operations

❌ Use FREE proxies for:
   - Testing
   - Development
   - General browsing
   - Low-priority tasks
```

### Monitor Performance
```
Daily checks:
/proxy_health    ← Check overall health
/proxy_stats     ← Monitor usage
/proxy_providers ← See WebShare status

Weekly tasks:
- Check WebShare dashboard
- Review bandwidth usage
- Monitor success rates
- Adjust strategy if needed
```

---

## 🎊 **CONGRATULATIONS!**

You now have:
- ✅ Premium WebShare proxies integrated
- ✅ Mixed proxy pool (free + premium)
- ✅ Better success rates for critical ops
- ✅ Automatic proxy management
- ✅ Full control via Telegram commands

**Your proxy ecosystem is complete!** 🚀

---

*Visual guide created: October 19, 2025*  
*Total setup time: 5-10 minutes*  
*Difficulty: Beginner-friendly*
