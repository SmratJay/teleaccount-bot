@echo off
title Heroku Bot Deployment
color 0A

echo.
echo 🚀 TELEGRAM BOT HEROKU DEPLOYMENT
echo ==================================
echo.
echo This will deploy your bot to Heroku in 3 steps:
echo 1. Install Heroku CLI (if needed)
echo 2. Deploy your bot
echo 3. Set tokens
echo.

echo 📋 CHECKING REQUIREMENTS...
echo.

REM Check if Heroku CLI is installed
heroku --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Heroku CLI not found!
    echo.
    echo 📥 INSTALLING HEROKU CLI...
    echo Please download and install from: https://cli-assets.heroku.com/heroku-x64.exe
    echo.
    echo After installation:
    echo 1. CLOSE this window
    echo 2. REOPEN Command Prompt or PowerShell
    echo 3. Run this script again
    echo.
    start https://cli-assets.heroku.com/heroku-x64.exe
    pause
    exit
)

echo ✅ Heroku CLI found!

REM Check if git repository is ready
if not exist ".git" (
    echo ❌ Git repository not found!
    echo Initializing git repository...
    git init
    git add .
    git commit -m "Initial commit"
)

echo ✅ Git repository ready!
echo.

echo 🔐 HEROKU LOGIN
echo Please login to your Heroku account in the browser...
heroku login
if errorlevel 1 (
    echo ❌ Heroku login failed!
    pause
    exit
)

echo.
set /p "APP_NAME=📝 Enter your unique app name (lowercase, no spaces): "
if "%APP_NAME%"=="" (
    set APP_NAME=mytelebot%RANDOM%
    echo Using random name: %APP_NAME%
)

echo.
echo 🏗️ Creating Heroku app: %APP_NAME%
heroku create %APP_NAME%
if errorlevel 1 (
    echo ❌ App creation failed (name might be taken)
    echo Try a different name or add numbers: %APP_NAME%123
    pause
    exit
)

echo.
echo 🐘 Adding PostgreSQL database...
heroku addons:create heroku-postgresql:essential-0 --app %APP_NAME%

echo.
echo ⚙️ Setting configuration...
heroku config:set DB_USER=postgres DEBUG=False ENVIRONMENT=production FLASK_ENV=production PORT=8080 --app %APP_NAME%

echo.
echo 🚀 Deploying your bot (this may take 2-3 minutes)...
git add .
git commit -m "Deploy to Heroku" --allow-empty
git push heroku main
if errorlevel 1 (
    echo ❌ Deployment failed!
    echo Check the error messages above.
    pause
    exit
)

echo.
echo 🎉 DEPLOYMENT SUCCESSFUL!
echo.
echo 🔗 Your bot: https://%APP_NAME%.herokuapp.com
echo 🔗 Dashboard: https://dashboard.heroku.com/apps/%APP_NAME%
echo.
echo 🔑 IMPORTANT: SET YOUR TOKENS NOW!
echo.
echo Opening Heroku dashboard to set tokens...
start https://dashboard.heroku.com/apps/%APP_NAME%/settings
echo.
echo Click "Reveal Config Vars" and add these variables:
echo.
echo BOT_TOKEN = get_from_@BotFather
echo API_ID = get_from_my.telegram.org  
echo API_HASH = get_from_my.telegram.org
echo TELEGRAM_API_ID = same_as_API_ID
echo TELEGRAM_API_HASH = same_as_API_HASH
echo ADMIN_CHAT_ID = your_telegram_user_id
echo ADMIN_USER_ID = your_telegram_user_id
echo.
echo 📱 After setting tokens, your bot will be LIVE!
echo Message your bot on Telegram to test it!
echo.
echo 🔧 Useful commands:
echo heroku logs --tail --app %APP_NAME%
echo heroku restart --app %APP_NAME%
echo.
pause