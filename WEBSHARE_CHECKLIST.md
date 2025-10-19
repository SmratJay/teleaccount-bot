# ✅ WEBSHARE SETUP CHECKLIST

Print this and check off each step as you complete it!

---

## 🎯 **YOUR SETUP CHECKLIST**

### STEP 1: GET WEBSHARE ACCOUNT ⏱️ 2 min

- [ ] Go to https://proxy.webshare.io/
- [ ] Click "Sign Up"
- [ ] Enter email: ___________________________
- [ ] Create password
- [ ] Verify email (check inbox)
- [ ] Login to account

**Account Type:**
- [ ] Free (10 proxies)
- [ ] Starter ($2.99 - 25 proxies)
- [ ] Professional ($9.99 - 100 proxies)
- [ ] Business ($49.99 - 500 proxies)

---

### STEP 2: GET API TOKEN ⏱️ 1 min

- [ ] Visit: https://proxy.webshare.io/userapi/
- [ ] Find "API Token" section
- [ ] Click "Copy Token" button
- [ ] Token copied to clipboard ✓

**Write your token here (for reference):**
```
_____________________________________________
_____________________________________________
```

---

### STEP 3: CONFIGURE BOT ⏱️ 1 min

- [ ] Open folder: `D:\teleaccount_bot`
- [ ] Open file: `.env`
- [ ] Find line: `WEBSHARE_ENABLED=false`
- [ ] Change to: `WEBSHARE_ENABLED=true`
- [ ] Find line: `WEBSHARE_API_TOKEN=your_webshare_token_here`
- [ ] Paste your token after `=`
- [ ] Adjust `WEBSHARE_PROXY_COUNT` (optional)
  - [ ] Set to 10 (Free)
  - [ ] Set to 25 (Starter)
  - [ ] Set to 100 (Professional)
  - [ ] Set to 500 (Business)
- [ ] Save file (Ctrl+S)

---

### STEP 4: RESTART BOT ⏱️ 30 sec

- [ ] Open PowerShell
- [ ] Navigate: `cd D:\teleaccount_bot`
- [ ] Stop bot: Press `Ctrl+C` (if running)
- [ ] Start bot: `D:/teleaccount_bot/.venv/Scripts/python.exe bot_proxy_test.py`
- [ ] Wait for: "✅ Bot started successfully!"
- [ ] Bot is running ✓

---

### STEP 5: TEST IN TELEGRAM ⏱️ 1 min

- [ ] Open Telegram app
- [ ] Find your bot
- [ ] Send: `/webshare_info`
- [ ] Response shows account details ✓
- [ ] Send: `/fetch_webshare`
- [ ] Response: "Successfully fetched" ✓
- [ ] Send: `/proxy_stats`
- [ ] Total proxies increased ✓
- [ ] Send: `/proxy_providers`
- [ ] "webshare" provider appears ✓

---

### OPTIONAL: AUTO-REFRESH

- [ ] Open `.env` file again
- [ ] Find: `PROXY_AUTO_REFRESH=false`
- [ ] Change to: `PROXY_AUTO_REFRESH=true`
- [ ] Save file
- [ ] Restart bot
- [ ] Auto-refresh enabled ✓

---

## 🎊 **COMPLETION CHECK**

### All Done? Check These:

- [ ] WebShare account created and active
- [ ] API token obtained and saved
- [ ] Token added to `.env` file correctly
- [ ] `WEBSHARE_ENABLED=true` set
- [ ] `.env` file saved
- [ ] Bot restarted successfully
- [ ] `/webshare_info` command works
- [ ] `/fetch_webshare` fetched proxies
- [ ] Proxy count increased in `/proxy_stats`
- [ ] WebShare appears in `/proxy_providers`
- [ ] `/proxy_test` shows WebShare proxies

---

## 📊 **FINAL STATUS**

**Before Setup:**
- Total Proxies: 500
- Providers: 3
- Premium Proxies: 0

**After Setup:**
- Total Proxies: _____ (should be 510+ for free account)
- Providers: _____ (should be 4)
- Premium Proxies: _____ (should be 10+ for free account)

---

## ✅ **SUCCESS CRITERIA**

You've successfully completed setup if:

✅ All checkboxes above are checked  
✅ Bot responds to all commands  
✅ WebShare provider shows in list  
✅ Proxy count increased  
✅ `/proxy_test` includes WebShare proxies  

---

## 🐛 **TROUBLESHOOTING**

If something doesn't work:

**Problem: Bot says "WebShare not enabled"**
- [ ] Check `.env` has `WEBSHARE_ENABLED=true`
- [ ] Verify no extra spaces
- [ ] Restart bot

**Problem: "API token not configured"**
- [ ] Verify token in `.env` is correct
- [ ] Check no line breaks in token
- [ ] Token should be one continuous string
- [ ] Get new token from WebShare if needed

**Problem: "Failed to fetch proxies"**
- [ ] Verify WebShare account is active
- [ ] Check you have available proxies
- [ ] Ensure internet connection works
- [ ] Try again in a few minutes

---

## 📞 **NEED HELP?**

**WebShare Issues:**
- Visit: https://proxy.webshare.io/
- Email: support@webshare.io
- Check: WebShare documentation

**Bot Issues:**
- Check terminal logs for errors
- Review Telegram bot responses
- Verify `.env` configuration
- Ensure bot is running

---

## 🎯 **QUICK COMMANDS REFERENCE**

Keep this handy:

```
/webshare_info    - Check account details
/fetch_webshare   - Fetch proxies from WebShare
/proxy_stats      - View total proxy count
/proxy_providers  - See all providers (including WebShare)
/proxy_test       - Test proxy selection
/proxy_health     - Check system health
/start            - Restart bot/show help
```

---

## 📅 **MAINTENANCE SCHEDULE**

**Daily:**
- [ ] Check bot is running
- [ ] Monitor `/proxy_health`

**Weekly:**
- [ ] Review WebShare dashboard
- [ ] Check bandwidth usage
- [ ] Run `/proxy_stats`

**Monthly:**
- [ ] Verify subscription active
- [ ] Review usage patterns
- [ ] Consider upgrading plan if needed

---

## 🎊 **CONGRATULATIONS!**

You've successfully integrated WebShare.io premium proxies!

**What you have now:**
- ✅ Premium datacenter proxies
- ✅ Higher success rates
- ✅ Better reliability
- ✅ Faster connections
- ✅ Mixed proxy pool (free + premium)
- ✅ Full Telegram control

**You're ready to go!** 🚀

---

*Print this checklist and check off each step!*  
*Estimated time: 5-10 minutes*  
*Difficulty: Easy*

**Date completed:** ___________________  
**Your signature:** ___________________
