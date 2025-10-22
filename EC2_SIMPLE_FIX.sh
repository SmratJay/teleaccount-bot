#!/bin/bash
# Run this script ON EC2 to update the bot code

echo "========================================="
echo "EC2 Bot Update Script"
echo "========================================="

cd ~/teleaccount-bot || { echo "ERROR: Directory not found"; exit 1; }

echo ""
echo "Step 1: Checking current code..."
echo "Current commit:"
git log -1 --oneline

echo ""
echo "Step 2: Fetching latest code from GitHub..."
git fetch origin

echo ""
echo "Step 3: Hard reset to latest code..."
git reset --hard origin/main

echo ""
echo "Step 4: Verify new code exists..."
if grep -q "Admin handlers registered successfully" handlers/real_handlers.py; then
    echo "✅ New code detected!"
else
    echo "❌ New code NOT found - something went wrong"
    exit 1
fi

echo ""
echo "Step 5: Clearing Python cache..."
find . -name "*.pyc" -delete 2>/dev/null
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

echo ""
echo "Step 6: Stopping bot..."
sudo systemctl stop telebot

echo ""
echo "Step 7: Starting bot with new code..."
sudo systemctl start telebot

echo ""
echo "Step 8: Waiting for startup..."
sleep 5

echo ""
echo "Step 9: Checking if new code is running..."
echo "========================================="
sudo journalctl -u telebot -n 50 --no-pager | grep -E "✅|registered|loaded|CRITICAL|⚠️" || echo "No handler messages found - code may not be updated"

echo ""
echo "========================================="
echo "Done! Check the output above for ✅ marks"
echo "========================================="
