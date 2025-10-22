#!/bin/bash
# Fix both the ConversationHandler scope error AND the markdown parsing error

cd ~/teleaccount-bot || exit 1

echo "Fixing Issue #1: Removing duplicate ConversationHandler import..."
sed -i '/from telegram.ext import ConversationHandler, MessageHandler/d' handlers/admin_handlers.py

echo "Fixing Issue #2: Removing backticks from markdown..."
sed -i 's/\*\*Example:\*\* `johndoe`/**Example:** johndoe/' handlers/reports_logs_handlers.py

echo ""
echo "Restarting bot..."
sudo systemctl restart telebot

echo ""
echo "Waiting for startup..."
sleep 5

echo ""
echo "Checking logs..."
sudo journalctl -u telebot -n 50 --no-pager | grep -E "✅|❌|CRITICAL"

echo ""
echo "Done! Check above for ✅ marks (should see NO ❌ errors)"
