@echo off
echo Starting Telegram Account Bot...
cd /d "D:\teleaccount_bot"

echo Bot is starting in background...
start /b python main.py

echo.
echo ✅ Bot started successfully in background!
echo.
echo 📱 To test your bot:
echo 1. Open Telegram app
echo 2. Search for your bot (the username you gave to @BotFather)
echo 3. Send /start command
echo.
echo 🔧 To stop the bot:
echo Use: taskkill /f /im python.exe
echo.
echo 📋 Bot logs are saved in the logs/ folder
echo.
pause