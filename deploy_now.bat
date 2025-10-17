@echo off
echo.
echo 🚀 HEROKU DEPLOYMENT - TELEACCOUNT BOT
echo ======================================
echo.
echo ⚠️  PREREQUISITE CHECK:
echo 1. Heroku CLI must be installed first!
echo    Download: https://cli-assets.heroku.com/heroku-x64.exe
echo.
echo 2. You need these tokens ready:
echo    - Bot Token (from @BotFather)
echo    - API ID and Hash (from my.telegram.org)  
echo    - Your Telegram User ID (from @userinfobot)
echo.

set /p "ready=Do you have Heroku CLI installed and tokens ready? (y/N): "
if /i not "%ready%"=="y" (
    echo.
    echo 📥 Please install Heroku CLI first:
    echo 1. Download: https://cli-assets.heroku.com/heroku-x64.exe
    echo 2. Install and restart command prompt
    echo 3. Run this script again
    pause
    exit
)

echo.
echo 🔐 Logging into Heroku...
heroku login

echo.
set /p "appname=Enter your unique app name (lowercase, no spaces): "
if "%appname%"=="" (
    echo ❌ App name required!
    pause
    exit
)

echo.
echo 🏗️  Creating Heroku app: %appname%
heroku create %appname%
if errorlevel 1 (
    echo ❌ Failed to create app. Name might be taken. Try a different name.
    pause
    exit
)

echo.
echo 🐘 Adding PostgreSQL database...
heroku addons:create heroku-postgresql:essential-0 --app %appname%

echo.
echo ⚙️  Setting up basic configuration...
heroku config:set DB_USER=postgres --app %appname%
heroku config:set DEBUG=False --app %appname%
heroku config:set ENVIRONMENT=production --app %appname%

echo.
echo 📦 Preparing code for deployment...
if not exist ".git" (
    git init
)
git add .
git commit -m "Deploy TeleAccount Bot to Heroku"

echo.
echo 🚀 Deploying to Heroku (this may take 2-3 minutes)...
git push heroku main
if errorlevel 1 (
    echo ❌ Deployment failed. Check the error messages above.
    pause
    exit
)

echo.
echo 🎉 DEPLOYMENT SUCCESSFUL!
echo.
echo 🔗 Your bot URL: https://%appname%.herokuapp.com
echo 🔗 Dashboard: https://dashboard.heroku.com/apps/%appname%
echo.
echo 🔑 CRITICAL: SET YOUR TOKENS NOW!
echo.
echo Go to: https://dashboard.heroku.com/apps/%appname%/settings
echo Click "Reveal Config Vars" and add:
echo.
echo BOT_TOKEN = your_bot_token_here
echo API_ID = your_api_id
echo API_HASH = your_api_hash  
echo TELEGRAM_API_ID = same_as_api_id
echo TELEGRAM_API_HASH = same_as_api_hash
echo ADMIN_CHAT_ID = your_telegram_user_id
echo ADMIN_USER_ID = your_telegram_user_id
echo.
echo Once you set these tokens, your bot will automatically restart and go live!
echo.
echo 📱 Test your bot by messaging it on Telegram!
echo.
pause