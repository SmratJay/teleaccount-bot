#!/bin/bash
# EC2 Deployment Script for Telegram Bot Updates
# Run this on your EC2 instance after pushing code to Git

echo "================================"
echo "🚀 EC2 Bot Deployment Script"
echo "================================"
echo ""

# Set your database URL (from /etc/telegram-bot/.env)
export DATABASE_URL="postgresql://neondb_owner:npg_oiTEI2qfeW8j@ep-silent-glade-ae6wc05t.c-2.us-east-2.aws.neon.tech/neondb?sslmode=require"

# Step 1: Navigate to project directory
echo "📁 Step 1: Navigating to project directory..."
cd ~/teleaccount-bot || { echo "❌ Project directory not found!"; exit 1; }
echo "✅ In project directory"
echo ""

# Step 2: Pull latest code from Git
echo "📥 Step 2: Pulling latest code from Git..."
git pull origin main || { echo "❌ Git pull failed!"; exit 1; }
echo "✅ Code updated"
echo ""

# Step 3: Add database column for 7-day CAPTCHA cache
echo "🗄️ Step 3: Adding captcha_verified_at column to database..."
psql $DATABASE_URL -c "ALTER TABLE users ADD COLUMN IF NOT EXISTS captcha_verified_at TIMESTAMP;" || { echo "❌ Database update failed!"; exit 1; }
echo "✅ Database column added"
echo ""

# Step 4: Verify column was added
echo "🔍 Step 4: Verifying database column..."
COLUMN_CHECK=$(psql $DATABASE_URL -t -c "SELECT column_name FROM information_schema.columns WHERE table_name='users' AND column_name='captcha_verified_at';")
if [[ -z "${COLUMN_CHECK// }" ]]; then
    echo "❌ Column verification failed!"
    exit 1
else
    echo "✅ Column verified: captcha_verified_at exists"
fi
echo ""

# Step 5: Restart the bot service
echo "🔄 Step 5: Restarting bot service..."
sudo systemctl restart telebot || { echo "❌ Service restart failed!"; exit 1; }
echo "✅ Bot restarted"
echo ""

# Step 6: Check service status
echo "📊 Step 6: Checking service status..."
sleep 2
sudo systemctl status telebot --no-pager -l || true
echo ""

echo "================================"
echo "✅ DEPLOYMENT COMPLETE!"
echo "================================"
echo ""
echo "📋 What was deployed:"
echo "  ✓ 7-day CAPTCHA verification cache"
echo "  ✓ Faster CAPTCHA (200x70px, 4 characters)"
echo "  ✓ Fixed 'Continue to Main Menu' button (Markdown parsing)"
echo "  ✓ Database migration system (Alembic)"
echo ""
echo "🧪 Testing checklist:"
echo "  1. Send /start to the bot"
echo "  2. Complete CAPTCHA verification"
echo "  3. Click 'Continue to Main Menu' - should work now!"
echo "  4. Send /start again - should skip CAPTCHA (cached for 7 days)"
echo ""
echo "📝 View live logs:"
echo "  sudo journalctl -u telebot -f"
echo ""
