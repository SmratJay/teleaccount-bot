@echo off
echo 🚀 Quick Heroku Deployment for Windows
echo =====================================

echo.
echo 📋 Prerequisites Check:
echo 1. Heroku CLI installed? (Download from: https://devcenter.heroku.com/articles/heroku-cli)
echo 2. Git installed?
echo 3. Heroku account created?
echo.

set /p "continue=Ready to deploy? (y/N): "
if /i not "%continue%"=="y" (
    echo Deployment cancelled.
    pause
    exit
)

echo.
set /p "appname=Enter your unique Heroku app name: "
if "%appname%"=="" (
    echo App name cannot be empty!
    pause
    exit
)

echo.
echo 🔑 IMPORTANT: You'll need these tokens ready:
echo - Bot Token (from @BotFather)
echo - API ID and API Hash (from my.telegram.org)
echo - Your Telegram User ID
echo.
pause

echo 🏗️ Creating Heroku app: %appname%
heroku create %appname%

echo 🐘 Adding PostgreSQL database...
heroku addons:create heroku-postgresql:essential-0 --app %appname%

echo ⚙️ Setting basic config vars...
heroku config:set DB_USER=postgres --app %appname%
heroku config:set DEBUG=False --app %appname%
heroku config:set ENVIRONMENT=production --app %appname%
heroku config:set FLASK_ENV=production --app %appname%
heroku config:set PORT=8080 --app %appname%

echo 📦 Initializing git and deploying...
git init
git add .
git commit -m "Deploy to Heroku"
git push heroku main

echo.
echo 🎉 DEPLOYMENT COMPLETE!
echo.
echo 🔗 Your app: https://%appname%.herokuapp.com
echo 🔗 Dashboard: https://dashboard.heroku.com/apps/%appname%
echo.
echo 🔑 NEXT STEPS - SET THESE ENVIRONMENT VARIABLES:
echo Go to: https://dashboard.heroku.com/apps/%appname%/settings
echo Click "Reveal Config Vars" and add:
echo.
echo BOT_TOKEN = your_bot_token_from_botfather
echo API_ID = your_api_id_from_my_telegram_org
echo API_HASH = your_api_hash_from_my_telegram_org
echo TELEGRAM_API_ID = same_as_api_id
echo TELEGRAM_API_HASH = same_as_api_hash
echo ADMIN_CHAT_ID = your_telegram_user_id
echo ADMIN_USER_ID = your_telegram_user_id
echo LEADER_CHANNEL_ID = your_channel_id_for_notifications
echo.
echo 🔧 Useful commands:
echo heroku logs --tail --app %appname%
echo heroku restart --app %appname%
echo.
pause