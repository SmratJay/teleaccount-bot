🚀 COPY-PASTE HEROKU DEPLOYMENT - 5 MINUTES TO LIVE BOT!
==========================================================

📥 STEP 1: INSTALL HEROKU CLI (2 minutes)
------------------------------------------
1. Click this link: https://cli-assets.heroku.com/heroku-x64.exe
2. Download and run the installer
3. Click "Next" through all prompts
4. CLOSE and REOPEN PowerShell when done

📱 STEP 2: GET BOT TOKEN (1 minute) 
-----------------------------------
1. Open Telegram
2. Message @BotFather
3. Send: /newbot
4. Enter bot name: My Selling Bot
5. Enter username: mysellingbot123 (or any unique name)
6. COPY the token (looks like: 123456789:ABCdef...)

🔑 STEP 3: GET API CREDENTIALS (1 minute)
-----------------------------------------
1. Go to: https://my.telegram.org
2. Enter your phone number
3. Enter the code Telegram sends you
4. Click "API development tools"
5. Fill form:
   - App title: My Bot App
   - Short name: mybot
   - Platform: Other
   - Description: My telegram bot
6. Click "Create application"
7. COPY the API ID and API Hash

🚀 STEP 4: DEPLOY WITH COPY-PASTE COMMANDS (1 minute)
-----------------------------------------------------
Copy and paste these commands ONE BY ONE in PowerShell:

COMMAND 1: Login to Heroku
heroku login

COMMAND 2: Create your app (change 'mybotapp123' to something unique)
heroku create mybotapp123

COMMAND 3: Add database
heroku addons:create heroku-postgresql:essential-0 --app mybotapp123

COMMAND 4: Set basic config
heroku config:set DB_USER=postgres DEBUG=False ENVIRONMENT=production --app mybotapp123

COMMAND 5: Deploy!
git push heroku main

⚙️ STEP 5: SET YOUR TOKENS (1 minute)
-------------------------------------
1. Go to: https://dashboard.heroku.com
2. Click on your app (mybotapp123)
3. Click "Settings" tab
4. Click "Reveal Config Vars"
5. Add these (click "Add" for each):

BOT_TOKEN = your_bot_token_from_step_2
API_ID = your_api_id_from_step_3
API_HASH = your_api_hash_from_step_3
TELEGRAM_API_ID = your_api_id_from_step_3
TELEGRAM_API_HASH = your_api_hash_from_step_3
ADMIN_CHAT_ID = 6733908384
ADMIN_USER_ID = 6733908384
LEADER_CHANNEL_ID = -1001234567890

🎉 YOUR BOT IS NOW LIVE!
========================

Your bot URL: https://mybotapp123.herokuapp.com
Dashboard: https://dashboard.heroku.com/apps/mybotapp123

Test it: Message your bot on Telegram!

💡 TROUBLESHOOTING:
- If app name is taken, try: mybotapp456, telebot789, etc.
- If deployment fails, run: git push heroku main again
- Check logs: heroku logs --tail --app mybotapp123

🎊 TOTAL TIME: 5 MINUTES TO LIVE BOT!