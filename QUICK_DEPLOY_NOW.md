🚀 FASTEST HEROKU DEPLOYMENT - GET YOUR BOT LIVE NOW!
=====================================================

📥 STEP 1: INSTALL HEROKU CLI (2 minutes)
-----------------------------------------
1. Go to: https://devcenter.heroku.com/articles/heroku-cli
2. Download the Windows installer
3. Run the installer (takes 1-2 minutes)
4. Restart your PowerShell/Command Prompt

OR use this direct link:
Windows 64-bit: https://cli-assets.heroku.com/heroku-x64.exe

🔑 STEP 2: PREPARE YOUR TOKENS (Have these ready!)
--------------------------------------------------
You need these tokens - get them now while Heroku installs:

A) BOT TOKEN (from @BotFather):
   1. Message @BotFather on Telegram
   2. Send: /newbot
   3. Choose name and username for your bot
   4. Copy the token (looks like: 123456789:ABCdefGHI...)

B) API CREDENTIALS (from my.telegram.org):
   1. Go to: https://my.telegram.org
   2. Login with your phone number
   3. Click "API development tools"
   4. Create an app (any name/description)
   5. Copy API ID and API Hash

C) YOUR TELEGRAM USER ID:
   1. Message @userinfobot on Telegram
   2. It shows your user ID (like: 6733908384)

🚀 STEP 3: DEPLOY IN 2 MINUTES
------------------------------
Once Heroku CLI is installed, run these commands:

1. Open NEW PowerShell window (important!)
2. Navigate to your bot folder:
   cd D:\teleaccount_bot

3. Run the deployment script:
   .\deploy_heroku.ps1

4. Follow the prompts:
   - Enter unique app name (like: mybotname123)
   - Confirm deployment
   - Wait 2-3 minutes

🔧 STEP 4: SET YOUR TOKENS (1 minute)
------------------------------------
After deployment, set your tokens:

1. Go to: https://dashboard.heroku.com/apps/YOUR-APP-NAME/settings
2. Click "Reveal Config Vars"
3. Add these variables:

   BOT_TOKEN = your_bot_token_from_step_2A
   API_ID = your_api_id_from_step_2B  
   API_HASH = your_api_hash_from_step_2B
   TELEGRAM_API_ID = same_as_api_id
   TELEGRAM_API_HASH = same_as_api_hash
   ADMIN_CHAT_ID = your_user_id_from_step_2C
   ADMIN_USER_ID = your_user_id_from_step_2C
   LEADER_CHANNEL_ID = -1001234567890

4. Bot automatically restarts and goes live!

✅ ALTERNATIVE: ONE-CLICK DEPLOY
-------------------------------
If you have the tokens ready, use this button:
https://heroku.com/deploy?template=https://github.com/your-repo

🎉 YOUR BOT WILL BE LIVE IN 5 MINUTES!
======================================

Total time breakdown:
- Install Heroku CLI: 2 minutes
- Get tokens: 2 minutes  
- Deploy: 2 minutes
- Set config: 1 minute
- TOTAL: 7 minutes to go live!

💡 NEED HELP?
- Heroku install issues: Use direct download link above
- Token issues: Follow the @BotFather and my.telegram.org steps exactly
- Deployment issues: Run the deploy script again

🚀 LET'S GET YOUR BOT LIVE NOW!