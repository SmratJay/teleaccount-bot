@echo off
echo Stopping all existing bot instances...
taskkill /F /IM python.exe /FI "WINDOWTITLE eq *real_main*" 2>nul
timeout /t 2 /nobreak >nul

echo Clearing Python cache...
if exist "d:\teleaccount_bot\database\__pycache__" rmdir /s /q "d:\teleaccount_bot\database\__pycache__"
if exist "d:\teleaccount_bot\__pycache__" rmdir /s /q "d:\teleaccount_bot\__pycache__"

echo Starting bot...
python real_main.py
