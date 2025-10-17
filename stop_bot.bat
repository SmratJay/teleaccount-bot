@echo off
echo Stopping Telegram Account Bot...

tasklist /FI "IMAGENAME eq python.exe" | find /I "python.exe" >nul
if %ERRORLEVEL% EQU 0 (
    echo Found running Python processes. Stopping bot...
    taskkill /f /im python.exe /t
    echo ✅ Bot stopped successfully!
) else (
    echo ❌ No Python processes found. Bot may not be running.
)

echo.
pause